from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core import mail
from django.test import override_settings
from unittest.mock import patch
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from datetime import datetime, time, timedelta
from agenda.models import Categorie, PreferenceUtilisateur, StatistiqueUtilisation, Tache


class AuthenticationEndpointsTests(APITestCase):
    def setUp(self):
        cache.clear()
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

    def test_login_uses_the_same_error_for_an_unknown_identifier(self):
        wrong_password_response = self.client.post(
            '/api/auth/login/',
            {'identifier': 'alice', 'password': 'wrong-password'},
            format='json',
        )
        unknown_identifier_response = self.client.post(
            '/api/auth/login/',
            {'identifier': 'inconnu@example.com', 'password': 'wrong-password'},
            format='json',
        )

        self.assertEqual(wrong_password_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(unknown_identifier_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_password_response.data, unknown_identifier_response.data)

    def test_login_limits_anonymous_failed_attempts(self):
        payload = {'identifier': 'alice', 'password': 'wrong-password'}

        for _ in range(5):
            response = self.client.post('/api/auth/login/', payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post('/api/auth/login/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_register_uses_email_confirmation_and_creates_a_hashed_password(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'Charlie@Example.COM',
                'password': 'Une phrase de passe robuste 2026!',
                'password_confirmation': 'Une phrase de passe robuste 2026!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(email='charlie@example.com')
        self.assertTrue(created_user.username)
        self.assertTrue(created_user.password.startswith('pbkdf2_'))
        self.assertTrue(created_user.check_password('Une phrase de passe robuste 2026!'))
        self.assertEqual(response.data['user'], {
            'id': created_user.id,
            'username': created_user.username,
            'email': 'charlie@example.com',
        })
        self.assertTrue(Token.objects.filter(key=response.data['token'], user=created_user).exists())

    def test_register_rejects_mismatched_password_confirmation(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'Charlie@Example.COM',
                'password': 'Une phrase de passe robuste 2026!',
                'password_confirmation': 'Un autre mot de passe robuste 2026!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Les mots de passe ne correspondent pas.'})
        self.assertFalse(User.objects.filter(email='charlie@example.com').exists())

    def test_register_reports_an_existing_email(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'ALICE@EXAMPLE.COM',
                'password': 'Une phrase de passe robuste 2026!',
                'password_confirmation': 'Une phrase de passe robuste 2026!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Un compte existe déjà avec cette adresse e-mail.'})

    def test_register_suffixes_colliding_generated_usernames(self):
        password = 'Une phrase de passe robuste 2026!'
        first_response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'jean.dupont@gmail.com',
                'password': password,
                'password_confirmation': password,
            },
            format='json',
        )
        second_response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'jean-dupont@yahoo.fr',
                'password': password,
                'password_confirmation': password,
            },
            format='json',
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(email='jean.dupont@gmail.com').username, 'jean-dupont')
        self.assertEqual(User.objects.get(email='jean-dupont@yahoo.fr').username, 'jean-dupont-2')

    def test_login_accepts_existing_username_and_new_account_email(self):
        password = 'Une phrase de passe robuste 2026!'
        self.client.post(
            '/api/auth/register/',
            {
                'email': 'charlie@example.com',
                'password': password,
                'password_confirmation': password,
            },
            format='json',
        )

        username_response = self.client.post(
            '/api/auth/login/',
            {'identifier': 'alice', 'password': 'secret-password'},
            format='json',
        )
        email_response = self.client.post(
            '/api/auth/login/',
            {'identifier': 'CHARLIE@EXAMPLE.COM', 'password': password},
            format='json',
        )

        self.assertEqual(username_response.status_code, status.HTTP_200_OK)
        self.assertEqual(email_response.status_code, status.HTTP_200_OK)

    def test_register_enforces_configured_password_validators(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'nouveau@example.com',
                'password': 'court',
                'password_confirmation': 'court',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Mot de passe invalide.')
        self.assertTrue(response.data['details'])
        self.assertFalse(User.objects.filter(email='nouveau@example.com').exists())

    def test_register_limits_anonymous_attempts_by_ip(self):
        payload = {
            'email': 'nouveau@example.com',
            'password': 'court',
            'password_confirmation': 'court',
        }

        for _ in range(5):
            response = self.client.post('/api/auth/register/', payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post('/api/auth/register/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_request_is_generic_and_sends_an_email_for_an_existing_account(self):
        existing_response = self.client.post(
            '/api/auth/mot-de-passe-oublie/',
            {'email': 'ALICE@EXAMPLE.COM'},
            format='json',
        )
        unknown_response = self.client.post(
            '/api/auth/mot-de-passe-oublie/',
            {'email': 'inconnu@example.com'},
            format='json',
        )

        expected_response = {'message': 'Si ce compte existe, un e-mail a été envoyé.'}
        self.assertEqual(existing_response.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown_response.status_code, status.HTTP_200_OK)
        self.assertEqual(existing_response.data, expected_response)
        self.assertEqual(unknown_response.data, expected_response)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reinitialiser-mot-de-passe/', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_request_limits_requests_per_normalized_email(self):
        for _ in range(3):
            response = self.client.post(
                '/api/auth/mot-de-passe-oublie/',
                {'email': 'ALICE@EXAMPLE.COM'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            '/api/auth/mot-de-passe-oublie/',
            {'email': 'alice@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_password_reset_request_limits_requests_per_ip(self):
        for index in range(5):
            response = self.client.post(
                '/api/auth/mot-de-passe-oublie/',
                {'email': f'inconnu{index}@example.com'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            '/api/auth/mot-de-passe-oublie/',
            {'email': 'inconnu6@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_password_reset_changes_the_password_and_invalidates_the_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        password = 'Un nouveau mot de passe robuste 2026!'

        response = self.client.post(
            '/api/auth/reinitialiser-mot-de-passe/',
            {
                'uid': uid,
                'token': token,
                'password': password,
                'password_confirmation': password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'message': 'Mot de passe réinitialisé avec succès.'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(password))
        self.assertFalse(default_token_generator.check_token(self.user, token))

    def test_password_reset_rejects_an_invalid_or_expired_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        expired_token = default_token_generator._make_token_with_timestamp(self.user, 0, self.user.password)

        for token in ('invalide', expired_token):
            response = self.client.post(
                '/api/auth/reinitialiser-mot-de-passe/',
                {
                    'uid': uid,
                    'token': token,
                    'password': 'Un nouveau mot de passe robuste 2026!',
                    'password_confirmation': 'Un nouveau mot de passe robuste 2026!',
                },
                format='json',
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, {'error': 'Lien de réinitialisation invalide ou expiré.'})

    def test_password_reset_confirmation_limits_requests_per_ip(self):
        payload = {
            'uid': 'invalide',
            'token': 'invalide',
            'password': 'Un nouveau mot de passe robuste 2026!',
            'password_confirmation': 'Un nouveau mot de passe robuste 2026!',
        }

        for _ in range(5):
            response = self.client.post('/api/auth/reinitialiser-mot-de-passe/', payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post('/api/auth/reinitialiser-mot-de-passe/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

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


class TacheEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        self.category = Categorie.objects.create(utilisateur=self.user, nom='Travail')
        self.other_category = Categorie.objects.create(utilisateur=self.other_user, nom='Privé')
        self.own_task = Tache.objects.create(
            utilisateur=self.user,
            titre='Préparer la réunion',
            description='Finaliser l ordre du jour',
            date_echeance=timezone.now(),
            priorite=3,
            categorie=self.category,
        )
        self.other_task = Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tâche de Bob',
            date_echeance=timezone.now(),
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def task_payload(self, **overrides):
        payload = {
            'titre': 'Rédiger le compte rendu',
            'description': 'Envoyer la synthèse à l équipe',
            'date_echeance': '2026-09-15T09:30:00Z',
            'priorite': 4,
            'categorie': self.category.id,
        }
        payload.update(overrides)
        return payload

    def test_list_returns_only_the_authenticated_users_tasks(self):
        response = self.client.get('/api/taches/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([task['id'] for task in response.data], [self.own_task.id])

    def test_create_assigns_the_authenticated_user_and_owned_category(self):
        response = self.client.post('/api/taches/', self.task_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Tache.objects.get(pk=response.data['id'])
        self.assertEqual(task.utilisateur, self.user)
        self.assertEqual(task.categorie, self.category)
        self.assertEqual(task.priorite, 4)

    def test_create_rejects_a_category_owned_by_another_user(self):
        response = self.client.post(
            '/api/taches/',
            self.task_payload(categorie=self.other_category.id),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('categorie', response.data)

    def test_create_persists_task_emoji_colour_and_urgent_priority(self):
        response = self.client.post(
            '/api/taches/',
            self.task_payload(emoji='🎯', couleur='#1a2b3c', priorite=4),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Tache.objects.get(pk=response.data['id'])
        self.assertEqual(task.emoji, '🎯')
        self.assertEqual(task.couleur, '#1a2b3c')
        self.assertEqual(task.priorite, 4)

    def test_create_rejects_a_task_with_an_invalid_colour(self):
        response = self.client.post(
            '/api/taches/',
            self.task_payload(couleur='blue'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('couleur', response.data)

    def test_update_changes_an_owned_task(self):
        response = self.client.put(
            f'/api/taches/{self.own_task.id}/',
            self.task_payload(titre='Réunion replanifiée', priorite=1),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own_task.refresh_from_db()
        self.assertEqual(self.own_task.titre, 'Réunion replanifiée')
        self.assertEqual(self.own_task.priorite, 1)

    def test_update_and_delete_cannot_access_another_users_task(self):
        response = self.client.put(
            f'/api/taches/{self.other_task.id}/',
            self.task_payload(),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.delete(f'/api/taches/{self.other_task.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Tache.objects.filter(pk=self.other_task.id).exists())

    def test_delete_removes_an_owned_task(self):
        response = self.client.delete(f'/api/taches/{self.own_task.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tache.objects.filter(pk=self.own_task.id).exists())

    def test_aujourdhui_returns_only_the_authenticated_users_tasks_due_today(self):
        self.own_task.delete()
        today = timezone.localdate()
        tasks = [
            Tache.objects.create(
                utilisateur=self.user,
                titre='Tâche du jour',
                date_echeance=timezone.make_aware(datetime.combine(today, time(12))),
            ),
            Tache.objects.create(
                utilisateur=self.user,
                titre='Tâche de demain',
                date_echeance=timezone.make_aware(
                    datetime.combine(today + timedelta(days=1), time(12))
                ),
            ),
        ]
        Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tâche du jour de Bob',
            date_echeance=timezone.make_aware(datetime.combine(today, time(12))),
        )

        response = self.client.get('/api/taches/aujourd_hui/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({task['id'] for task in response.data}, {tasks[0].id})

    def test_cette_semaine_returns_tasks_from_monday_through_sunday(self):
        self.own_task.delete()
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        tasks = [
            Tache.objects.create(
                utilisateur=self.user,
                titre='Tâche du lundi',
                date_echeance=timezone.make_aware(datetime.combine(monday, time(9))),
            ),
            Tache.objects.create(
                utilisateur=self.user,
                titre='Tâche du dimanche',
                date_echeance=timezone.make_aware(datetime.combine(sunday, time(18))),
            ),
        ]
        Tache.objects.create(
            utilisateur=self.user,
            titre='Tâche de la semaine prochaine',
            date_echeance=timezone.make_aware(
                datetime.combine(sunday + timedelta(days=1), time(9))
            ),
        )
        Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tâche de Bob cette semaine',
            date_echeance=timezone.make_aware(datetime.combine(monday, time(9))),
        )

        response = self.client.get('/api/taches/cette_semaine/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({task['id'] for task in response.data}, {task.id for task in tasks})


class CategorieEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        self.category = Categorie.objects.create(utilisateur=self.user, nom='Travail')
        self.other_category = Categorie.objects.create(utilisateur=self.other_user, nom='Privé')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_list_returns_only_the_authenticated_users_categories(self):
        response = self.client.get('/api/categories/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([category['id'] for category in response.data], [self.category.id])

    def test_create_assigns_the_authenticated_user_to_the_category(self):
        response = self.client.post(
            '/api/categories/',
            {'nom': 'Santé', 'couleur': '#2ecc71', 'emoji': '💪'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        category = Categorie.objects.get(pk=response.data['id'])
        self.assertEqual(category.utilisateur, self.user)
        self.assertEqual(category.nom, 'Santé')

    def test_update_cannot_transfer_a_category_to_another_user(self):
        response = self.client.put(
            f'/api/categories/{self.category.id}/',
            {
                'nom': 'Travail important',
                'couleur': '#3498db',
                'emoji': '💼',
                'utilisateur': self.other_user.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.nom, 'Travail important')
        self.assertEqual(self.category.utilisateur, self.user)

    def test_delete_category_keeps_tasks_and_clears_their_category(self):
        task = Tache.objects.create(
            utilisateur=self.user,
            titre='Préparer la réunion',
            date_echeance=timezone.now(),
            categorie=self.category,
        )

        response = self.client.delete(f'/api/categories/{self.category.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Tache.objects.filter(pk=task.id).exists())
        task.refresh_from_db()
        self.assertIsNone(task.categorie)


class PreferenceEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def preference_payload(self, **overrides):
        payload = {
            'heure_productive_debut': '08:30:00',
            'heure_productive_fin': '16:30:00',
            'theme': 'sombre',
            'notifications_actives': False,
        }
        payload.update(overrides)
        return payload

    def test_create_assigns_preferences_to_the_authenticated_user(self):
        response = self.client.post('/api/preferences/', self.preference_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        preference = PreferenceUtilisateur.objects.get(pk=response.data['id'])
        self.assertEqual(preference.utilisateur, self.user)
        self.assertEqual(preference.theme, 'sombre')
        self.assertFalse(preference.notifications_actives)

    def test_update_changes_the_authenticated_users_existing_preferences(self):
        preference = PreferenceUtilisateur.objects.create(
            utilisateur=self.user,
            heure_productive_debut='09:00',
            heure_productive_fin='17:00',
            theme='clair',
            notifications_actives=True,
        )

        response = self.client.put(
            f'/api/preferences/{preference.id}/',
            self.preference_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        preference.refresh_from_db()
        self.assertEqual(preference.theme, 'sombre')
        self.assertFalse(preference.notifications_actives)

    def test_preferences_reject_an_invalid_theme(self):
        response = self.client.post(
            '/api/preferences/',
            self.preference_payload(theme='auto'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('theme', response.data)

    def test_preferences_reject_a_productive_time_range_ending_before_it_starts(self):
        response = self.client.post(
            '/api/preferences/',
            self.preference_payload(heure_productive_debut='18:00:00', heure_productive_fin='09:00:00'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('heure_productive_fin', response.data)


class StatistiquesEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def create_task(self, priorite, completee=False, utilisateur=None):
        return Tache.objects.create(
            utilisateur=utilisateur or self.user,
            titre=f'Tâche priorité {priorite}',
            date_echeance=timezone.now(),
            priorite=priorite,
            completee=completee,
        )

    def test_statistiques_returns_totals_and_all_four_priorities_for_the_user(self):
        self.create_task(1, completee=True)
        self.create_task(3)
        self.create_task(3)
        self.create_task(4, completee=True, utilisateur=self.other_user)

        response = self.client.get('/api/taches/statistiques/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 3)
        self.assertEqual(response.data['completees'], 1)
        self.assertEqual(response.data['en_cours'], 2)
        self.assertAlmostEqual(response.data['taux_completion'], 100 / 3)
        self.assertEqual(response.data['par_priorite'], [
            {'priorite': 1, 'count': 1},
            {'priorite': 2, 'count': 0},
            {'priorite': 3, 'count': 2},
            {'priorite': 4, 'count': 0},
        ])

    def test_statistiques_returns_zero_counts_for_an_empty_task_list(self):
        response = self.client.get('/api/taches/statistiques/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 0)
        self.assertEqual(response.data['taux_completion'], 0)
        self.assertEqual(response.data['par_priorite'], [
            {'priorite': 1, 'count': 0},
            {'priorite': 2, 'count': 0},
            {'priorite': 3, 'count': 0},
            {'priorite': 4, 'count': 0},
        ])


class MeilleurMomentEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        self.user_task = Tache.objects.create(
            utilisateur=self.user,
            titre='Tâche Alice',
            date_echeance=timezone.now(),
        )
        self.other_task = Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tâche Bob',
            date_echeance=timezone.now(),
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def add_completion(self, hour, utilisateur=None, tache=None):
        StatistiqueUtilisation.objects.create(
            utilisateur=utilisateur or self.user,
            tache=tache or self.user_task,
            heure_completion=time(hour),
            duree_estimee=30,
        )

    def test_meilleur_moment_returns_the_users_three_most_frequent_hours_in_order(self):
        for hour in [14, 14, 9, 9, 17]:
            self.add_completion(hour)
        for hour in [8, 8, 8]:
            self.add_completion(hour, utilisateur=self.other_user, tache=self.other_task)

        response = self.client.get('/api/taches/meilleur_moment/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [9, 14, 17],
            'message': 'Vous êtes plus productif vers 9h',
        })

    def test_meilleur_moment_returns_the_fallback_contract_when_no_completion_exists(self):
        response = self.client.get('/api/taches/meilleur_moment/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [],
            'message': 'Pas assez de données pour une recommandation',
        })

    def test_meilleur_moment_requires_authentication(self):
        self.client.credentials()

        response = self.client.get('/api/taches/meilleur_moment/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RecommandationIAEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.other_user = User.objects.create_user(username='bob', password='secret-password')
        self.user_task = Tache.objects.create(
            utilisateur=self.user,
            titre='Tâche Alice',
            date_echeance=timezone.now(),
        )
        Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tâche Bob',
            date_echeance=timezone.now(),
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @patch('api.views.parser_reponse', return_value={
        'heures_recommandees': [10, 15],
        'message': 'Concentrez-vous sur vos tâches importantes.',
    })
    @patch('api.views.appeler_llm', return_value='{"heures_recommandees": [10, 15], "message": "..."}')
    @patch('api.views.construire_prompt', return_value='prompt nettoye')
    def test_recommandation_ia_returns_the_validated_llm_response(self, construire_prompt, appeler_llm, parser_reponse):
        response = self.client.get('/api/taches/recommandation_ia/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [10, 15],
            'message': 'Concentrez-vous sur vos tâches importantes.',
        })

    @patch('api.views.appeler_llm', return_value=None)
    @patch('api.views.construire_prompt', return_value='prompt nettoye')
    def test_recommandation_ia_falls_back_when_the_llm_call_fails(self, construire_prompt, appeler_llm):
        StatistiqueUtilisation.objects.create(
            utilisateur=self.user,
            tache=self.user_task,
            heure_completion=time(14),
            duree_estimee=30,
        )

        response = self.client.get('/api/taches/recommandation_ia/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [14],
            'message': 'Vous êtes plus productif vers 14h',
        })

    @patch('api.views.parser_reponse', return_value=None)
    @patch('api.views.appeler_llm', return_value='reponse non JSON')
    @patch('api.views.construire_prompt', return_value='prompt nettoye')
    def test_recommandation_ia_falls_back_when_the_llm_response_is_invalid(self, construire_prompt, appeler_llm, parser_reponse):
        response = self.client.get('/api/taches/recommandation_ia/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [],
            'message': 'Pas assez de données pour une recommandation',
        })

    def test_recommandation_ia_requires_authentication(self):
        self.client.credentials()

        response = self.client.get('/api/taches/recommandation_ia/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
