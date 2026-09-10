from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from api.models import EntreeCacheRecommandation, JournalAppelLLM


class EntreeCacheRecommandationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')

    def test_cache_key_is_unique_across_cache_entries(self):
        EntreeCacheRecommandation.objects.create(
            utilisateur=self.user,
            cle='llm_reco:1:abc123',
            recommandation={'heures_recommandees': [9], 'message': 'Travaillez a 9h.'},
            expire_a=timezone.now() + timedelta(hours=24),
        )

        with self.assertRaises(IntegrityError):
            EntreeCacheRecommandation.objects.create(
                utilisateur=self.user,
                cle='llm_reco:1:abc123',
                recommandation={'heures_recommandees': [14], 'message': 'Travaillez a 14h.'},
                expire_a=timezone.now() + timedelta(hours=24),
            )

    def test_valid_cache_query_is_scoped_to_user_and_expiry(self):
        now = timezone.now()
        other_user = User.objects.create_user(username='bob', password='secret-password')
        active_entry = EntreeCacheRecommandation.objects.create(
            utilisateur=self.user,
            cle='llm_reco:1:active',
            recommandation={'heures_recommandees': [9], 'message': 'Travaillez a 9h.'},
            expire_a=now + timedelta(hours=1),
        )
        EntreeCacheRecommandation.objects.create(
            utilisateur=self.user,
            cle='llm_reco:1:expired',
            recommandation={'heures_recommandees': [], 'message': 'Expiree.'},
            expire_a=now - timedelta(seconds=1),
        )
        EntreeCacheRecommandation.objects.create(
            utilisateur=other_user,
            cle='llm_reco:2:active',
            recommandation={'heures_recommandees': [14], 'message': 'Autre utilisateur.'},
            expire_a=now + timedelta(hours=1),
        )

        entries = EntreeCacheRecommandation.objects.filter(
            utilisateur=self.user,
            expire_a__gt=now,
        )

        self.assertEqual(list(entries), [active_entry])


class JournalAppelLLMModelTests(TestCase):
    def test_log_allows_a_missing_duration_when_no_external_call_was_made(self):
        journal = JournalAppelLLM(
            user_hash='a' * 64,
            prompt_hash='b' * 64,
            prompt_length=1,
            status=JournalAppelLLM.Status.CACHE_HIT,
            cache_hit=True,
        )

        journal.full_clean()
        journal.save()

        self.assertIsNone(journal.duration_ms)

    def test_log_persists_only_privacy_preserving_fields(self):
        journal = JournalAppelLLM.objects.create(
            user_hash='a' * 64,
            prompt_hash='b' * 64,
            prompt_length=312,
            duration_ms=245,
            status=JournalAppelLLM.Status.SUCCESS,
            cache_hit=False,
        )

        journal.refresh_from_db()

        self.assertEqual(journal.user_hash, 'a' * 64)
        self.assertEqual(journal.prompt_hash, 'b' * 64)
        self.assertEqual(journal.prompt_length, 312)
        self.assertEqual(journal.duration_ms, 245)
        self.assertEqual(journal.status, 'success')
        self.assertFalse(journal.cache_hit)
        self.assertEqual(journal.error_type, '')
        self.assertIsNotNone(journal.created_at)

        foreign_keys = [
            field for field in JournalAppelLLM._meta.fields
            if field.remote_field is not None
        ]
        self.assertEqual(foreign_keys, [])

    def test_log_rejects_an_unknown_status(self):
        journal = JournalAppelLLM(
            user_hash='a' * 64,
            prompt_hash='b' * 64,
            prompt_length=1,
            status='unknown',
            cache_hit=False,
        )

        with self.assertRaises(ValidationError):
            journal.full_clean()

    def test_database_rejects_an_unknown_status(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalAppelLLM.objects.create(
                    user_hash='a' * 64,
                    prompt_hash='b' * 64,
                    prompt_length=1,
                    status='unknown',
                    cache_hit=False,
                )
