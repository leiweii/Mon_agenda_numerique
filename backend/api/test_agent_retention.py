import importlib.util
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from api.models import ActionEnAttente, ConversationAgent


class AgentPendingActionRetentionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent-retention-owner')
        self.conversation = ConversationAgent.objects.create(utilisateur=self.user)

    def create_action(self, title):
        return ActionEnAttente.objects.create(
            conversation=self.conversation,
            utilisateur=self.user,
            tool_name='create_task',
            arguments={'titre': title, 'priorite': 2},
        )

    def test_probabilistic_purge_expires_only_pending_actions_older_than_24_hours(self):
        self.assertIsNotNone(importlib.util.find_spec('api.agent_retention'))
        from api.agent_retention import purger_actions_si_necessaire

        now = timezone.now()
        old_action = self.create_action('Ancienne')
        recent_action = self.create_action('Recente')
        already_confirmed = self.create_action('Deja confirmee')
        ActionEnAttente.objects.filter(pk=old_action.pk).update(
            date_creation=now - timedelta(hours=24, seconds=1),
        )
        ActionEnAttente.objects.filter(pk=already_confirmed.pk).update(
            date_creation=now - timedelta(days=2),
            statut=ActionEnAttente.Statut.CONFIRMEE,
            date_traitement=now - timedelta(days=1),
        )

        with patch('api.agent_retention.secrets.randbelow', return_value=0) as randbelow:
            expired_count = purger_actions_si_necessaire(now=now)

        old_action.refresh_from_db()
        recent_action.refresh_from_db()
        already_confirmed.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(old_action.statut, ActionEnAttente.Statut.EXPIREE)
        self.assertEqual(old_action.date_traitement, now)
        self.assertEqual(recent_action.statut, ActionEnAttente.Statut.EN_ATTENTE)
        self.assertEqual(already_confirmed.statut, ActionEnAttente.Statut.CONFIRMEE)
        randbelow.assert_called_once_with(100)
