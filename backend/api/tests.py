from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from datetime import datetime, time, timedelta
from agenda.models import Categorie, Tache


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
