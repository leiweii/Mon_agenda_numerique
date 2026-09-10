import hashlib
import hmac
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone

from agenda.models import PreferenceUtilisateur, Tache
from api.models import EntreeCacheRecommandation, JournalAppelLLM
from api.llm_performance import (
    construire_cle_cache,
    ecrire_cache,
    obtenir_cache,
    obtenir_derniere_cache_valide,
    purger_journaux_si_necessaire,
    quota_disponible,
    reserver_appel_llm,
    journaliser_appel_llm,
)


@override_settings(SECRET_KEY='test-secret')
class LlmCacheServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.preference = PreferenceUtilisateur.objects.create(
            utilisateur=self.user,
            heure_productive_debut='09:00',
            heure_productive_fin='17:00',
            theme='clair',
            notifications_actives=True,
        )
        self.first_task = Tache.objects.create(
            utilisateur=self.user,
            titre='Premiere tache',
            date_echeance=timezone.now(),
        )
        self.second_task = Tache.objects.create(
            utilisateur=self.user,
            titre='Seconde tache',
            date_echeance=timezone.now(),
        )

    def test_cache_key_uses_sorted_task_ids_and_canonical_preferences(self):
        key_in_order = construire_cle_cache(
            self.user,
            [self.first_task, self.second_task],
            self.preference,
        )
        key_reversed = construire_cle_cache(
            self.user,
            [self.second_task, self.first_task],
            self.preference,
        )

        self.preference.theme = 'sombre'
        key_with_changed_preferences = construire_cle_cache(
            self.user,
            [self.first_task, self.second_task],
            self.preference,
        )

        self.assertEqual(key_in_order, key_reversed)
        self.assertTrue(key_in_order.startswith(f'llm_reco:{self.user.id}:'))
        self.assertEqual(len(key_in_order.rsplit(':', 1)[1]), 64)
        self.assertNotEqual(key_in_order, key_with_changed_preferences)

    def test_cache_returns_a_valid_entry_and_excludes_expired_entries(self):
        now = timezone.now()
        key = 'llm_reco:1:active'
        recommendation = {'heures_recommandees': [9], 'message': 'Travaillez a 9h.'}

        entry = ecrire_cache(self.user, key, recommendation, now=now)
        EntreeCacheRecommandation.objects.create(
            utilisateur=self.user,
            cle='llm_reco:1:expired',
            recommandation={'heures_recommandees': [], 'message': 'Expiree.'},
            expire_a=now - timedelta(seconds=1),
        )

        self.assertEqual(entry.expire_a, now + timedelta(hours=24))
        self.assertEqual(obtenir_cache(self.user, key, now=now), recommendation)
        self.assertIsNone(obtenir_cache(self.user, 'llm_reco:1:expired', now=now))
        self.assertEqual(obtenir_derniere_cache_valide(self.user, now=now), recommendation)

    def test_cache_entry_cannot_be_read_or_replaced_by_another_user(self):
        other_user = User.objects.create_user(username='bob', password='secret-password')
        key = 'llm_reco:2:other-user-entry'
        other_recommendation = {'heures_recommandees': [14], 'message': 'Reserve a Bob.'}
        own_recommendation = {'heures_recommandees': [9], 'message': 'Reserve a Alice.'}
        foreign_entry = ecrire_cache(other_user, key, other_recommendation)

        result = ecrire_cache(self.user, key, own_recommendation)

        foreign_entry.refresh_from_db()
        self.assertIsNone(obtenir_cache(self.user, key))
        self.assertEqual(obtenir_cache(other_user, key), other_recommendation)
        self.assertIsNone(result)
        self.assertEqual(foreign_entry.recommandation, other_recommendation)

    def test_cache_returns_existing_user_entry_after_a_concurrent_create_collision(self):
        key = 'llm_reco:1:concurrent-entry'
        existing_recommendation = {'heures_recommandees': [14], 'message': 'Deja ecrite.'}
        existing_entry = EntreeCacheRecommandation.objects.create(
            utilisateur=self.user,
            cle=key,
            recommandation=existing_recommendation,
            expire_a=timezone.now() + timedelta(hours=24),
        )

        with patch.object(EntreeCacheRecommandation.objects, 'select_for_update') as select_for_update, patch.object(
            EntreeCacheRecommandation.objects,
            'create',
            side_effect=IntegrityError,
        ):
            select_for_update.return_value.filter.return_value.first.return_value = None

            result = ecrire_cache(
                self.user,
                key,
                {'heures_recommandees': [9], 'message': 'Nouvelle recommandation.'},
            )

        self.assertEqual(result.pk, existing_entry.pk)
        self.assertEqual(result.recommandation, existing_recommendation)

    def test_reservation_stops_after_ten_external_calls_but_ignores_cache_logs(self):
        now = timezone.now()
        journaliser_appel_llm(
            self.user,
            prompt='cache prompt',
            status=JournalAppelLLM.Status.CACHE_HIT,
            cache_hit=True,
            now=now,
        )
        journaliser_appel_llm(
            self.user,
            prompt='quota prompt',
            status=JournalAppelLLM.Status.QUOTA_FALLBACK,
            cache_hit=False,
            now=now,
        )

        reservations = [
            reserver_appel_llm(self.user, prompt=f'prompt {index}', now=now)
            for index in range(10)
        ]

        self.assertTrue(all(reservations))
        self.assertFalse(quota_disponible(self.user, now=now))
        self.assertIsNone(reserver_appel_llm(self.user, prompt='prompt 11', now=now))

    def test_log_hashes_user_and_prompt_without_storing_plaintext(self):
        prompt = 'Projet medical confidentiel'
        journal = journaliser_appel_llm(
            self.user,
            prompt=prompt,
            duration_ms=250,
            status=JournalAppelLLM.Status.SUCCESS,
            cache_hit=False,
        )

        expected_user_hash = hmac.new(
            b'test-secret', str(self.user.id).encode(), hashlib.sha256,
        ).hexdigest()

        self.assertEqual(journal.user_hash, expected_user_hash)
        self.assertEqual(journal.prompt_hash, hashlib.sha256(prompt.encode()).hexdigest())
        self.assertEqual(journal.prompt_length, len(prompt))
        self.assertEqual(journal.duration_ms, 250)
        self.assertNotIn('prompt', {field.name for field in JournalAppelLLM._meta.fields})
        self.assertNotIn('response', {field.name for field in JournalAppelLLM._meta.fields})

    @patch('api.llm_performance.secrets.randbelow', return_value=0)
    def test_probabilistic_purge_removes_only_logs_older_than_thirty_days(self, randbelow):
        now = timezone.now()
        old_log = journaliser_appel_llm(
            self.user,
            prompt='old prompt',
            status=JournalAppelLLM.Status.SUCCESS,
            cache_hit=False,
            now=now,
        )
        recent_log = journaliser_appel_llm(
            self.user,
            prompt='recent prompt',
            status=JournalAppelLLM.Status.SUCCESS,
            cache_hit=False,
            now=now,
        )
        JournalAppelLLM.objects.filter(pk=old_log.pk).update(
            created_at=now - timedelta(days=31),
        )

        deleted_count = purger_journaux_si_necessaire(now=now)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(JournalAppelLLM.objects.filter(pk=old_log.pk).exists())
        self.assertTrue(JournalAppelLLM.objects.filter(pk=recent_log.pk).exists())
        randbelow.assert_called_once_with(100)

    @patch('api.llm_performance.purger_journaux_anciens', side_effect=RuntimeError('prompt confidentiel'))
    @patch('api.llm_performance.secrets.randbelow', return_value=0)
    def test_probabilistic_purge_returns_zero_when_purge_fails(self, randbelow, purge):
        with self.assertLogs('api.llm_performance', level='WARNING') as logs:
            result = purger_journaux_si_necessaire()

        self.assertEqual(result, 0)
        self.assertEqual(len(logs.output), 1)
        self.assertIn('RuntimeError', logs.output[0])
        self.assertNotIn('prompt confidentiel', logs.output[0])
        randbelow.assert_called_once_with(100)


class LlmCacheInvalidationSignalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.task = Tache.objects.create(
            utilisateur=self.user,
            titre='Tache a modifier',
            date_echeance=timezone.now(),
        )
        self.preference = PreferenceUtilisateur.objects.create(utilisateur=self.user)

    def create_cache_entry(self, suffix):
        return EntreeCacheRecommandation.objects.create(
            utilisateur=self.user,
            cle=f'llm_reco:{self.user.id}:{suffix}',
            recommandation={'heures_recommandees': [], 'message': 'Cache.'},
            expire_a=timezone.now() + timedelta(hours=24),
        )

    def test_task_save_invalidates_all_of_the_users_cache_entries(self):
        self.create_cache_entry('task-save')

        self.task.titre = 'Tache modifiee'
        self.task.save()

        self.assertFalse(EntreeCacheRecommandation.objects.filter(utilisateur=self.user).exists())

    def test_task_delete_invalidates_all_of_the_users_cache_entries(self):
        self.create_cache_entry('task-delete')

        self.task.delete()

        self.assertFalse(EntreeCacheRecommandation.objects.filter(utilisateur=self.user).exists())

    def test_preference_save_invalidates_all_of_the_users_cache_entries(self):
        self.create_cache_entry('preference-save')

        self.preference.theme = 'sombre'
        self.preference.save()

        self.assertFalse(EntreeCacheRecommandation.objects.filter(utilisateur=self.user).exists())

    def test_preference_delete_invalidates_all_of_the_users_cache_entries(self):
        self.create_cache_entry('preference-delete')

        self.preference.delete()

        self.assertFalse(EntreeCacheRecommandation.objects.filter(utilisateur=self.user).exists())
