from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import ActionCandidature, Candidature


class ActionCandidatureModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='actions-model')
        self.candidature = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/actions-model',
            titre='Developpeuse backend',
        )

    def test_action_keeps_business_date_creation_date_and_parent_relation(self):
        business_date = timezone.now() - timedelta(days=1)
        action = ActionCandidature.objects.create(
            candidature=self.candidature,
            type_action=ActionCandidature.TypeAction.ENTRETIEN_VISIO,
            date_action=business_date,
            commentaire='Echange avec la responsable technique.',
        )

        self.assertEqual(action.date_action, business_date)
        self.assertIsNotNone(action.date_creation)
        self.assertEqual(list(self.candidature.actions.all()), [action])

    def test_actions_are_ordered_by_business_date_descending(self):
        older = ActionCandidature.objects.create(
            candidature=self.candidature,
            type_action=ActionCandidature.TypeAction.CANDIDATURE_ENVOYEE,
            date_action=timezone.now() - timedelta(days=2),
        )
        newer = ActionCandidature.objects.create(
            candidature=self.candidature,
            type_action=ActionCandidature.TypeAction.RELANCE,
            date_action=timezone.now(),
        )

        self.assertEqual(list(self.candidature.actions.all()), [newer, older])


class ActionCandidatureEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='actions-owner')
        self.other_user = User.objects.create_user(username='actions-other')
        self.client.force_authenticate(self.user)
        self.candidature = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/actions-owner',
            titre='Developpeuse Django',
        )
        self.other_candidature = Candidature.objects.create(
            utilisateur=self.other_user,
            url='https://example.com/actions-other',
            titre='Offre privee',
        )
        self.action = ActionCandidature.objects.create(
            candidature=self.candidature,
            type_action=ActionCandidature.TypeAction.CANDIDATURE_ENVOYEE,
            date_action=timezone.now() - timedelta(days=1),
            commentaire='CV transmis.',
        )
        self.other_action = ActionCandidature.objects.create(
            candidature=self.other_candidature,
            type_action=ActionCandidature.TypeAction.NOTE,
            date_action=timezone.now(),
            commentaire='Information privee.',
        )

    def test_list_and_create_actions_for_owned_candidature(self):
        list_response = self.client.get(f'/api/candidatures/{self.candidature.id}/actions/')

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in list_response.data], [self.action.id])

        response = self.client.post(
            f'/api/candidatures/{self.candidature.id}/actions/',
            {
                'candidature': self.other_candidature.id,
                'type_action': ActionCandidature.TypeAction.RELANCE,
                'date_action': '2026-09-14T10:30:00Z',
                'commentaire': 'Message envoye.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = ActionCandidature.objects.get(pk=response.data['id'])
        self.assertEqual(created.candidature, self.candidature)
        self.assertEqual(created.type_action, ActionCandidature.TypeAction.RELANCE)
        self.assertEqual(created.commentaire, 'Message envoye.')

    def test_detail_supports_get_patch_put_and_delete(self):
        url = f'/api/candidatures/{self.candidature.id}/actions/{self.action.id}/'
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(url, {'commentaire': 'CV et lettre transmis.'}, format='json')
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        put_response = self.client.put(
            url,
            {
                'type_action': ActionCandidature.TypeAction.ENTRETIEN_TEL,
                'date_action': '2026-09-15T08:00:00Z',
                'commentaire': 'Premier entretien.',
            },
            format='json',
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.action.refresh_from_db()
        self.assertEqual(self.action.type_action, ActionCandidature.TypeAction.ENTRETIEN_TEL)

        delete_response = self.client.delete(url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ActionCandidature.objects.filter(pk=self.action.id).exists())

    def test_actions_are_scoped_by_parent_and_authenticated_user(self):
        other_parent_url = f'/api/candidatures/{self.other_candidature.id}/actions/'
        self.assertEqual(self.client.get(other_parent_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.post(other_parent_url, {
                'type_action': ActionCandidature.TypeAction.NOTE,
                'date_action': '2026-09-14T10:30:00Z',
            }, format='json').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        mismatched_url = f'/api/candidatures/{self.candidature.id}/actions/{self.other_action.id}/'
        self.assertEqual(self.client.get(mismatched_url).status_code, status.HTTP_404_NOT_FOUND)

