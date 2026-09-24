import base64
import socket
from email import message_from_bytes, policy
from unittest.mock import patch

import requests
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from google.auth.exceptions import RefreshError

from .gmail_oauth_service import chiffrer
from .models import ConnexionGmail


@override_settings(
    GMAIL_OAUTH_CLIENT_ID='test-client',
    GMAIL_OAUTH_CLIENT_SECRET='test-secret',
    GMAIL_OAUTH_REDIRECT_URI='http://localhost:8000/callback',
    GMAIL_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'),
)
class GmailSendServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gmail-send-test', email='sender@example.com')
        self.connexion = ConnexionGmail.objects.create(
            utilisateur=self.user,
            refresh_token_chiffre=chiffrer('refresh-test'),
        )

    def send(self):
        from .gmail_send_service import envoyer_message_gmail

        return envoyer_message_gmail(
            connexion=self.connexion,
            recipient='candidatures@example.com',
            subject='Candidature é',
            body='Bonjour, voici mon CV. Équipe et expérience.',
            cv_bytes=b'%PDF-1.4\nprivate',
            cv_filename='mon-cv.pdf',
        )

    @patch('api.gmail_send_service.requests.post')
    @patch('api.gmail_send_service.Credentials')
    def test_sends_one_utf8_message_with_pdf_as_base64url(self, credentials_class, post):
        credentials = credentials_class.return_value
        credentials.token = 'access-test'
        credentials.refresh_token = 'refresh-test'
        post.return_value.status_code = 200
        post.return_value.json.return_value = {'id': 'gmail-123'}

        message_id = self.send()

        self.assertEqual(message_id, 'gmail-123')
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args, ('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',))
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer access-test')
        self.assertEqual(kwargs['timeout'], (5, 20))
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(set(kwargs['json']), {'raw'})
        parsed = message_from_bytes(base64.urlsafe_b64decode(kwargs['json']['raw']), policy=policy.default)
        self.assertEqual(parsed['From'], 'sender@example.com')
        self.assertEqual(parsed['To'], 'candidatures@example.com')
        self.assertEqual(str(parsed['Subject']), 'Candidature é')
        self.assertIn('Équipe et expérience.', parsed.get_body(preferencelist=('plain',)).get_content())
        attachment = list(parsed.iter_attachments())[0]
        self.assertEqual(attachment.get_filename(), 'mon-cv.pdf')
        self.assertEqual(attachment.get_payload(decode=True), b'%PDF-1.4\nprivate')

    @patch('api.gmail_send_service.requests.post')
    @patch('api.gmail_send_service.Credentials')
    def test_definite_preconnection_failures_are_failed(self, credentials_class, post):
        from .gmail_send_service import EnvoiRefuse

        credentials_class.return_value.token = 'access-test'
        credentials_class.return_value.refresh_token = 'refresh-test'
        failures = [
            requests.exceptions.ConnectTimeout('connect'),
            requests.exceptions.ConnectionError(socket.gaierror(11001, 'dns')),
            requests.exceptions.SSLError('tls handshake'),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                post.side_effect = failure
                with self.assertRaises(EnvoiRefuse):
                    self.send()

    @patch('api.gmail_send_service.requests.post')
    @patch('api.gmail_send_service.Credentials')
    def test_unknown_outcomes_remain_uncertain(self, credentials_class, post):
        from .gmail_send_service import ResultatIncertain

        credentials_class.return_value.token = 'access-test'
        credentials_class.return_value.refresh_token = 'refresh-test'
        for failure in (
            requests.exceptions.ReadTimeout('read'),
            requests.exceptions.ConnectionError('unknown phase'),
            requests.exceptions.SSLError('tls record failed after connection'),
        ):
            with self.subTest(failure=type(failure).__name__):
                post.side_effect = failure
                with self.assertRaises(ResultatIncertain):
                    self.send()

        post.side_effect = None
        for status_code, payload in [(408, {}), (503, {}), (200, {})]:
            with self.subTest(status_code=status_code):
                post.return_value.status_code = status_code
                post.return_value.json.return_value = payload
                with self.assertRaises(ResultatIncertain):
                    self.send()

    @patch('api.gmail_send_service.requests.post')
    @patch('api.gmail_send_service.Credentials')
    def test_explicit_4xx_is_refused_without_exposing_response_body(self, credentials_class, post):
        from .gmail_send_service import EnvoiRefuse

        credentials_class.return_value.token = 'access-test'
        credentials_class.return_value.refresh_token = 'refresh-test'
        post.return_value.status_code = 403
        post.return_value.text = 'sensitive server body'

        with self.assertRaises(EnvoiRefuse) as caught:
            self.send()

        self.assertNotIn('sensitive server body', str(caught.exception))

    @patch('api.gmail_send_service.requests.post')
    @patch('api.gmail_send_service.Credentials')
    def test_revoked_refresh_token_requires_reconnection_without_gmail_post(self, credentials_class, post):
        from .gmail_send_service import EnvoiRefuse

        credentials_class.return_value.refresh.side_effect = RefreshError('invalid_grant')

        with self.assertRaises(EnvoiRefuse) as caught:
            self.send()

        self.assertEqual(caught.exception.code, 'reconnect_required')
        self.connexion.refresh_from_db()
        self.assertEqual(self.connexion.statut, ConnexionGmail.Statut.RECONNEXION_REQUISE)
        post.assert_not_called()
