import csv
import io
from datetime import timedelta

from django.contrib.auth.models import User
from unittest.mock import patch
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from api import models as api_models
from api.models import Candidature, EmailCandidature


class CandidatureModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')

    def test_creation_uses_expected_default_tracking_fields(self):
        candidature = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/jobs/123',
            titre='Developpeuse Django',
        )

        self.assertEqual(candidature.entreprise, '')
        self.assertEqual(candidature.description, '')
        self.assertEqual(candidature.lieu, '')
        self.assertEqual(candidature.mode_travail, '')
        self.assertEqual(candidature.type_poste, Candidature.TypePoste.AUTRE)
        self.assertEqual(candidature.statut, Candidature.Statut.A_POSTULER)
        self.assertEqual(candidature.source_extraction, '')
        self.assertEqual(candidature.source_canal, Candidature.SourceCanal.AUTRE)
        self.assertEqual(candidature.tags, [])
        self.assertFalse(candidature.favori)
        self.assertFalse(candidature.archive)
        self.assertEqual(candidature.cv_utilise, '')
        self.assertIsNone(candidature.date_limite)
        self.assertIsNone(candidature.date_relance)
        self.assertEqual(candidature.notes, '')

    def test_same_user_cannot_create_two_candidatures_for_the_same_url(self):
        payload = {
            'utilisateur': self.user,
            'url': 'https://example.com/jobs/123',
            'titre': 'Developpeuse Django',
        }
        Candidature.objects.create(**payload)

        with self.assertRaises(IntegrityError):
            Candidature.objects.create(**payload)

    def test_lot_six_models_and_complementary_fields_are_declared(self):
        candidature_fields = {field.name for field in Candidature._meta.get_fields()}

        self.assertTrue({'lieu', 'mode_travail'} <= candidature_fields)
        self.assertTrue(hasattr(api_models, 'ActionCandidature'))


class CandidatureEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        self.candidature = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/jobs/alice',
            titre='Developpeuse backend',
            entreprise='Example',
            type_poste=Candidature.TypePoste.CDI,
            statut=Candidature.Statut.POSTULE,
            source_canal=Candidature.SourceCanal.LINKEDIN,
            tags=['django', 'remote'],
            favori=True,
            cv_utilise='CV_backend_v3.pdf',
            date_relance='2026-09-20',
        )
        self.other_candidature = Candidature.objects.create(
            utilisateur=self.other_user,
            url='https://example.com/jobs/bob',
            titre='Candidature Bob',
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def candidature_payload(self, **overrides):
        payload = {
            'url': 'https://example.com/jobs/new',
            'titre': 'Alternance React',
            'entreprise': 'Front Corp',
            'lieu': 'Paris',
            'mode_travail': Candidature.ModeTravail.HYBRIDE,
            'description': 'Construire une interface de suivi.',
            'type_poste': Candidature.TypePoste.ALTERNANCE,
            'statut': Candidature.Statut.A_POSTULER,
            'source_extraction': 'scraping',
            'source_canal': Candidature.SourceCanal.INDEED,
            'tags': ['react', 'mui'],
            'favori': True,
            'archive': False,
            'cv_utilise': 'CV_front.pdf',
            'date_limite': '2026-10-01',
            'date_relance': '2026-09-25',
            'notes': 'Relancer apres une semaine.',
        }
        payload.update(overrides)
        return payload

    def test_list_returns_only_the_authenticated_users_candidatures(self):
        response = self.client.get('/api/candidatures/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [self.candidature.id])

    def test_list_email_status_is_null_without_email(self):
        response = self.client.get('/api/candidatures/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data[0]['email_status'])

    def test_list_email_status_uses_latest_created_at_then_id(self):
        first = EmailCandidature.objects.create(
            candidature=self.candidature,
            recipient_email='contact@example.com',
            subject='Premier email',
            body='Bonjour',
            status=EmailCandidature.Status.SENT,
        )
        second = EmailCandidature.objects.create(
            candidature=self.candidature,
            recipient_email='contact@example.com',
            subject='Deuxieme email',
            body='Bonjour',
            status=EmailCandidature.Status.FAILED,
        )
        shared_created_at = first.created_at
        EmailCandidature.objects.filter(pk=second.pk).update(created_at=shared_created_at)

        response = self.client.get('/api/candidatures/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['email_status'], EmailCandidature.Status.FAILED)

    def test_list_email_status_prioritizes_created_at_over_id(self):
        earlier_id = EmailCandidature.objects.create(
            candidature=self.candidature,
            recipient_email='contact@example.com',
            subject='Email le plus recent',
            body='Bonjour',
            status=EmailCandidature.Status.SENT,
        )
        later_id = EmailCandidature.objects.create(
            candidature=self.candidature,
            recipient_email='contact@example.com',
            subject='Ancien email',
            body='Bonjour',
            status=EmailCandidature.Status.FAILED,
        )
        EmailCandidature.objects.filter(pk=earlier_id.pk).update(
            created_at=later_id.created_at + timedelta(seconds=1)
        )

        response = self.client.get('/api/candidatures/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['email_status'], EmailCandidature.Status.SENT)

    def test_list_email_status_is_not_taken_from_another_users_candidature(self):
        EmailCandidature.objects.create(
            candidature=self.other_candidature,
            recipient_email='bob@example.com',
            subject='Email Bob',
            body='Bonjour',
            status=EmailCandidature.Status.SENT,
        )

        response = self.client.get('/api/candidatures/')

        self.assertEqual([item['id'] for item in response.data], [self.candidature.id])
        self.assertIsNone(response.data[0]['email_status'])

    def test_export_csv_contains_expected_columns_and_respects_filters(self):
        Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/jobs/frontend',
            titre='Developpeuse frontend',
            statut=Candidature.Statut.A_POSTULER,
            tags=['react'],
        )

        response = self.client.get('/api/candidatures/export_csv/?statut=postule&tags=django')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="candidatures.csv"')
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))
        reader = csv.DictReader(io.StringIO(response.content.decode('utf-8-sig')))
        self.assertEqual(
            reader.fieldnames,
            [
                'titre', 'entreprise', 'type_poste', 'statut', 'source_canal',
                'tags', 'favori', 'date_limite', 'date_relance', 'date_ajout', 'url',
            ],
        )
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['titre'], self.candidature.titre)
        self.assertEqual(rows[0]['tags'], 'django;remote')

    def test_export_csv_neutralizes_spreadsheet_formulas(self):
        self.candidature.titre = '=HYPERLINK("https://example.com")'
        self.candidature.tags = ['@commande', 'django']
        self.candidature.save(update_fields=['titre', 'tags'])

        response = self.client.get('/api/candidatures/export_csv/')

        rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(rows[0]['titre'], '\'=HYPERLINK("https://example.com")')
        self.assertEqual(rows[0]['tags'], "'@commande;django")

    def test_create_assigns_authenticated_user_and_persists_tracking_fields(self):
        response = self.client.post('/api/candidatures/', self.candidature_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        candidature = Candidature.objects.get(pk=response.data['id'])
        self.assertEqual(candidature.utilisateur, self.user)
        self.assertEqual(candidature.type_poste, Candidature.TypePoste.ALTERNANCE)
        self.assertEqual(candidature.lieu, 'Paris')
        self.assertEqual(candidature.mode_travail, Candidature.ModeTravail.HYBRIDE)
        self.assertEqual(candidature.source_canal, Candidature.SourceCanal.INDEED)
        self.assertEqual(candidature.tags, ['react', 'mui'])
        self.assertTrue(candidature.favori)
        self.assertEqual(candidature.cv_utilise, 'CV_front.pdf')
        self.assertEqual(candidature.date_relance.isoformat(), '2026-09-25')

    def test_create_cannot_assign_candidature_to_another_user(self):
        response = self.client.post(
            '/api/candidatures/',
            self.candidature_payload(utilisateur=self.other_user.id),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        candidature = Candidature.objects.get(pk=response.data['id'])
        self.assertEqual(candidature.utilisateur, self.user)

    def test_update_and_delete_cannot_access_another_users_candidature(self):
        response = self.client.patch(
            f'/api/candidatures/{self.other_candidature.id}/',
            {'titre': 'Tentative de modification'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.delete(f'/api/candidatures/{self.other_candidature.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Candidature.objects.filter(pk=self.other_candidature.id).exists())

    def test_update_changes_an_owned_candidature(self):
        response = self.client.patch(
            f'/api/candidatures/{self.candidature.id}/',
            {'statut': Candidature.Statut.ENTRETIEN, 'archive': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.candidature.refresh_from_db()
        self.assertEqual(self.candidature.statut, Candidature.Statut.ENTRETIEN)
        self.assertTrue(self.candidature.archive)

    @patch('api.views.scraper_candidature')
    def test_import_duplicate_normalizes_existing_url_without_network(self, scrape):
        self.candidature.url += '?utm_source=old'
        self.candidature.save()
        response = self.client.post('/api/candidatures/import_url/', {'url': 'https://example.com/jobs/alice?utm_source=new#top'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'duplicate': True, 'candidature_id': self.candidature.id})
        scrape.assert_not_called()

    @patch('api.views.scraper_candidature')
    def test_import_preview_is_scoped_and_not_saved(self, scrape):
        self.candidature.url = 'https://example.com:99999/old'
        self.candidature.save()
        scrape.return_value = {'titre': 'Dev Django', 'entreprise': '', 'description': 'Une description extraite.', 'type_poste': 'autre', 'source_extraction': 'scraping'}
        response = self.client.post('/api/candidatures/import_url/', {'url': self.other_candidature.url + '?utm_source=test'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'url': self.other_candidature.url, **scrape.return_value})
        self.assertEqual(Candidature.objects.count(), 2)

    @patch('api.views.scraper_candidature', return_value=None)
    def test_import_failure_returns_empty_form(self, scrape):
        response = self.client.post('/api/candidatures/import_url/', {'url': 'https://example.com/new'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'url': 'https://example.com/new', 'titre': '', 'entreprise': '', 'description': '', 'type_poste': 'autre', 'source_extraction': ''})
        self.assertEqual(Candidature.objects.count(), 2)

    def test_import_requires_authentication_and_valid_http_url(self):
        for payload in [{}, {'url': 'invalid'}, {'url': 'ftp://example.com/file'}, {'url': 'https://user:secret@example.com'}]:
            self.assertEqual(self.client.post('/api/candidatures/import_url/', payload, format='json').status_code, 400)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/candidatures/import_url/', {'url': 'https://example.com'}, format='json').status_code, 401)


class CandidatureFilterTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='filters')
        self.other_user = User.objects.create_user(username='other-filters')
        self.client.force_authenticate(self.user)
        today = timezone.localdate()
        self.backend = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/backend',
            titre='Developpeuse Django',
            entreprise='Alpha',
            type_poste=Candidature.TypePoste.CDI,
            statut=Candidature.Statut.POSTULE,
            source_canal=Candidature.SourceCanal.LINKEDIN,
            tags=['python', 'django'],
            favori=True,
            date_limite=today + timezone.timedelta(days=5),
            date_relance=today,
        )
        self.frontend = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/frontend',
            titre='Developpeuse React',
            entreprise='Beta Studio',
            type_poste=Candidature.TypePoste.ALTERNANCE,
            statut=Candidature.Statut.ENTRETIEN,
            source_canal=Candidature.SourceCanal.INDEED,
            tags=['javascript', 'react'],
            date_limite=today + timezone.timedelta(days=12),
            date_relance=today + timezone.timedelta(days=2),
        )
        self.archived = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/archived',
            titre='Ancienne offre Django',
            entreprise='Gamma',
            archive=True,
            tags=['python'],
        )
        self.other = Candidature.objects.create(
            utilisateur=self.other_user,
            url='https://example.com/other',
            titre='Offre privee',
        )

    def ids(self, query=''):
        response = self.client.get(f'/api/candidatures/{query}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [item['id'] for item in response.data]

    def test_default_list_excludes_archived_and_orders_newest_first(self):
        Candidature.objects.filter(pk=self.backend.pk).update(
            date_ajout=timezone.now() - timezone.timedelta(days=2)
        )
        self.assertEqual(self.ids(), [self.frontend.id, self.backend.id])

    def test_archive_true_includes_active_and_archived(self):
        self.assertCountEqual(
            self.ids('?archive=true'),
            [self.backend.id, self.frontend.id, self.archived.id],
        )

    def test_archived_candidature_remains_available_by_id(self):
        response = self.client.get(f'/api/candidatures/{self.archived.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.archived.id)

    @patch('api.views.scraper_candidature')
    def test_import_detects_an_archived_duplicate_before_scraping(self, scrape):
        response = self.client.post(
            '/api/candidatures/import_url/',
            {'url': self.archived.url},
            format='json',
        )
        self.assertEqual(response.data, {
            'duplicate': True,
            'candidature_id': self.archived.id,
        })
        scrape.assert_not_called()

    def test_choice_boolean_search_and_tag_filters(self):
        cases = {
            '?statut=postule': [self.backend.id],
            '?statut=postule&statut=entretien': [self.backend.id, self.frontend.id],
            '?type_poste=cdi': [self.backend.id],
            '?source_canal=indeed': [self.frontend.id],
            '?tags=python&tags=django': [self.backend.id],
            '?favori=true': [self.backend.id],
            '?search=beta': [self.frontend.id],
            '?search=django': [self.backend.id],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertCountEqual(self.ids(query), expected)

    def test_date_deadline_and_follow_up_filters(self):
        today = timezone.localdate().isoformat()
        tomorrow = (timezone.localdate() + timezone.timedelta(days=1)).isoformat()
        cases = {
            f'?date_ajout_min={tomorrow}': [],
            f'?date_ajout_max={today}': [self.backend.id, self.frontend.id],
            '?date_limite=7j': [self.backend.id],
            '?relance_due=true': [self.backend.id],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertCountEqual(self.ids(query), expected)

    def test_ordering_is_whitelisted(self):
        self.backend.date_limite = timezone.localdate() + timezone.timedelta(days=5)
        self.frontend.date_limite = timezone.localdate() + timezone.timedelta(days=12)
        self.backend.save()
        self.frontend.save()
        self.assertEqual(self.ids('?ordering=date_limite'), [self.backend.id, self.frontend.id])
        self.assertCountEqual(self.ids('?ordering=utilisateur'), [self.backend.id, self.frontend.id])

    def test_archiver_action_only_updates_an_owned_candidature(self):
        response = self.client.patch(f'/api/candidatures/{self.backend.id}/archiver/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.backend.refresh_from_db()
        self.assertTrue(self.backend.archive)
        self.assertTrue(response.data['archive'])

        response = self.client.patch(f'/api/candidatures/{self.other.id}/archiver/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
