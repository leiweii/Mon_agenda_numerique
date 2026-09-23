import csv
import logging
import time
from pathlib import PurePosixPath

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date, timedelta
from agenda.models import Tache, Categorie, PreferenceUtilisateur, StatistiqueUtilisation
from api.models import CVUtilisateur, Candidature, EmailCandidature
from .candidature_scraper import formulaire_vide, normaliser_url, scraper_candidature
from .candidature_llm import extraire_candidature_llm
from .email_candidature_service import preparer_contenu_email
from .email_send_service import EmailSendError, confirmer_manuellement, envoyer_email, lire_cv_par_defaut, nouvelle_tentative
from .serializers import ImportCandidatureSerializer
from .serializers import (
    ActionCandidatureSerializer,
    CandidatureSerializer,
    CategorieSerializer,
    EmailCandidatureSerializer,
    PreferenceUtilisateurSerializer,
    PreparationEmailCandidatureSerializer,
    PreparationEmailMasseLigneSerializer,
    PreparationEmailsMasseCommunSerializer,
    TacheSerializer,
)
from .llm_service import appeler_llm, construire_prompt, parser_reponse
from .llm_performance import (
    construire_cle_cache,
    ecrire_cache,
    finaliser_appel_llm,
    journaliser_appel_llm,
    obtenir_cache,
    obtenir_derniere_cache_valide,
    purger_journaux_si_necessaire,
    reserver_appel_llm,
)


logger = logging.getLogger(__name__)


def _csv_cell(value):
    if value is None:
        return ''
    if hasattr(value, 'isoformat'):
        value = value.isoformat()
    else:
        value = str(value)
    return f"'{value}" if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value


def _recommandation_meilleur_moment(utilisateur):
    stats = StatistiqueUtilisation.objects.filter(
        utilisateur=utilisateur
    ).values('heure_completion__hour').annotate(
        count=Count('id')
    ).order_by('-count', 'heure_completion__hour')[:3]

    if stats:
        heures_productives = [stat['heure_completion__hour'] for stat in stats]
        return {
            'heures_recommandees': heures_productives,
            'message': f'Vous êtes plus productif vers {heures_productives[0]}h',
        }
    return {
        'heures_recommandees': [],
        'message': 'Pas assez de données pour une recommandation',
    }

class TacheViewSet(viewsets.ModelViewSet):
    serializer_class = TacheSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Tache.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)
    
    @action(detail=False, methods=['get'])
    def aujourd_hui(self, request):
        today = timezone.localdate()
        taches = self.get_queryset().filter(
            date_echeance__date=today
        )
        serializer = self.get_serializer(taches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cette_semaine(self, request):
        today = timezone.localdate()
        debut_semaine = today - timedelta(days=today.weekday())
        fin_semaine = debut_semaine + timedelta(days=6)
        taches = self.get_queryset().filter(
            date_echeance__date__range=[debut_semaine, fin_semaine]
        )
        serializer = self.get_serializer(taches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        total = self.get_queryset().count()
        completees = self.get_queryset().filter(completee=True).count()
        comptes_priorite = {
            item['priorite']: item['count']
            for item in self.get_queryset().values('priorite').annotate(count=Count('id'))
        }
        par_priorite = [
            {'priorite': priorite, 'count': comptes_priorite.get(priorite, 0)}
            for priorite in range(1, 5)
        ]
        
        return Response({
            'total': total,
            'completees': completees,
            'en_cours': total - completees,
            'par_priorite': par_priorite,
            'taux_completion': (completees / total * 100) if total > 0 else 0
        })
    
    @action(detail=False, methods=['get'])
    def meilleur_moment(self, request):
        """Algorithme de recommandation du meilleur moment de travail"""
        return Response(_recommandation_meilleur_moment(request.user))


class CandidatureViewSet(viewsets.ModelViewSet):
    serializer_class = CandidatureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Candidature.objects.filter(utilisateur=self.request.user)
        if self.action not in {'list', 'export_csv'}:
            return queryset
        params = self.request.query_params

        if params.get('archive', '').lower() != 'true':
            queryset = queryset.filter(archive=False)

        choice_filters = {
            'statut': Candidature.Statut.values,
            'type_poste': Candidature.TypePoste.values,
            'source_canal': Candidature.SourceCanal.values,
        }
        for field, allowed_values in choice_filters.items():
            values = [value for value in params.getlist(field) if value in allowed_values]
            if values:
                queryset = queryset.filter(**{f'{field}__in': values})

        tags = [tag.strip() for tag in params.getlist('tags') if tag.strip()]
        if tags:
            queryset = queryset.filter(tags__contains=tags)

        if params.get('favori', '').lower() == 'true':
            queryset = queryset.filter(favori=True)

        search = params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(titre__icontains=search) | Q(entreprise__icontains=search))

        for param, lookup in (
            ('date_ajout_min', 'date_ajout__date__gte'),
            ('date_ajout_max', 'date_ajout__date__lte'),
        ):
            value = params.get(param, '').strip()
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    continue
                queryset = queryset.filter(**{lookup: value})

        today = timezone.localdate()
        if params.get('date_limite') == '7j':
            queryset = queryset.filter(date_limite__range=(today, today + timedelta(days=7)))
        if params.get('relance_due', '').lower() == 'true':
            queryset = queryset.filter(date_relance__lte=today)

        ordering = params.get('ordering', '-date_ajout')
        allowed_orderings = {
            'date_ajout', '-date_ajout', 'date_limite', '-date_limite',
            'date_relance', '-date_relance', 'statut', '-statut',
        }
        if ordering not in allowed_orderings:
            ordering = '-date_ajout'
        return queryset.order_by(ordering, '-id')

    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)

    @action(detail=False, methods=['get', 'put'])
    def cv_par_defaut(self, request):
        cv = CVUtilisateur.objects.filter(utilisateur=request.user).first()
        if request.method == 'PUT':
            fichier = request.FILES.get('fichier')
            if fichier is None:
                return Response({'detail': 'Selectionnez un fichier PDF.'}, status=status.HTTP_400_BAD_REQUEST)
            if not fichier.name.lower().endswith('.pdf') or fichier.size > 5 * 1024 * 1024:
                return Response({'detail': 'Le CV doit etre un PDF de 5 Mio maximum.'}, status=status.HTTP_400_BAD_REQUEST)
            if fichier.read(5) != b'%PDF-':
                return Response({'detail': 'Le contenu du fichier doit etre un PDF.'}, status=status.HTTP_400_BAD_REQUEST)
            fichier.seek(0)
            if cv is None:
                cv = CVUtilisateur(utilisateur=request.user)
            old_name = cv.fichier.name
            new_name = None
            try:
                cv.fichier.save(fichier.name, fichier, save=False)
                new_name = cv.fichier.name
                cv.save()
            except Exception:
                if new_name:
                    cv.fichier.storage.delete(new_name)
                raise
            if old_name and old_name != new_name:
                cv.fichier.storage.delete(old_name)
        filename = PurePosixPath(cv.fichier.name).name if cv else None
        fingerprint = None
        if cv:
            try:
                _, filename, fingerprint = lire_cv_par_defaut(request.user)
            except EmailSendError:
                pass
        return Response({'filename': filename, 'fingerprint': fingerprint})

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        columns = [
            'titre', 'entreprise', 'type_poste', 'statut', 'source_canal',
            'tags', 'favori', 'date_limite', 'date_relance', 'date_ajout', 'url',
        ]
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="candidatures.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(columns)

        for candidature in self.get_queryset().iterator():
            writer.writerow(_csv_cell(value) for value in [
                candidature.titre,
                candidature.entreprise,
                candidature.type_poste,
                candidature.statut,
                candidature.source_canal,
                ';'.join(candidature.tags),
                candidature.favori,
                candidature.date_limite,
                candidature.date_relance,
                candidature.date_ajout,
                candidature.url,
            ])
        return response

    @action(detail=True, methods=['patch'])
    def archiver(self, request, pk=None):
        candidature = self.get_object()
        candidature.archive = True
        candidature.save(update_fields=['archive', 'date_modification'])
        return Response(self.get_serializer(candidature).data)

    @action(detail=True, methods=['post'])
    def preparer_email(self, request, pk=None):
        candidature = self.get_object()
        serializer = PreparationEmailCandidatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        contenu = preparer_contenu_email(
            entreprise=candidature.entreprise,
            nom_contact=donnees.get('nom_contact', ''),
            prenom_contact=donnees.get('prenom_contact', ''),
            civilite=donnees.get('civilite', ''),
            poste=candidature.titre,
            formation=donnees['formation'],
            portfolio_url=donnees['portfolio_url'],
            github_url=donnees['github_url'],
        )
        recipient_name = ' '.join(
            part for part in (
                donnees.get('prenom_contact', '').strip(),
                donnees.get('nom_contact', '').strip(),
            )
            if part
        )
        email = EmailCandidature.objects.create(
            candidature=candidature,
            recipient_email=donnees['recipient_email'],
            recipient_name=recipient_name,
            subject=contenu['subject'],
            body=contenu['body'],
        )
        return Response(EmailCandidatureSerializer(email).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def preparer_emails(self, request):
        if not isinstance(request.data, dict):
            return Response({'detail': 'Un objet JSON est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        lignes = request.data.get('emails')
        if not isinstance(lignes, list) or not lignes:
            return Response({'detail': 'Selectionnez au moins une candidature.'}, status=status.HTTP_400_BAD_REQUEST)

        commun = PreparationEmailsMasseCommunSerializer(data=request.data)
        if not commun.is_valid():
            return Response({'common_errors': commun.errors}, status=status.HTTP_400_BAD_REQUEST)

        erreurs = []
        donnees = []
        ids_vus = set()
        for index, brute in enumerate(lignes):
            candidature_id = brute.get('candidature_id') if isinstance(brute, dict) else None
            if not isinstance(brute, dict):
                erreurs.append({'index': index, 'candidature_id': None, 'errors': {'candidature_id': ['Une candidature est requise.']}})
                continue
            serializer = PreparationEmailMasseLigneSerializer(data={**brute, **commun.validated_data})
            if not serializer.is_valid():
                erreurs.append({'index': index, 'candidature_id': candidature_id, 'errors': serializer.errors})
                continue
            ligne = serializer.validated_data
            candidature_id = ligne['candidature_id']
            if candidature_id in ids_vus:
                erreurs.append({'index': index, 'candidature_id': candidature_id, 'errors': {'candidature_id': ['Candidature selectionnee plusieurs fois.']}})
                continue
            ids_vus.add(candidature_id)
            donnees.append((index, ligne))

        with transaction.atomic():
            accessibles = self.get_queryset().select_for_update().in_bulk(ids_vus)
            for index, ligne in donnees:
                candidature_id = ligne['candidature_id']
                if candidature_id not in accessibles:
                    erreurs.append({'index': index, 'candidature_id': candidature_id, 'errors': {'candidature_id': ['Candidature introuvable ou non autorisee.']}})
            if erreurs:
                return Response({'row_errors': sorted(erreurs, key=lambda erreur: erreur['index'])}, status=status.HTTP_400_BAD_REQUEST)

            emails = []
            for _index, ligne in donnees:
                candidature = accessibles[ligne['candidature_id']]
                contenu = preparer_contenu_email(
                    entreprise=candidature.entreprise,
                    nom_contact=ligne.get('nom_contact', ''),
                    prenom_contact=ligne.get('prenom_contact', ''),
                    civilite=ligne.get('civilite', ''),
                    poste=candidature.titre,
                    formation=ligne['formation'],
                    portfolio_url=ligne['portfolio_url'],
                    github_url=ligne['github_url'],
                )
                recipient_name = ' '.join(part for part in (
                    ligne.get('prenom_contact', '').strip(),
                    ligne.get('nom_contact', '').strip(),
                ) if part)
                emails.append(EmailCandidature.objects.create(
                    candidature=candidature,
                    recipient_email=ligne['recipient_email'],
                    recipient_name=recipient_name,
                    subject=contenu['subject'],
                    body=contenu['body'],
                ))
        return Response({'emails': EmailCandidatureSerializer(emails, many=True).data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def emails(self, request, pk=None):
        candidature = self.get_object()
        return Response(EmailCandidatureSerializer(candidature.emails.all(), many=True).data)

    @action(detail=True, methods=['patch'], url_path=r'emails/(?P<email_id>[^/.]+)')
    def email_item(self, request, pk=None, email_id=None):
        candidature = self.get_object()
        with transaction.atomic():
            email = get_object_or_404(candidature.emails.select_for_update(), pk=email_id)
            if email.status != EmailCandidature.Status.DRAFT:
                return Response({'detail': 'Ce brouillon ne peut plus etre modifie.'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = EmailCandidatureSerializer(email, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path=r'emails/(?P<email_id>[^/.]+)/annuler')
    def annuler_email(self, request, pk=None, email_id=None):
        candidature = self.get_object()
        with transaction.atomic():
            email = get_object_or_404(candidature.emails.select_for_update(), pk=email_id)
            if email.status != EmailCandidature.Status.DRAFT:
                return Response({'detail': 'Ce brouillon ne peut plus etre annule.'}, status=status.HTTP_400_BAD_REQUEST)
            email.status = EmailCandidature.Status.CANCELLED
            email.save(update_fields=['status', 'updated_at'])
        return Response(EmailCandidatureSerializer(email).data)

    @action(detail=True, methods=['post'], url_path=r'emails/(?P<email_id>[^/.]+)/preparer_envoi')
    def preparer_envoi_email(self, request, pk=None, email_id=None):
        candidature = self.get_object()
        with transaction.atomic():
            email = get_object_or_404(candidature.emails.select_for_update(), pk=email_id)
            if email.status != EmailCandidature.Status.DRAFT:
                return Response({'detail': 'Ce brouillon ne peut plus etre prepare.'}, status=status.HTTP_400_BAD_REQUEST)
            if not CVUtilisateur.objects.filter(utilisateur=request.user).exists():
                return Response({'detail': 'Configurez un CV par defaut avant de preparer l’envoi.'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = EmailCandidatureSerializer(email, data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.save(status=EmailCandidature.Status.READY)
        return Response(EmailCandidatureSerializer(email).data)

    def _email_action_target(self, request, email_id):
        candidature = self.get_object()
        if request.data.get('confirmation') is not True:
            return None, Response({'detail': 'Confirmation explicite requise.'}, status=status.HTTP_400_BAD_REQUEST)
        return get_object_or_404(candidature.emails.all(), pk=email_id), None

    @action(detail=True, methods=['post'], url_path=r'emails/(?P<email_id>[^/.]+)/envoyer')
    def envoyer_email(self, request, pk=None, email_id=None):
        email, error = self._email_action_target(request, email_id)
        if error is not None:
            return error
        try:
            updated, code = envoyer_email(email, request.user, request.data.get('cv_fingerprint'))
        except EmailSendError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)
        return Response(EmailCandidatureSerializer(updated).data, status=code)

    @action(detail=True, methods=['post'], url_path=r'emails/(?P<email_id>[^/.]+)/confirmer_manuellement')
    def confirmer_email_manuellement(self, request, pk=None, email_id=None):
        email, error = self._email_action_target(request, email_id)
        if error is not None:
            return error
        try:
            updated = confirmer_manuellement(email)
        except EmailSendError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)
        return Response(EmailCandidatureSerializer(updated).data)

    @action(detail=True, methods=['post'], url_path=r'emails/(?P<email_id>[^/.]+)/nouvelle_tentative')
    def nouvelle_tentative_email(self, request, pk=None, email_id=None):
        email, error = self._email_action_target(request, email_id)
        if error is not None:
            return error
        try:
            updated, created = nouvelle_tentative(email)
        except EmailSendError as exc:
            return Response({'detail': exc.detail}, status=exc.status_code)
        return Response(EmailCandidatureSerializer(updated).data, status=201 if created else 200)

    @action(detail=True, methods=['get', 'post'], url_path='actions')
    def actions(self, request, pk=None):
        candidature = self.get_object()
        if request.method == 'GET':
            serializer = ActionCandidatureSerializer(candidature.actions.all(), many=True)
            return Response(serializer.data)

        serializer = ActionCandidatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(candidature=candidature)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['get', 'put', 'patch', 'delete'],
        url_path=r'actions/(?P<action_id>[^/.]+)',
    )
    def action_item(self, request, pk=None, action_id=None):
        candidature = self.get_object()
        candidature_action = get_object_or_404(candidature.actions.all(), pk=action_id)
        if request.method == 'GET':
            return Response(ActionCandidatureSerializer(candidature_action).data)
        if request.method == 'DELETE':
            candidature_action.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ActionCandidatureSerializer(
            candidature_action,
            data=request.data,
            partial=request.method == 'PATCH',
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def import_url(self, request):
        serializer = ImportCandidatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = normaliser_url(serializer.validated_data['url'])
        # Existing CRUD records may still contain tracking parameters.
        for candidature_id, existing_url in self.get_queryset().values_list('id', 'url').iterator():
            try:
                normalized_existing_url = normaliser_url(existing_url)
            except ValueError:
                continue
            if normalized_existing_url == url:
                return Response({'duplicate': True, 'candidature_id': candidature_id})
        contexte = {}
        result = scraper_candidature(url, contexte=contexte)
        if result is None:
            result = extraire_candidature_llm(request.user, contexte.get('html', ''))
        return Response({'url': url, **(result or formulaire_vide())})


class RecommandationIAView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        taches = Tache.objects.filter(utilisateur=request.user).select_related('categorie')
        preferences = PreferenceUtilisateur.objects.filter(utilisateur=request.user).first()
        try:
            prompt = construire_prompt(taches, preferences)
        except Exception as error:
            logger.warning('Construction de recommandation IA indisponible: %s', type(error).__name__)
            return Response(_recommandation_meilleur_moment(request.user))

        purger_journaux_si_necessaire()
        cle_cache = construire_cle_cache(request.user, taches, preferences)
        recommandation = obtenir_cache(request.user, cle_cache)
        if _recommandation_valide(recommandation):
            journaliser_appel_llm(
                request.user,
                prompt,
                status='cache_hit',
                cache_hit=True,
            )
            return Response(recommandation)

        reservation = reserver_appel_llm(request.user, prompt)
        if reservation is None:
            recommandation = obtenir_derniere_cache_valide(request.user)
            if _recommandation_valide(recommandation):
                journaliser_appel_llm(
                    request.user,
                    prompt,
                    status='quota_cache',
                    cache_hit=True,
                )
                return Response(recommandation)

            recommandation = _recommandation_meilleur_moment(request.user)
            journaliser_appel_llm(
                request.user,
                prompt,
                status='quota_fallback',
                cache_hit=False,
            )
            return Response(recommandation)

        debut = time.monotonic()
        try:
            texte_llm = appeler_llm(prompt)
            recommandation = parser_reponse(texte_llm) if texte_llm else None
        except Exception as error:
            duree_ms = round((time.monotonic() - debut) * 1000)
            finaliser_appel_llm(
                reservation,
                success=False,
                duration_ms=duree_ms,
                error_type=type(error).__name__,
            )
            logger.warning('Appel de recommandation IA indisponible: %s', type(error).__name__)
            return Response(_recommandation_meilleur_moment(request.user))

        duree_ms = round((time.monotonic() - debut) * 1000)
        if not _recommandation_valide(recommandation):
            finaliser_appel_llm(
                reservation,
                success=False,
                duration_ms=duree_ms,
                error_type='InvalidResponse' if texte_llm else 'LLMUnavailable',
            )
            return Response(_recommandation_meilleur_moment(request.user))

        try:
            ecrire_cache(request.user, cle_cache, recommandation)
        except Exception as error:
            logger.warning('Ecriture du cache de recommandation IA echouee: %s', type(error).__name__)
        finaliser_appel_llm(reservation, success=True, duration_ms=duree_ms)
        return Response(recommandation)


def _recommandation_valide(recommandation):
    return (
        isinstance(recommandation, dict)
        and isinstance(recommandation.get('heures_recommandees'), list)
        and isinstance(recommandation.get('message'), str)
    )

class CategorieViewSet(viewsets.ModelViewSet):
    serializer_class = CategorieSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Categorie.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)

class PreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = PreferenceUtilisateurSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PreferenceUtilisateur.objects.filter(utilisateur=self.request.user)

    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)
