"""Services persistants de cache, quota et journalisation des appels LLM."""

import hashlib
import hmac
import json
import logging
import re
import secrets
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from api.models import EntreeCacheRecommandation, JournalAppelLLM


logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=24)
RETENTION_DAYS = 30
DAILY_LLM_LIMIT = 10
EXTERNAL_CALL_STATUSES = [JournalAppelLLM.Status.SUCCESS, JournalAppelLLM.Status.ERROR]
PREFERENCE_FIELDS = (
    'heure_productive_debut',
    'heure_productive_fin',
    'theme',
    'notifications_actives',
)


def construire_cle_cache(utilisateur, taches, preferences):
    """Retourne la cle stable du cache pour les taches et preferences fournies."""
    task_ids = sorted(
        task['id'] if isinstance(task, dict) else task.pk
        for task in taches
    )
    preference_values = {
        field: _serialiser_valeur_preference(_lire_champ(preferences, field))
        for field in PREFERENCE_FIELDS
    }
    payload = json.dumps(
        {'taches_ids': task_ids, 'preferences': preference_values},
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f'llm_reco:{utilisateur.pk}:{digest}'


def obtenir_cache(utilisateur, cle, now=None):
    """Retourne la recommandation valide d'un utilisateur pour une cle, sinon ``None``."""
    now = now or timezone.now()
    entry = EntreeCacheRecommandation.objects.filter(
        utilisateur=utilisateur,
        cle=cle,
        expire_a__gt=now,
    ).first()
    return entry.recommandation if entry else None


def obtenir_derniere_cache_valide(utilisateur, now=None):
    """Retourne la plus recente recommandation valide d'un utilisateur, sinon ``None``."""
    now = now or timezone.now()
    entry = EntreeCacheRecommandation.objects.filter(
        utilisateur=utilisateur,
        expire_a__gt=now,
    ).order_by('-created_at').first()
    return entry.recommandation if entry else None


def ecrire_cache(utilisateur, cle, recommandation, now=None):
    """Persiste le cache d'un utilisateur pour 24 heures, sans ecraser celui d'un autre.

    Retourne ``None`` lorsqu'une cle deja existante appartient a un autre utilisateur,
    y compris apres une collision d'insertion concurrente.
    """
    now = now or timezone.now()
    with transaction.atomic():
        entry = EntreeCacheRecommandation.objects.select_for_update().filter(cle=cle).first()
        if entry is None:
            try:
                with transaction.atomic():
                    return EntreeCacheRecommandation.objects.create(
                        utilisateur=utilisateur,
                        cle=cle,
                        recommandation=recommandation,
                        expire_a=now + CACHE_TTL,
                    )
            except IntegrityError:
                entry = EntreeCacheRecommandation.objects.filter(
                    utilisateur=utilisateur,
                    cle=cle,
                ).first()
                if entry is not None:
                    return entry
                if EntreeCacheRecommandation.objects.filter(cle=cle).exists():
                    return None
                raise
        if entry.utilisateur_id != utilisateur.pk:
            return None
        entry.recommandation = recommandation
        entry.expire_a = now + CACHE_TTL
        entry.save(update_fields=['recommandation', 'expire_a'])
        return entry


def invalider_cache_utilisateur(utilisateur_id):
    """Supprime toutes les entrees de cache d'un utilisateur et retourne leur nombre."""
    deleted_count, _ = EntreeCacheRecommandation.objects.filter(
        utilisateur_id=utilisateur_id,
    ).delete()
    return deleted_count


def hacher_utilisateur(utilisateur):
    """Retourne le HMAC-SHA256 pseudonymisant l'identifiant utilisateur."""
    user_id = getattr(utilisateur, 'pk', utilisateur)
    return hmac.new(
        settings.SECRET_KEY.encode(),
        str(user_id).encode(),
        hashlib.sha256,
    ).hexdigest()


def hacher_prompt(prompt):
    """Retourne le SHA-256 du prompt sans le persister."""
    return hashlib.sha256(prompt.encode()).hexdigest()


def journaliser_appel_llm(
    utilisateur,
    prompt,
    *,
    status,
    cache_hit,
    duration_ms=None,
    error_type='',
    now=None,
    usage=JournalAppelLLM.Usage.RECOMMANDATION,
):
    """Cree un journal ne contenant que des metadonnees hachees de l'appel."""
    journal = JournalAppelLLM.objects.create(
        user_hash=hacher_utilisateur(utilisateur),
        usage=usage,
        prompt_hash=hacher_prompt(prompt),
        prompt_length=len(prompt),
        duration_ms=duration_ms,
        status=status,
        cache_hit=cache_hit,
        error_type=_normaliser_error_type(error_type),
    )
    if now is not None:
        JournalAppelLLM.objects.filter(pk=journal.pk).update(created_at=now)
        journal.created_at = now
    return journal


def quota_disponible(utilisateur, now=None, *, usage=JournalAppelLLM.Usage.RECOMMANDATION):
    """Indique si l'utilisateur peut encore reserver un appel LLM aujourd'hui."""
    now = now or timezone.now()
    start, end = _bornes_jour_local(now)
    if usage not in JournalAppelLLM.Usage.values:
        raise ValueError('Usage LLM inconnu')
    limit = settings.CANDIDATURE_LLM_DAILY_LIMIT if usage == JournalAppelLLM.Usage.CANDIDATURE else DAILY_LLM_LIMIT
    return JournalAppelLLM.objects.filter(
        user_hash=hacher_utilisateur(utilisateur),
        usage=usage,
        created_at__gte=start,
        created_at__lt=end,
        status__in=EXTERNAL_CALL_STATUSES,
    ).count() < limit


def reserver_appel_llm(utilisateur, prompt, now=None, *, usage=JournalAppelLLM.Usage.RECOMMANDATION):
    """Reserve atomiquement un appel externe, ou retourne ``None`` si le quota est atteint.

    La reservation est journalisee comme une erreur temporaire puis doit etre finalisee
    par ``finaliser_appel_llm`` apres l'appel externe.
    """
    now = now or timezone.now()
    user_model = get_user_model()
    with transaction.atomic():
        locked_user = user_model.objects.select_for_update().get(pk=utilisateur.pk)
        if not quota_disponible(locked_user, now=now, usage=usage):
            return None
        return journaliser_appel_llm(
            locked_user,
            prompt,
            status=JournalAppelLLM.Status.ERROR,
            cache_hit=False,
            error_type='reservation',
            now=now,
            usage=usage,
        )


def finaliser_appel_llm(journal, *, success, duration_ms, error_type=''):
    """Finalise une reservation LLM avec son statut et ses seules metadonnees admises."""
    journal.status = JournalAppelLLM.Status.SUCCESS if success else JournalAppelLLM.Status.ERROR
    journal.duration_ms = duration_ms
    journal.error_type = '' if success else _normaliser_error_type(error_type)
    journal.save(update_fields=['status', 'duration_ms', 'error_type'])
    return journal


def purger_journaux_anciens(now=None):
    """Supprime les journaux vieux de plus de trente jours et retourne leur nombre."""
    now = now or timezone.now()
    deleted_count, _ = JournalAppelLLM.objects.filter(
        created_at__lt=now - timedelta(days=RETENTION_DAYS),
    ).delete()
    return deleted_count


def purger_journaux_si_necessaire(now=None):
    """Declenche la purge dans environ un pour cent des requetes sans les interrompre."""
    if secrets.randbelow(100) != 0:
        return 0
    try:
        return purger_journaux_anciens(now=now)
    except Exception as error:
        logger.warning('LLM log retention purge failed: %s', type(error).__name__)
        return 0


def _lire_champ(source, field):
    if source is None:
        return None
    return source.get(field) if isinstance(source, dict) else getattr(source, field, None)


def _serialiser_valeur_preference(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def _bornes_jour_local(now):
    local_date = timezone.localdate(now)
    start = timezone.make_aware(datetime.combine(local_date, time.min))
    return start, start + timedelta(days=1)


def _normaliser_error_type(error_type):
    if not error_type:
        return ''
    if not isinstance(error_type, str):
        return type(error_type).__name__
    return error_type if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', error_type) else ''
