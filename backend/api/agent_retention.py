import logging
import secrets
from datetime import timedelta

from django.utils import timezone

from api.models import ActionEnAttente


logger = logging.getLogger(__name__)

ACTION_PENDING_TTL = timedelta(hours=24)


def expirer_actions_en_attente(now=None):
    """Marque comme expirees les actions en attente depuis plus de 24 heures."""
    now = now or timezone.now()
    return ActionEnAttente.objects.filter(
        statut=ActionEnAttente.Statut.EN_ATTENTE,
        date_creation__lt=now - ACTION_PENDING_TTL,
    ).update(
        statut=ActionEnAttente.Statut.EXPIREE,
        date_traitement=now,
    )


def purger_actions_si_necessaire(now=None):
    """Declenche la purge dans environ un pour cent des requetes agent."""
    if secrets.randbelow(100) != 0:
        return 0
    try:
        return expirer_actions_en_attente(now=now)
    except Exception as error:
        logger.warning('Agent pending action purge failed: %s', type(error).__name__)
        return 0


def expirer_action_si_necessaire(action, now=None):
    """Expire une action verrouillee si son delai est depasse."""
    now = now or timezone.now()
    if (
        action.statut == ActionEnAttente.Statut.EN_ATTENTE
        and action.date_creation < now - ACTION_PENDING_TTL
    ):
        action.statut = ActionEnAttente.Statut.EXPIREE
        action.date_traitement = now
        action.save(update_fields=['statut', 'date_traitement'])
        return True
    return False
