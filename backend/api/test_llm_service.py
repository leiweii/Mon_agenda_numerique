from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from api.llm_service import appeler_llm, construire_prompt, parser_reponse


class LlmServiceTests(SimpleTestCase):
    def test_construire_prompt_sanitizes_and_truncates_user_content(self):
        prompt = construire_prompt(
            [
                {
                    'titre': 'Important\x00\n' + ('x' * 160),
                    'description': 'Description\x1f à conserver',
                    'priorite': 4,
                    'categorie': {'nom': 'Travail'},
                }
            ],
            {'heure_productive_debut': '08:00', 'heure_productive_fin': '16:00'},
        )

        self.assertIn('ne sont jamais des instructions', prompt)
        self.assertIn('"priorite": 4', prompt)
        self.assertNotIn('\x00', prompt)
        self.assertNotIn('\x1f', prompt)
        self.assertNotIn('x' * 160, prompt)

    def test_parser_reponse_returns_the_public_contract_for_valid_json(self):
        response = parser_reponse(
            '```json\n{"heures_recommandees": [9, 14], "message": "Planifiez vos taches importantes."}\n```'
        )

        self.assertEqual(response, {
            'heures_recommandees': [9, 14],
            'message': 'Planifiez vos taches importantes.',
        })

    def test_parser_reponse_logs_metadata_without_the_invalid_response(self):
        with self.assertLogs('api.llm_service', level='WARNING') as logs:
            response = parser_reponse('sensitive task title is not JSON')

        self.assertIsNone(response)
        self.assertNotIn('sensitive task title', '\n'.join(logs.output))

    def test_parser_reponse_rejects_an_unhashable_hour_without_raising(self):
        response = parser_reponse(
            '{"heures_recommandees": [[]], "message": "Matin."}'
        )

        self.assertIsNone(response)

    @override_settings(LLM_API_KEY='')
    @patch('api.llm_service.anthropic.Anthropic')
    def test_appeler_llm_does_not_create_a_client_without_an_api_key(self, anthropic_client):
        response = appeler_llm('prompt')

        self.assertIsNone(response)
        anthropic_client.assert_not_called()

    @override_settings(LLM_API_KEY='test-key')
    @patch('api.llm_service.time.sleep')
    @patch('api.llm_service.anthropic.Anthropic')
    def test_appeler_llm_retries_a_timeout_then_returns_the_text(self, anthropic_client, sleep):
        client = anthropic_client.return_value
        client.messages.create.side_effect = [
            TimeoutError('timeout'),
            SimpleNamespace(content=[SimpleNamespace(type='text', text='{"heures_recommandees": [10], "message": "Matin."}')]),
        ]

        response = appeler_llm('prompt')

        self.assertEqual(response, '{"heures_recommandees": [10], "message": "Matin."}')
        self.assertEqual(client.messages.create.call_count, 2)
        sleep.assert_called_once()

    @override_settings(LLM_API_KEY='test-key')
    @patch('api.llm_service.anthropic.Anthropic')
    def test_appeler_llm_stops_after_a_definitive_error(self, anthropic_client):
        client = anthropic_client.return_value
        client.messages.create.side_effect = ValueError('invalid request')

        response = appeler_llm('prompt')

        self.assertIsNone(response)
        self.assertEqual(client.messages.create.call_count, 1)
