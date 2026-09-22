from datetime import timedelta
from base64 import urlsafe_b64encode
from hashlib import sha256
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .gmail_oauth_service import (
    OAuthError,
    chiffrer,
    dechiffrer,
    demarrer_connexion,
    terminer_connexion,
    verifier_connexion,
)
from .models import ConnexionGmail, TentativeOAuthGmail


class GmailOAuthModelTests(TestCase):
    def test_one_connection_per_user_and_state_consumption(self):
        user = User.objects.create_user(username='gmail-owner')
        connexion = ConnexionGmail.objects.create(utilisateur=user, refresh_token_chiffre='encrypted')

        with self.assertRaises(IntegrityError), transaction.atomic():
            ConnexionGmail.objects.create(utilisateur=user, refresh_token_chiffre='duplicate')

        tentative = TentativeOAuthGmail.objects.create(
            utilisateur=user,
            state_digest='a' * 64,
            pkce_verifier_chiffre='encrypted-verifier',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        user.refresh_from_db()
        self.assertEqual(user.connexion_gmail, connexion)
        self.assertIsNone(tentative.consumed_at)


class GmailOAuthServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gmail-service-owner')
        self.other_user = User.objects.create_user(username='other-service-owner')
        self.config = override_settings(
            GMAIL_OAUTH_CLIENT_ID='client-id.example',
            GMAIL_OAUTH_CLIENT_SECRET='dummy-client-secret',
            GMAIL_OAUTH_REDIRECT_URI='http://localhost:8000/api/gmail/oauth/callback/',
            GMAIL_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'),
        )
        self.config.enable()
        self.addCleanup(self.config.disable)

    def test_refresh_token_is_encrypted_and_key_is_required(self):
        ciphertext = chiffrer('refresh-token-secret')

        self.assertNotIn('refresh-token-secret', ciphertext)
        self.assertEqual(dechiffrer(ciphertext), 'refresh-token-secret')
        with override_settings(GMAIL_TOKEN_ENCRYPTION_KEY=''):
            with self.assertRaises(OAuthError):
                chiffrer('another-token')

    @patch('socket.create_connection')
    def test_start_uses_state_pkce_offline_and_gmail_send_without_network(self, network):
        url = demarrer_connexion(self.user)

        params = parse_qs(urlsplit(url).query)
        tentative = TentativeOAuthGmail.objects.get(utilisateur=self.user)
        self.assertEqual(tentative.state_digest, sha256(params['state'][0].encode()).hexdigest())
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertEqual(params['access_type'], ['offline'])
        self.assertEqual(params['scope'], ['https://www.googleapis.com/auth/gmail.send'])
        self.assertEqual(params['redirect_uri'], ['http://localhost:8000/api/gmail/oauth/callback/'])
        self.assertEqual(params['prompt'], ['consent'])
        self.assertLessEqual(tentative.expires_at, timezone.now() + timedelta(minutes=10))
        self.assertGreater(tentative.expires_at, timezone.now() + timedelta(minutes=9))
        verifier = dechiffrer(tentative.pkce_verifier_chiffre)
        expected_challenge = urlsafe_b64encode(sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
        self.assertEqual(params['code_challenge'], [expected_challenge])
        self.assertNotIn(verifier, tentative.pkce_verifier_chiffre)
        network.assert_not_called()

    def test_start_removes_expired_pending_verifiers(self):
        TentativeOAuthGmail.objects.create(
            utilisateur=self.user,
            state_digest='e' * 64,
            pkce_verifier_chiffre=chiffrer('old-verifier'),
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        demarrer_connexion(self.user)

        self.assertFalse(TentativeOAuthGmail.objects.filter(state_digest='e' * 64).exists())
        self.assertEqual(TentativeOAuthGmail.objects.filter(utilisateur=self.user).count(), 1)

    @patch('socket.create_connection')
    def test_callback_stores_only_encrypted_refresh_token_for_starting_user(self, network):
        url = demarrer_connexion(self.user)
        state = parse_qs(urlsplit(url).query)['state'][0]
        expected_verifier = dechiffrer(TentativeOAuthGmail.objects.get(utilisateur=self.user).pkce_verifier_chiffre)
        flow = Mock()
        flow.credentials.refresh_token = 'new-refresh-token'

        with patch('api.gmail_oauth_service.Flow.from_client_config', return_value=flow) as factory:
            result = terminer_connexion(state=state, code='one-time-code')

        self.assertEqual(result, 'connected')
        connexion = ConnexionGmail.objects.get(utilisateur=self.user)
        self.assertEqual(connexion.statut, ConnexionGmail.Statut.CONNECTE)
        self.assertNotIn('new-refresh-token', connexion.refresh_token_chiffre)
        self.assertEqual(dechiffrer(connexion.refresh_token_chiffre), 'new-refresh-token')
        self.assertFalse(ConnexionGmail.objects.filter(utilisateur=self.other_user).exists())
        self.assertIsNotNone(TentativeOAuthGmail.objects.get(utilisateur=self.user).consumed_at)
        self.assertEqual(TentativeOAuthGmail.objects.get(utilisateur=self.user).pkce_verifier_chiffre, '')
        flow.fetch_token.assert_called_once_with(code='one-time-code')
        self.assertEqual(factory.call_args.kwargs['code_verifier'], expected_verifier)
        self.assertEqual(factory.call_args.kwargs['state'], state)
        network.assert_not_called()

    def test_callback_rejects_expired_and_reused_state_before_google(self):
        url = demarrer_connexion(self.user)
        state = parse_qs(urlsplit(url).query)['state'][0]
        tentative = TentativeOAuthGmail.objects.get(utilisateur=self.user)
        tentative.expires_at = timezone.now() - timedelta(seconds=1)
        tentative.save(update_fields=['expires_at'])
        with patch('api.gmail_oauth_service.Flow.from_client_config') as flow_factory:
            with self.assertRaises(OAuthError):
                terminer_connexion(state=state, code='code')
            flow_factory.assert_not_called()

            tentative.expires_at = timezone.now() + timedelta(minutes=1)
            tentative.save(update_fields=['expires_at'])
            flow_factory.return_value.credentials.refresh_token = 'valid-refresh'
            self.assertEqual(terminer_connexion(state=state, code='code'), 'connected')
            with self.assertRaises(OAuthError):
                terminer_connexion(state=state, code='code')
            self.assertEqual(flow_factory.return_value.fetch_token.call_count, 1)

    def test_callback_without_refresh_token_does_not_claim_connected(self):
        url = demarrer_connexion(self.user)
        state = parse_qs(urlsplit(url).query)['state'][0]
        with patch('api.gmail_oauth_service.Flow.from_client_config') as flow_factory:
            flow_factory.return_value.credentials.refresh_token = None
            with self.assertRaises(OAuthError):
                terminer_connexion(state=state, code='code')

        self.assertFalse(ConnexionGmail.objects.filter(utilisateur=self.user).exists())

    def test_denied_consent_consumes_state_without_contacting_google(self):
        url = demarrer_connexion(self.user)
        state = parse_qs(urlsplit(url).query)['state'][0]

        with patch('api.gmail_oauth_service.Flow.from_client_config') as flow_factory:
            with self.assertRaises(OAuthError):
                terminer_connexion(state=state, error='access_denied')
            flow_factory.assert_not_called()

        tentative = TentativeOAuthGmail.objects.get(utilisateur=self.user)
        self.assertIsNotNone(tentative.consumed_at)
        self.assertEqual(tentative.pkce_verifier_chiffre, '')
        self.assertFalse(ConnexionGmail.objects.filter(utilisateur=self.user).exists())

    @patch('api.gmail_oauth_service.Credentials.refresh')
    @patch('socket.create_connection')
    def test_verify_refreshes_expired_access_without_storing_it(self, network, refresh):
        connexion = ConnexionGmail.objects.create(
            utilisateur=self.user,
            refresh_token_chiffre=chiffrer('refresh-token'),
        )

        self.assertEqual(verifier_connexion(self.user), 'connected')

        refresh.assert_called_once()
        connexion.refresh_from_db()
        self.assertEqual(dechiffrer(connexion.refresh_token_chiffre), 'refresh-token')
        self.assertIsNotNone(connexion.date_verification)
        network.assert_not_called()

    @patch('api.gmail_oauth_service.Credentials.refresh', autospec=True)
    def test_verify_persists_rotated_refresh_token_encrypted(self, refresh):
        connexion = ConnexionGmail.objects.create(
            utilisateur=self.user,
            refresh_token_chiffre=chiffrer('old-refresh-token'),
        )
        refresh.side_effect = lambda credentials, request: setattr(credentials, '_refresh_token', 'rotated-refresh-token')

        self.assertEqual(verifier_connexion(self.user), 'connected')

        connexion.refresh_from_db()
        self.assertEqual(dechiffrer(connexion.refresh_token_chiffre), 'rotated-refresh-token')

    @patch('api.gmail_oauth_service.Credentials.refresh')
    def test_revoked_token_requires_reconnection(self, refresh):
        from google.auth.exceptions import RefreshError

        connexion = ConnexionGmail.objects.create(
            utilisateur=self.user,
            refresh_token_chiffre=chiffrer('revoked-token'),
        )
        refresh.side_effect = RefreshError('invalid_grant: Token has been revoked')

        self.assertEqual(verifier_connexion(self.user), 'reconnect_required')
        connexion.refresh_from_db()
        self.assertEqual(connexion.statut, ConnexionGmail.Statut.RECONNEXION_REQUISE)
        self.assertEqual(connexion.refresh_token_chiffre, '')

    @patch('api.gmail_oauth_service.Credentials.refresh')
    def test_temporary_refresh_failure_does_not_discard_credentials(self, refresh):
        from google.auth.exceptions import TransportError

        connexion = ConnexionGmail.objects.create(
            utilisateur=self.user,
            refresh_token_chiffre=chiffrer('still-valid-token'),
        )
        refresh.side_effect = TransportError('temporary connection problem')

        with self.assertRaises(OAuthError):
            verifier_connexion(self.user)
        connexion.refresh_from_db()
        self.assertEqual(connexion.statut, ConnexionGmail.Statut.CONNECTE)
        self.assertEqual(dechiffrer(connexion.refresh_token_chiffre), 'still-valid-token')


class GmailOAuthEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gmail-api-owner')
        self.other_user = User.objects.create_user(username='gmail-api-other')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')
        self.config = override_settings(
            GMAIL_OAUTH_CLIENT_ID='client-id.example',
            GMAIL_OAUTH_CLIENT_SECRET='dummy-client-secret',
            GMAIL_OAUTH_REDIRECT_URI='http://localhost:8000/api/gmail/oauth/callback/',
            GMAIL_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode('ascii'),
            FRONTEND_URL='http://localhost:3000',
        )
        self.config.enable()
        self.addCleanup(self.config.disable)

    @patch('socket.create_connection')
    def test_connect_returns_only_authorization_url_and_creates_attempt(self, network):
        response = self.client.post('/api/gmail/connecter/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {'authorization_url'})
        self.assertTrue(response.data['authorization_url'].startswith('https://accounts.google.com/'))
        self.assertEqual(TentativeOAuthGmail.objects.filter(utilisateur=self.user).count(), 1)
        self.assertNotIn('dummy-client-secret', str(response.data))
        network.assert_not_called()

    def test_status_is_scoped_and_never_returns_credentials(self):
        ConnexionGmail.objects.create(
            utilisateur=self.other_user,
            refresh_token_chiffre=chiffrer('private-refresh-token'),
        )

        response = self.client.get('/api/gmail/statut/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'status': 'disconnected'})
        self.assertNotIn('private-refresh-token', str(response.data))

    @patch('api.gmail_oauth_service.Credentials.refresh')
    @patch('socket.create_connection')
    def test_verify_revoked_token_returns_clear_reconnection_message(self, network, refresh):
        from google.auth.exceptions import RefreshError

        ConnexionGmail.objects.create(
            utilisateur=self.user,
            refresh_token_chiffre=chiffrer('revoked-refresh-token'),
        )
        refresh.side_effect = RefreshError('invalid_grant')

        response = self.client.post('/api/gmail/verifier/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'reconnect_required')
        self.assertIn('Reconnectez', response.data['message'])
        self.assertNotIn('revoked-refresh-token', str(response.data))
        network.assert_not_called()

    @patch('socket.create_connection')
    def test_callback_redirects_to_fixed_frontend_url_without_code_or_token(self, network):
        start = self.client.post('/api/gmail/connecter/')
        state = parse_qs(urlsplit(start.data['authorization_url']).query)['state'][0]
        with patch('api.gmail_oauth_service.Flow.from_client_config') as flow_factory:
            flow_factory.return_value.credentials.refresh_token = 'secret-refresh-token'
            response = self.client.get('/api/gmail/oauth/callback/', {'state': state, 'code': 'one-time-code'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:3000/parametres?gmail=connected')
        self.assertNotIn('one-time-code', response['Location'])
        self.assertNotIn('secret-refresh-token', response['Location'])
        self.assertEqual(ConnexionGmail.objects.get(utilisateur=self.user).statut, ConnexionGmail.Statut.CONNECTE)
        network.assert_not_called()

    def test_invalid_callback_state_never_exchanges_code(self):
        with patch('api.gmail_oauth_service.Flow.from_client_config') as flow_factory:
            response = self.client.get('/api/gmail/oauth/callback/', {'state': 'invalid', 'code': 'secret-code'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:3000/parametres?gmail=error')
        flow_factory.assert_not_called()

    def test_connect_status_and_verify_require_authentication(self):
        self.client.credentials()
        for method, path in (
            (self.client.post, '/api/gmail/connecter/'),
            (self.client.get, '/api/gmail/statut/'),
            (self.client.post, '/api/gmail/verifier/'),
        ):
            with self.subTest(path=path):
                self.assertEqual(method(path).status_code, 401)

    def test_missing_configuration_returns_controlled_error_without_attempt(self):
        with override_settings(GMAIL_TOKEN_ENCRYPTION_KEY=''):
            response = self.client.post('/api/gmail/connecter/')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data, {'detail': 'La connexion Gmail est indisponible.'})
        self.assertFalse(TentativeOAuthGmail.objects.filter(utilisateur=self.user).exists())
