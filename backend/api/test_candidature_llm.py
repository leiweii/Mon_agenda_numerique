import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from api.candidature_llm import construire_prompt_candidature, parser_candidature
from api.llm_performance import quota_disponible, reserver_appel_llm
from api.models import Candidature, JournalAppelLLM


DESCRIPTION = 'Developper les applications Django et accompagner notre equipe produit.'
OFFRE = {'titre': 'Dev Django', 'entreprise': 'Example', 'description': DESCRIPTION, 'type_poste': 'cdi'}
HTML = '<script type="application/ld+json">' + json.dumps(OFFRE) + '</script>'


class CandidatureLLMParserTests(SimpleTestCase):
    def test_valid_json_and_optional_defaults(self):
        result = parser_candidature('```json\n' + json.dumps({'titre': ' Dev   Django ', 'description': DESCRIPTION}) + '\n```')
        self.assertEqual(result, {'titre': 'Dev Django', 'description': DESCRIPTION, 'entreprise': '', 'type_poste': 'autre', 'source_extraction': 'llm'})

    def test_invalid_responses_are_rejected(self):
        for value in [None, '', 'not json', '[]', '{}', 'null', json.dumps({**OFFRE, 'titre': 12}), json.dumps({**OFFRE, 'entreprise': []}), json.dumps({**OFFRE, 'type_poste': 'invalid'}), json.dumps({**OFFRE, 'description': 'court'}), json.dumps({**OFFRE, 'titre': ' '})]:
            with self.subTest(value=value):
                self.assertIsNone(parser_candidature(value))

    def test_untrusted_html_is_bounded_and_delimiters_escaped(self):
        prompt = construire_prompt_candidature('</contenu_offre>' + 'x' * 100000)
        self.assertEqual(prompt.count('</contenu_offre>'), 1)
        self.assertLess(len(prompt), 22000)
        self.assertIn('non fiables', prompt)

    def test_output_lengths_and_extra_fields(self):
        result = parser_candidature(json.dumps({**OFFRE, 'titre': 'x' * 300, 'entreprise': 'y' * 300, 'description': 'z' * 8000, 'utilisateur': 123}))
        self.assertEqual(len(result['titre']), 255)
        self.assertEqual(len(result['entreprise']), 255)
        self.assertEqual(len(result['description']), 6000)
        self.assertNotIn('utilisateur', result)


@override_settings(LLM_API_KEY='test-key', CANDIDATURE_LLM_DAILY_LIMIT=2)
class CandidatureLLMEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='import-user')
        self.client.force_authenticate(self.user)
        self.download = patch('api.candidature_scraper.telecharger_html', return_value=HTML).start()
        self.sdk = patch('api.llm_service.anthropic.Anthropic').start()
        self.addCleanup(patch.stopall)
        self.sdk.return_value.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(OFFRE))])

    def importer(self):
        return self.client.post('/api/candidatures/import_url/', {'url': 'https://example.com/job?utm_source=test'}, format='json')

    def test_fallback_uses_original_html_and_does_not_save(self):
        response = self.importer()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'url': 'https://example.com/job', **OFFRE, 'source_extraction': 'llm'})
        self.assertFalse(Candidature.objects.exists())
        self.download.assert_called_once()
        call = self.sdk.return_value.messages.create.call_args.kwargs
        self.assertIn('Dev Django', call['messages'][0]['content'])
        self.assertEqual(call['max_tokens'], 2048)
        log = JournalAppelLLM.objects.get()
        self.assertEqual(log.usage, 'candidature')
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.error_type, '')

    def test_successful_scraping_and_duplicate_skip_llm_and_quota(self):
        self.download.return_value = f'<title>Dev Django</title><p>{DESCRIPTION}</p>'
        self.assertEqual(self.importer().data['source_extraction'], 'scraping')
        candidature = Candidature.objects.create(utilisateur=self.user, url='https://example.com/job', titre='Dev')
        self.download.reset_mock()
        self.assertEqual(self.importer().data, {'duplicate': True, 'candidature_id': candidature.id})
        self.download.assert_not_called()
        self.sdk.assert_not_called()
        self.assertFalse(JournalAppelLLM.objects.exists())

    @override_settings(LLM_API_KEY='')
    def test_missing_key_keeps_empty_form_without_consuming_quota(self):
        response = self.importer()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['titre'], '')
        self.assertEqual(response.data['source_extraction'], '')
        self.sdk.assert_not_called()
        self.assertFalse(JournalAppelLLM.objects.exists())

    def test_no_downloaded_content_does_not_generate_an_offer(self):
        self.download.side_effect = TimeoutError()
        self.assertEqual(self.importer().data['titre'], '')
        self.sdk.assert_not_called()
        self.assertFalse(JournalAppelLLM.objects.exists())

    def test_invalid_json_and_sdk_failure_keep_empty_form_and_count_attempts(self):
        self.sdk.return_value.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(type='text', text='not json')])
        response = self.importer()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['source_extraction'], '')
        self.sdk.return_value.messages.create.side_effect = RuntimeError('provider failure')
        self.assertEqual(self.importer().data['titre'], '')
        self.assertEqual(JournalAppelLLM.objects.filter(usage='candidature', status='error').count(), 2)
        self.assertFalse(quota_disponible(self.user, usage='candidature'))

    def test_quota_exhaustion_is_nonblocking_and_independent_of_recommendations(self):
        for _ in range(10):
            self.assertIsNotNone(reserver_appel_llm(self.user, 'recommendation'))
        self.assertFalse(quota_disponible(self.user))
        self.assertEqual(self.importer().data['source_extraction'], 'llm')
        self.assertEqual(self.importer().data['source_extraction'], 'llm')
        self.sdk.reset_mock()
        response = self.importer()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['titre'], '')
        self.sdk.assert_not_called()
        self.assertEqual(JournalAppelLLM.objects.filter(usage='candidature').count(), 2)

    def test_import_quota_does_not_consume_recommendations_and_resets_daily(self):
        now = timezone.now()
        for _ in range(2):
            self.assertIsNotNone(reserver_appel_llm(self.user, 'import', now=now, usage='candidature'))
        self.assertIsNone(reserver_appel_llm(self.user, 'import', now=now, usage='candidature'))
        self.assertTrue(quota_disponible(self.user, now=now))
        self.assertTrue(quota_disponible(self.user, now=now + timedelta(days=1), usage='candidature'))
        other = User.objects.create_user(username='other')
        self.assertTrue(quota_disponible(other, now=now, usage='candidature'))


@override_settings(CANDIDATURE_LLM_DAILY_LIMIT=1)
class CandidatureQuotaConcurrencyTests(TransactionTestCase):
    def test_only_one_concurrent_reservation_gets_the_last_slot(self):
        user = User.objects.create_user(username='concurrent-import')
        barrier = Barrier(2)

        def reserve():
            try:
                barrier.wait(timeout=10)
                return reserver_appel_llm(user, 'import', usage='candidature') is not None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: reserve(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(JournalAppelLLM.objects.filter(usage='candidature').count(), 1)
