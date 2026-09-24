import tempfile
from datetime import timedelta
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import ActionCandidature, CVUtilisateur, Candidature, ConnexionGmail, EmailCandidature


class DefaultCvUploadTests(APITestCase):
    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp_media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user(username='cv-upload-owner')
        self.other = User.objects.create_user(username='cv-upload-other')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')
        self.url = '/api/candidatures/cv_par_defaut/'

    def upload(self, name='cv.pdf', content=b'%PDF-1.4\nvalid', client=None):
        file = SimpleUploadedFile(name, content, content_type='application/pdf')
        return (client or self.client).put(self.url, {'fichier': file}, format='multipart')

    def test_uploads_private_pdf_for_authenticated_owner(self):
        response = self.upload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filename'], 'cv.pdf')
        self.assertRegex(response.data['fingerprint'], r'^[0-9a-f]{64}$')
        self.assertEqual(self.client.get(self.url).data['fingerprint'], response.data['fingerprint'])
        cv = CVUtilisateur.objects.get(utilisateur=self.user)
        self.assertTrue(Path(cv.fichier.path).is_file())
        self.assertEqual(CVUtilisateur.objects.count(), 1)

    def test_post_upload_is_rejected_with_put_listed_as_allowed(self):
        file = SimpleUploadedFile('cv.pdf', b'%PDF-1.4\nvalid', content_type='application/pdf')

        response = self.client.post(self.url, {'fichier': file}, format='multipart')

        self.assertEqual(response.status_code, 405)
        self.assertIn('PUT', response['Allow'])
        self.assertIn('POST', str(response.data['detail']))
        self.assertFalse(CVUtilisateur.objects.filter(utilisateur=self.user).exists())

    def test_cv_remains_scoped_to_owner(self):
        CVUtilisateur.objects.create(utilisateur=self.other, fichier='cv/other.pdf')

        response = self.upload()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CVUtilisateur.objects.count(), 2)
        self.assertEqual(CVUtilisateur.objects.get(utilisateur=self.other).fichier.name, 'cv/other.pdf')

    @patch('api.views.lire_cv_par_defaut', return_value=(b'%PDF-1.4', 'updated.pdf', 'a' * 64))
    def test_cv_name_and_fingerprint_come_from_the_same_read(self, read_cv):
        self.upload('original.pdf')
        read_cv.reset_mock()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'filename': 'updated.pdf', 'fingerprint': 'a' * 64})
        read_cv.assert_called_once_with(self.user)

    def test_replacement_keeps_one_record_and_removes_old_file(self):
        self.upload()
        cv = CVUtilisateur.objects.get(utilisateur=self.user)
        old_id, old_path = cv.id, Path(cv.fichier.path)

        response = self.upload('new.pdf')

        cv.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cv.id, old_id)
        self.assertEqual(response.data['filename'], 'new.pdf')
        self.assertRegex(response.data['fingerprint'], r'^[0-9a-f]{64}$')
        self.assertFalse(old_path.exists())
        self.assertTrue(Path(cv.fichier.path).exists())

    def test_rejects_non_pdf_extension_and_signature(self):
        for name, content in [('cv.txt', b'%PDF-1.4\nvalid'), ('cv.pdf', b'not a pdf')]:
            with self.subTest(name=name, content=content):
                response = self.upload(name, content)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(CVUtilisateur.objects.filter(utilisateur=self.user).exists())

    def test_rejects_more_than_five_mebibytes(self):
        response = self.upload(content=b'%PDF-' + b'x' * (5 * 1024 * 1024))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(CVUtilisateur.objects.filter(utilisateur=self.user).exists())

    def test_rejects_missing_file_and_preserves_existing_cv(self):
        self.upload()
        cv = CVUtilisateur.objects.get(utilisateur=self.user)
        old_path = Path(cv.fichier.path)

        response = self.client.put(self.url, {}, format='multipart')

        cv.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Path(cv.fichier.path), old_path)
        self.assertTrue(old_path.exists())

    def test_rejects_unauthenticated_upload(self):
        self.client.credentials()

        response = self.upload()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(CVUtilisateur.objects.exists())


class EmailSendEndpointTests(APITestCase):
    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp_media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user(username='send-owner', email='sender@example.com')
        self.other = User.objects.create_user(username='send-other')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')
        self.candidature = Candidature.objects.create(
            utilisateur=self.user, url='https://example.com/send-owner',
            titre='Developpeur', entreprise='Example',
        )
        self.other_candidature = Candidature.objects.create(
            utilisateur=self.other, url='https://example.com/send-other', titre='Autre',
        )
        self.email = EmailCandidature.objects.create(
            candidature=self.candidature, recipient_email='jobs@example.com',
            subject='Candidature', body='Bonjour,', status=EmailCandidature.Status.READY,
        )
        self.other_email = EmailCandidature.objects.create(
            candidature=self.other_candidature, recipient_email='private@example.com',
            subject='Private', body='Private', status=EmailCandidature.Status.READY,
        )
        CVUtilisateur.objects.create(
            utilisateur=self.user,
            fichier=SimpleUploadedFile('test.pdf', b'%PDF-1.4\nprivate'),
        )
        self.connexion = ConnexionGmail.objects.create(
            utilisateur=self.user, refresh_token_chiffre='encrypted-test-value',
        )
        from .email_send_service import lire_cv_par_defaut
        self.cv_fingerprint = lire_cv_par_defaut(self.user)[2]

    def url(self, email=None, candidature=None, action='envoyer'):
        return (
            f'/api/candidatures/{(candidature or self.candidature).id}/emails/'
            f'{(email or self.email).id}/{action}/'
        )

    def post(self, action='envoyer', email=None, candidature=None, payload=None):
        return self.client.post(
            self.url(email=email, candidature=candidature, action=action),
            {'confirmation': True, 'cv_fingerprint': self.cv_fingerprint} if payload is None else payload,
            format='json',
        )

    @patch('api.email_send_service.envoyer_message_gmail', return_value='gmail-parcours-1')
    def test_full_draft_edit_confirm_send_and_history_with_mock_gmail(self, gmail_send):
        base_url = f'/api/candidatures/{self.candidature.id}/'
        prepared = self.client.post(f'{base_url}preparer_email/', {
            'recipient_email': 'contact@example.com',
            'formation': 'Licence professionnelle',
            'portfolio_url': 'https://portfolio.example.com',
            'github_url': 'https://github.com/example',
        }, format='json')
        self.assertEqual(prepared.status_code, 201)
        email_id = prepared.data['id']
        self.assertEqual(prepared.data['status'], 'draft')
        gmail_send.assert_not_called()

        email_url = f'{base_url}emails/{email_id}/'
        edited = self.client.patch(email_url, {
            'recipient_email': 'recrutement@example.com',
            'subject': 'Candidature modifiee',
            'body': 'Bonjour, voici ma candidature modifiee.',
        }, format='json')
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.data['status'], 'draft')
        self.assertEqual(edited.data['subject'], 'Candidature modifiee')
        gmail_send.assert_not_called()

        ready = self.client.post(f'{email_url}preparer_envoi/', {
            'recipient_email': 'recrutement@example.com',
            'subject': 'Candidature modifiee',
            'body': 'Bonjour, voici ma candidature modifiee.',
        }, format='json')
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.data['status'], 'ready')
        gmail_send.assert_not_called()

        sent = self.client.post(f'{email_url}envoyer/', {
            'confirmation': True,
            'cv_fingerprint': self.cv_fingerprint,
        }, format='json')
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data['status'], 'sent')
        self.assertEqual(sent.data['gmail_message_id'], 'gmail-parcours-1')
        gmail_send.assert_called_once()
        self.assertEqual(gmail_send.call_args.kwargs['recipient'], 'recrutement@example.com')
        self.assertEqual(gmail_send.call_args.kwargs['subject'], 'Candidature modifiee')
        self.assertEqual(gmail_send.call_args.kwargs['body'], 'Bonjour, voici ma candidature modifiee.')

        emails = self.client.get(f'{base_url}emails/')
        actions = self.client.get(f'{base_url}actions/')
        self.assertEqual(emails.status_code, 200)
        self.assertEqual(actions.status_code, 200)
        self.assertTrue(any(item['id'] == email_id and item['status'] == 'sent' for item in emails.data))
        self.assertTrue(any(item['type_action'] == 'envoyee' for item in actions.data))

    @patch('api.email_send_service.envoyer_message_gmail', return_value='gmail-123')
    def test_success_sends_once_and_creates_history(self, gmail_send):
        response = self.post()

        self.assertEqual(response.status_code, 200)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'sent')
        self.assertEqual(self.email.gmail_message_id, 'gmail-123')
        self.assertIsNotNone(self.email.sent_at)
        self.assertEqual(ActionCandidature.objects.filter(candidature=self.candidature, type_action='envoyee').count(), 1)
        gmail_send.assert_called_once()


    @patch('api.email_send_service.envoyer_message_gmail', return_value='gmail-123')
    def test_repeated_send_does_not_call_gmail_twice(self, gmail_send):
        first = self.post()
        second = self.post()

        self.assertEqual((first.status_code, second.status_code), (200, 200))
        gmail_send.assert_called_once()
        self.assertEqual(ActionCandidature.objects.filter(type_action='envoyee').count(), 1)

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_missing_confirmation_and_invalid_status_without_gmail(self, gmail_send):
        self.assertEqual(self.post(payload={}).status_code, 400)
        self.email.status = EmailCandidature.Status.DRAFT
        self.email.save(update_fields=['status'])
        self.assertEqual(self.post().status_code, 409)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_corrupt_email_and_missing_cv_without_gmail(self, gmail_send):
        self.email.recipient_email = 'invalid'
        self.email.save(update_fields=['recipient_email'])
        self.assertEqual(self.post().status_code, 400)
        self.email.recipient_email = 'jobs@example.com'
        self.email.save(update_fields=['recipient_email'])
        cv = CVUtilisateur.objects.get(utilisateur=self.user)
        cv.fichier.delete(save=False)
        self.assertEqual(self.post().status_code, 400)
        gmail_send.assert_not_called()
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'ready')

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_changed_cv_before_reserving_or_contacting_gmail(self, gmail_send):
        replacement = self.client.put(
            '/api/candidatures/cv_par_defaut/',
            {'fichier': SimpleUploadedFile('updated.pdf', b'%PDF-1.4\nnew content')},
            format='multipart',
        )
        self.assertEqual(replacement.status_code, 200)
        self.assertNotEqual(replacement.data['fingerprint'], self.cv_fingerprint)

        response = self.post()

        self.assertEqual(response.status_code, 409)
        self.assertIn('CV', response.data['detail'])
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'ready')
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_send_without_confirmed_cv_fingerprint(self, gmail_send):
        response = self.post(payload={'confirmation': True})

        self.assertEqual(response.status_code, 400)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'ready')
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_header_injection_before_reservation(self, gmail_send):
        self.email.subject = 'Candidature\nBcc: private@example.com'
        self.email.save(update_fields=['subject'])

        response = self.post()

        self.assertEqual(response.status_code, 400)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'ready')
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_invalid_sender_address_before_reservation(self, gmail_send):
        self.user.email = 'not-an-email'
        self.user.save(update_fields=['email'])

        response = self.post()

        self.assertEqual(response.status_code, 400)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'ready')
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_rejects_missing_or_disconnected_gmail_without_send(self, gmail_send):
        self.connexion.delete()
        self.assertEqual(self.post().status_code, 409)
        self.connexion = ConnexionGmail.objects.create(
            utilisateur=self.user, statut=ConnexionGmail.Statut.RECONNEXION_REQUISE,
        )
        self.assertEqual(self.post().status_code, 409)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_foreign_parent_and_email_are_not_accessible(self, gmail_send):
        self.assertEqual(self.post(candidature=self.other_candidature, email=self.other_email).status_code, 404)
        self.assertEqual(self.post(email=self.other_email).status_code, 404)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_unauthenticated_user_cannot_send(self, gmail_send):
        self.client.credentials()

        response = self.post()

        self.assertEqual(response.status_code, 401)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_definite_failure_marks_failed_without_history(self, gmail_send):
        from .gmail_send_service import EnvoiRefuse

        gmail_send.side_effect = EnvoiRefuse('gmail_rejected')

        response = self.post()

        self.assertEqual(response.status_code, 502)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'failed')
        self.assertFalse(ActionCandidature.objects.exists())

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_uncertain_result_stays_sending_without_history(self, gmail_send):
        from .gmail_send_service import ResultatIncertain

        gmail_send.side_effect = ResultatIncertain('network_outcome_unknown')

        response = self.post()

        self.assertEqual(response.status_code, 202)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'sending')
        self.assertFalse(ActionCandidature.objects.exists())
        self.assertEqual(self.post().status_code, 409)
        gmail_send.assert_called_once()

    @patch('api.email_send_service.envoyer_message_gmail', return_value=None)
    def test_missing_gmail_id_never_marks_sent(self, gmail_send):
        response = self.post()

        self.assertEqual(response.status_code, 202)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'sending')
        self.assertFalse(ActionCandidature.objects.exists())
        gmail_send.assert_called_once()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_manual_confirmation_after_uncertainty_never_calls_gmail(self, gmail_send):
        self.email.status = EmailCandidature.Status.SENDING
        self.email.error_message = 'network_outcome_unknown'
        self.email.save(update_fields=['status', 'error_message'])

        response = self.post(action='confirmer_manuellement')

        self.assertEqual(response.status_code, 200)
        self.email.refresh_from_db()
        self.assertEqual(self.email.status, 'sent')
        self.assertIsNotNone(self.email.manual_confirmation_at)
        self.assertEqual(ActionCandidature.objects.filter(type_action='envoyee').count(), 1)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_manual_actions_wait_five_minutes_for_stale_sending(self, gmail_send):
        self.email.status = EmailCandidature.Status.SENDING
        self.email.save(update_fields=['status'])
        self.assertEqual(self.post(action='confirmer_manuellement').status_code, 409)
        self.assertEqual(self.post(action='nouvelle_tentative').status_code, 409)
        EmailCandidature.objects.filter(pk=self.email.pk).update(updated_at=timezone.now() - timedelta(minutes=6))

        response = self.post(action='nouvelle_tentative')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'draft')
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_retry_is_new_editable_draft_with_single_linear_successor(self, gmail_send):
        self.email.status = EmailCandidature.Status.SENDING
        self.email.error_message = 'gmail_outcome_unknown'
        self.email.save(update_fields=['status', 'error_message'])

        first = self.post(action='nouvelle_tentative')
        second = self.post(action='nouvelle_tentative')

        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.data['id'], second.data['id'])
        retry = EmailCandidature.objects.get(pk=first.data['id'])
        self.assertEqual(retry.retry_of_id, self.email.id)
        self.assertEqual(retry.status, 'draft')
        self.assertEqual(retry.subject, self.email.subject)
        self.assertEqual(retry.gmail_message_id, '')
        self.assertEqual(EmailCandidature.objects.filter(retry_of=self.email).count(), 1)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_cancelled_retry_can_have_next_linear_draft_without_global_cap(self, gmail_send):
        self.email.status = EmailCandidature.Status.SENDING
        self.email.error_message = 'network_outcome_unknown'
        self.email.save(update_fields=['status', 'error_message'])
        first_retry_response = self.post(action='nouvelle_tentative')
        first_retry = EmailCandidature.objects.get(pk=first_retry_response.data['id'])
        first_retry.status = EmailCandidature.Status.CANCELLED
        first_retry.save(update_fields=['status'])

        response = self.post(action='nouvelle_tentative', email=first_retry)

        self.assertEqual(response.status_code, 201)
        second_retry = EmailCandidature.objects.get(pk=response.data['id'])
        self.assertEqual(second_retry.status, EmailCandidature.Status.DRAFT)
        self.assertEqual(second_retry.retry_of_id, first_retry.id)
        gmail_send.assert_not_called()

    @patch('api.email_send_service.envoyer_message_gmail', return_value='gmail-retry')
    def test_two_confirmed_attempts_remain_visible_in_history(self, gmail_send):
        self.email.status = EmailCandidature.Status.SENDING
        self.email.error_message = 'network_outcome_unknown'
        self.email.save(update_fields=['status', 'error_message'])
        retry_response = self.post(action='nouvelle_tentative')
        retry = EmailCandidature.objects.get(pk=retry_response.data['id'])
        retry.status = EmailCandidature.Status.READY
        retry.save(update_fields=['status'])

        self.assertEqual(self.post(email=retry).status_code, 200)
        self.assertEqual(self.post(action='confirmer_manuellement').status_code, 200)

        actions = list(ActionCandidature.objects.filter(type_action='envoyee').order_by('id'))
        self.assertEqual(len(actions), 2)
        self.assertIn(str(retry.id), actions[0].commentaire)
        self.assertIn(str(self.email.id), actions[1].commentaire)
        gmail_send.assert_called_once()


class ConcurrentEmailSendTests(TransactionTestCase):
    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_media.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp_media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user(username='concurrent-send', email='sender@example.com')
        self.token = Token.objects.create(user=self.user)
        self.candidature = Candidature.objects.create(
            utilisateur=self.user, url='https://example.com/concurrent-send', titre='Developpeur',
        )
        self.email = EmailCandidature.objects.create(
            candidature=self.candidature, recipient_email='jobs@example.com',
            subject='Candidature', body='Bonjour,', status='ready',
        )
        CVUtilisateur.objects.create(
            utilisateur=self.user,
            fichier=SimpleUploadedFile('test.pdf', b'%PDF-1.4\nprivate'),
        )
        ConnexionGmail.objects.create(utilisateur=self.user, refresh_token_chiffre='encrypted-test-value')
        from .email_send_service import lire_cv_par_defaut
        self.cv_fingerprint = lire_cv_par_defaut(self.user)[2]

    def client_for_user(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        return client

    @patch('api.email_send_service.envoyer_message_gmail')
    def test_parallel_double_post_reserves_only_one_send(self, gmail_send):
        entered, release = Event(), Event()
        results = []

        def blocked_send(**_kwargs):
            entered.set()
            self.assertTrue(release.wait(10))
            return 'gmail-concurrent'

        def first_post():
            try:
                client = self.client_for_user()
                response = client.post(
                    f'/api/candidatures/{self.candidature.id}/emails/{self.email.id}/envoyer/',
                    {'confirmation': True, 'cv_fingerprint': self.cv_fingerprint}, format='json',
                )
                results.append(response.status_code)
            finally:
                connections.close_all()

        gmail_send.side_effect = blocked_send
        worker = Thread(target=first_post)
        worker.start()
        try:
            self.assertTrue(entered.wait(10))
            second = self.client_for_user().post(
                f'/api/candidatures/{self.candidature.id}/emails/{self.email.id}/envoyer/',
                {'confirmation': True, 'cv_fingerprint': self.cv_fingerprint}, format='json',
            )
            self.assertEqual(second.status_code, 409)
        finally:
            release.set()
            worker.join(10)

        self.assertEqual(results, [200])
        gmail_send.assert_called_once()
        self.assertEqual(ActionCandidature.objects.filter(type_action='envoyee').count(), 1)
