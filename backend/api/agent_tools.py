from datetime import datetime

from django.core.exceptions import ValidationError
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from agenda.models import Categorie, Tache
from api.models import ActionCandidature, Candidature


def _datetime_iso(value):
    if value is None:
        return None
    return timezone.localtime(value).isoformat()


def _date_iso(value):
    return value.isoformat() if value is not None else None


def _serialize_task(task):
    return {
        'id': task.id,
        'titre': task.titre,
        'description': task.description,
        'date_echeance': _datetime_iso(task.date_echeance),
        'priorite': task.priorite,
        'completee': task.completee,
        'categorie_id': task.categorie_id,
        'categorie_nom': task.categorie.nom if task.categorie else None,
    }


def _parse_due_date(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = parse_datetime(value)
    else:
        parsed = None

    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def _get_category(user, category_id):
    if category_id is None:
        return None
    return Categorie.objects.filter(utilisateur=user, pk=category_id).first()


def get_today_tasks(user):
    tasks = (
        Tache.objects.filter(
            utilisateur=user,
            date_echeance__date=timezone.localdate(),
        )
        .select_related('categorie')
        .order_by('date_echeance', '-priorite', 'id')
    )

    return {
        'succes': True,
        'taches': [
            _serialize_task(task)
            for task in tasks
        ],
    }


def get_applications(user):
    latest_action = (
        ActionCandidature.objects.filter(candidature=OuterRef('pk'))
        .order_by('-date_action', '-id')
        .values('date_action')[:1]
    )
    applications = (
        Candidature.objects.filter(utilisateur=user, archive=False)
        .annotate(date_derniere_action=Subquery(latest_action))
        .order_by('-date_ajout', '-id')
    )

    return {
        'succes': True,
        'candidatures': [
            {
                'id': application.id,
                'titre': application.titre,
                'entreprise': application.entreprise,
                'description': application.description,
                'type_poste': application.type_poste,
                'statut': application.statut,
                'source_canal': application.source_canal,
                'tags': application.tags,
                'favori': application.favori,
                'date_limite': _date_iso(application.date_limite),
                'date_relance': _date_iso(application.date_relance),
                'date_derniere_action': _datetime_iso(application.date_derniere_action),
            }
            for application in applications
        ],
    }


def create_task(user, *, titre, priorite, date_echeance, categorie_id=None):
    category = _get_category(user, categorie_id)
    if categorie_id is not None and category is None:
        return {'succes': False, 'erreur': 'Categorie introuvable.'}

    parsed_due_date = _parse_due_date(date_echeance)
    if (
        not isinstance(titre, str)
        or not titre.strip()
        or type(priorite) is not int
        or priorite not in dict(Tache.PRIORITE_CHOICES)
        or parsed_due_date is None
    ):
        return {'succes': False, 'erreur': 'Donnees de tache invalides.'}

    task = Tache(
        utilisateur=user,
        titre=titre.strip(),
        priorite=priorite,
        date_echeance=parsed_due_date,
        categorie=category,
    )
    try:
        task.full_clean()
        task.save()
    except ValidationError:
        return {'succes': False, 'erreur': 'Donnees de tache invalides.'}

    return {'succes': True, 'tache': _serialize_task(task)}


def update_task(user, *, tache_id, **changes):
    task = Tache.objects.select_related('categorie').filter(
        utilisateur=user,
        pk=tache_id,
    ).first()
    if task is None:
        return {'succes': False, 'erreur': 'Tache introuvable.'}

    allowed_fields = {
        'titre',
        'description',
        'date_echeance',
        'priorite',
        'categorie_id',
        'couleur',
        'emoji',
        'completee',
    }
    if not changes or set(changes) - allowed_fields:
        return {'succes': False, 'erreur': 'Champs de modification invalides.'}

    if 'categorie_id' in changes:
        category_id = changes.pop('categorie_id')
        category = _get_category(user, category_id)
        if category_id is not None and category is None:
            return {'succes': False, 'erreur': 'Categorie introuvable.'}
        task.categorie = category

    if 'date_echeance' in changes:
        parsed_due_date = _parse_due_date(changes['date_echeance'])
        if parsed_due_date is None:
            return {'succes': False, 'erreur': 'Donnees de tache invalides.'}
        changes['date_echeance'] = parsed_due_date

    if 'titre' in changes:
        if not isinstance(changes['titre'], str) or not changes['titre'].strip():
            return {'succes': False, 'erreur': 'Donnees de tache invalides.'}
        changes['titre'] = changes['titre'].strip()

    if 'priorite' in changes and (
        type(changes['priorite']) is not int
        or changes['priorite'] not in dict(Tache.PRIORITE_CHOICES)
    ):
        return {'succes': False, 'erreur': 'Donnees de tache invalides.'}

    if 'completee' in changes and type(changes['completee']) is not bool:
        return {'succes': False, 'erreur': 'Donnees de tache invalides.'}

    for field, value in changes.items():
        setattr(task, field, value)

    try:
        task.full_clean()
        task.save()
    except ValidationError:
        return {'succes': False, 'erreur': 'Donnees de tache invalides.'}

    return {'succes': True, 'tache': _serialize_task(task)}
