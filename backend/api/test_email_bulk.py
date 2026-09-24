from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connection, ProgrammingError
from django.db.migrations.executor import MigrationExecutor
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APITransactionTestCase

from .models import Candidature, EmailCandidature


class PreparationEmailsMasseTests(APITestCase):
    url = '/api/candidatures/preparer_emails/'

    def setUp(self):
        self.user = User.objects.create_user(username='bulk-owner')
        self.other_user = User.objects.create_user(username='bulk-other')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.first = Candidature.objects.create(
            utilisateur=self.user, url='https://example.com/bulk-first',
            titre='Developpeur Python', entreprise='Entreprise A',
        )
        self.second = Candidature.objects.create(
            utilisateur=self.user, url='https://example.com/bulk-second',
            titre='Developpeur React', entreprise='Entreprise B',
        )
        self.foreign = Candidature.objects.create(
            utilisateur=self.other_user, url='https://example.com/bulk-foreign',
            titre='Developpeur Django', entreprise='Entreprise privee',
        )
        self.payload = {
            'formation': 'Licence professionnelle web',
            'portfolio_url': 'https://portfolio.example.com',
            'github_url': 'https://github.com/example',
            'emails': [
                {
                    'candidature_id': self.first.id,
                    'recipient_email': 'a@example.com',
                    'civilite': 'Madame',
                    'prenom_contact': 'Ada',
                    'nom_contact': 'Martin',
                },
                {
                    'candidature_id': self.second.id,
                    'recipient_email': 'b@example.com',
                },
            ],
        }

    @patch('socket.create_connection')
    def test_creates_independent_drafts_without_network_or_gmail(self, connection_mock):
        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['emails']), 2)
        first, second = response.data['emails']
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual([first['candidature'], second['candidature']], [self.first.id, self.second.id])
        self.assertEqual([first['recipient_email'], second['recipient_email']], ['a@example.com', 'b@example.com'])
        self.assertEqual([first['status'], second['status']], ['draft', 'draft'])
        self.assertIn('Entreprise A', first['body'])
        self.assertIn('Developpeur Python', first['body'])
        self.assertIn('Bonjour Madame, Monsieur', second['body'])
        self.assertIn('Entreprise B', second['body'])
        self.assertEqual(EmailCandidature.objects.count(), 2)
        connection_mock.assert_not_called()

    def test_existing_draft_does_not_prevent_a_distinct_new_draft(self):
        existing = EmailCandidature.objects.create(
            candidature=self.first, recipient_email='old@example.com',
            subject='Ancien brouillon', body='Ancien texte',
        )

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(EmailCandidature.objects.filter(candidature=self.first).count(), 2)
        self.assertNotIn(existing.id, [email['id'] for email in response.data['emails']])

    def test_second_insert_failure_rolls_back_the_first_draft(self):
        original_create = EmailCandidature.objects.create
        calls = 0

        def create_or_fail(**values):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('second insert failed')
            return original_create(**values)

        with patch.object(EmailCandidature.objects, 'create', side_effect=create_or_fail):
            with self.assertRaisesMessage(RuntimeError, 'second insert failed'):
                self.client.post(self.url, self.payload, format='json')

        self.assertEqual(calls, 2)
        self.assertFalse(EmailCandidature.objects.exists())

    def test_invalid_recipient_identifies_the_row_and_creates_nothing(self):
        self.payload['emails'][1]['recipient_email'] = 'not-an-email'

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['row_errors'][0]['index'], 1)
        self.assertEqual(response.data['row_errors'][0]['candidature_id'], self.second.id)
        self.assertIn('recipient_email', response.data['row_errors'][0]['errors'])
        self.assertFalse(EmailCandidature.objects.exists())

    def test_reports_each_invalid_row_without_partial_creation(self):
        self.payload['emails'][0]['recipient_email'] = 'bad-first'
        self.payload['emails'][1]['recipient_email'] = 'bad-second'

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            [(row['index'], row['candidature_id']) for row in response.data['row_errors']],
            [(0, self.first.id), (1, self.second.id)],
        )
        self.assertFalse(EmailCandidature.objects.exists())

    def test_invalid_shared_template_value_creates_nothing(self):
        self.payload['portfolio_url'] = 'not-a-url'

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('portfolio_url', response.data['common_errors'])
        self.assertFalse(EmailCandidature.objects.exists())

    def test_foreign_candidature_is_identified_without_creating_any_draft(self):
        self.payload['emails'][1]['candidature_id'] = self.foreign.id

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['row_errors'][0]['index'], 1)
        self.assertEqual(response.data['row_errors'][0]['candidature_id'], self.foreign.id)
        self.assertIn('candidature_id', response.data['row_errors'][0]['errors'])
        self.assertFalse(EmailCandidature.objects.exists())

    def test_unknown_candidature_is_identified_without_creating_any_draft(self):
        self.payload['emails'][1]['candidature_id'] = 987654

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['row_errors'][0]['candidature_id'], 987654)
        self.assertIn('candidature_id', response.data['row_errors'][0]['errors'])
        self.assertFalse(EmailCandidature.objects.exists())

    def test_duplicate_selection_is_rejected_without_creating_drafts(self):
        self.payload['emails'][1]['candidature_id'] = self.first.id

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['row_errors'][0]['index'], 1)
        self.assertIn('candidature_id', response.data['row_errors'][0]['errors'])
        self.assertFalse(EmailCandidature.objects.exists())

    def test_empty_selection_creates_nothing(self):
        self.payload['emails'] = []

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmailCandidature.objects.exists())

    def test_requires_authentication(self):
        self.client.credentials()

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 401)
        self.assertFalse(EmailCandidature.objects.exists())


class PreparationEmailsMasseMigrationTests(APITransactionTestCase):
    def test_bulk_creation_requires_migration_0009_on_existing_database(self):
        old_schema = ('api', '0008_connexiongmail_tentativeoauthgmail')
        current_schema = ('api', '0009_emailcandidature_manual_confirmation_retry')
        MigrationExecutor(connection).migrate([old_schema])
        try:
            user = User.objects.create_user(username='bulk-migration-owner')
            candidature = Candidature.objects.create(
                utilisateur=user, url='https://example.com/bulk-migration',
                titre='Developpeur Python', entreprise='Entreprise A',
            )
            self.client.force_authenticate(user=user)
            payload = {
                'formation': 'Licence professionnelle web',
                'portfolio_url': 'https://portfolio.example.com',
                'github_url': 'https://github.com/example',
                'emails': [{'candidature_id': candidature.id, 'recipient_email': 'a@example.com'}],
            }

            with self.assertRaises(ProgrammingError) as failure:
                self.client.post('/api/candidatures/preparer_emails/', payload, format='json')
            self.assertIn('manual_confirmation_at', str(failure.exception))
            self.assertFalse(EmailCandidature.objects.exists())
        finally:
            MigrationExecutor(connection).migrate([current_schema])

        response = self.client.post('/api/candidatures/preparer_emails/', payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['emails']), 1)
        self.assertEqual(response.data['emails'][0]['status'], 'draft')
