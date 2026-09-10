from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging
import time
from agenda.models import Tache, Categorie, PreferenceUtilisateur, StatistiqueUtilisation
from .serializers import TacheSerializer, CategorieSerializer, PreferenceUtilisateurSerializer
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
