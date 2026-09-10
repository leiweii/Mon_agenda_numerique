from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class AuthenticationEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='secret-password',
        )

    def authenticate_with_token(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return token

    def test_login_returns_a_token_and_the_authenticated_user(self):
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'secret-password'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], {
            'id': self.user.id,
            'username': 'alice',
            'email': 'alice@example.com',
        })
        self.assertTrue(Token.objects.filter(key=response.data['token'], user=self.user).exists())

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            '/api/auth/login/',
            {'username': 'alice', 'password': 'wrong-password'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {'error': 'Identifiants invalides'})

    def test_current_user_returns_the_user_bound_to_the_token(self):
        self.authenticate_with_token()

        response = self.client.get('/api/auth/user/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'id': self.user.id,
            'username': 'alice',
            'email': 'alice@example.com',
        })

    def test_current_user_requires_authentication(self):
        response = self.client.get('/api/auth/user/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_the_token(self):
        token = self.authenticate_with_token()

        response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
        self.assertEqual(self.client.get('/api/auth/user/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_succeeds_when_an_authenticated_user_has_no_token(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'message': 'Déconnexion réussie'})
