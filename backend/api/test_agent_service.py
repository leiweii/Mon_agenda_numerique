import importlib.util
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from api.models import ActionEnAttente, ConversationAgent, MessageAgent


FALLBACK_MESSAGE = (
    "Je n'ai pas reussi a conclure en un nombre raisonnable d'etapes. "
    "Peux-tu reformuler ta demande de facon plus precise ?"
)


def final_response(text):
    return SimpleNamespace(text=text, tool_call=None, content=[{'type': 'text', 'text': text}])


def tool_response(tool_use_id='tool-1', name='get_today_tasks', arguments=None):
    arguments = arguments or {}
    tool_call = SimpleNamespace(id=tool_use_id, name=name, arguments=arguments)
    return SimpleNamespace(
        text='',
        tool_call=tool_call,
        content=[{'type': 'tool_use', 'id': tool_use_id, 'name': name, 'input': arguments}],
    )


class AgentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent-service-owner')
        self.conversation = ConversationAgent.objects.create(utilisateur=self.user)

    def _load_service(self):
        self.assertIsNotNone(importlib.util.find_spec('api.agent_service'))
        from api import agent_service

        return agent_service

    def test_stops_and_persists_messages_when_llm_returns_final_text(self):
        agent_service = self._load_service()

        with patch('api.agent_service.appeler_llm', return_value=final_response('Voici ton programme.')) as call_llm:
            result = agent_service.executer_agent(self.conversation, 'Planifie ma journee.', self.user)

        self.assertEqual(result, 'Voici ton programme.')
        self.assertEqual(call_llm.call_count, 1)
        self.assertEqual(
            list(self.conversation.messages.values_list('role', 'contenu', 'tool_name')),
            [
                (MessageAgent.Role.UTILISATEUR, 'Planifie ma journee.', ''),
                (MessageAgent.Role.AGENT, 'Voici ton programme.', ''),
            ],
        )

    def test_executes_a_read_tool_then_returns_the_next_final_response(self):
        agent_service = self._load_service()

        with patch(
            'api.agent_service.appeler_llm',
            side_effect=[tool_response(), final_response('Tu n\'as aucune tache aujourd\'hui.')],
        ) as call_llm:
            result = agent_service.executer_agent(self.conversation, 'Que dois-je faire ?', self.user)

        self.assertEqual(result, "Tu n'as aucune tache aujourd'hui.")
        self.assertEqual(call_llm.call_count, 2)
        tool_message = self.conversation.messages.get(role=MessageAgent.Role.OUTIL)
        self.assertEqual(tool_message.tool_name, 'get_today_tasks')
        self.assertIn('"taches": []', tool_message.contenu)

    def test_returns_exact_fallback_after_five_tool_steps(self):
        agent_service = self._load_service()

        with patch('api.agent_service.appeler_llm', return_value=tool_response()) as call_llm:
            result = agent_service.executer_agent(self.conversation, 'Continue sans fin.', self.user)

        self.assertEqual(result, FALLBACK_MESSAGE)
        self.assertEqual(call_llm.call_count, 5)
        self.assertEqual(
            self.conversation.messages.filter(role=MessageAgent.Role.OUTIL).count(),
            5,
        )
        self.assertTrue(
            self.conversation.messages.filter(
                role=MessageAgent.Role.AGENT,
                contenu=FALLBACK_MESSAGE,
            ).exists()
        )

    def test_passes_the_current_local_date_to_the_llm(self):
        agent_service = self._load_service()
        current_date = date(2026, 9, 15)

        with (
            patch('api.agent_service.timezone.localdate', return_value=current_date),
            patch('api.agent_service.appeler_llm', return_value=final_response('Reponse.')) as call_llm,
        ):
            agent_service.executer_agent(self.conversation, 'Quel jour sommes-nous ?', self.user)

        self.assertEqual(call_llm.call_args.kwargs['date_du_jour'], current_date)

    def test_stops_on_a_write_tool_and_stores_an_exact_pending_action(self):
        agent_service = self._load_service()
        self.assertIn('create_task', agent_service.TOOL_REGISTRY)
        arguments = {
            'titre': 'Preparer entretien',
            'priorite': 4,
            'date_echeance': '2026-09-16T10:00:00+02:00',
        }

        with patch(
            'api.agent_service.appeler_llm',
            return_value=tool_response(name='create_task', arguments=arguments),
        ) as call_llm:
            result = agent_service.executer_agent(
                self.conversation,
                'Cree une tache pour mon entretien.',
                self.user,
            )

        action = ActionEnAttente.objects.get()
        self.assertEqual(call_llm.call_count, 1)
        self.assertEqual(action.conversation, self.conversation)
        self.assertEqual(action.utilisateur, self.user)
        self.assertEqual(action.tool_name, 'create_task')
        self.assertEqual(action.arguments, arguments)
        self.assertEqual(action.statut, ActionEnAttente.Statut.EN_ATTENTE)
        self.assertFalse(self.user.taches.exists())
        self.assertEqual(result.action_id, action.id)
        self.assertIn('Preparer entretien', result.message)


class AgentChatEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent-chat-owner')
        self.other_user = User.objects.create_user(username='agent-chat-other')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_chat_creates_a_conversation_and_returns_the_agent_message(self):
        with patch('api.agent_service.appeler_llm', return_value=final_response('Voici ton programme.')):
            response = self.client.post(
                '/api/agent/chat/',
                {'message': 'Planifie ma journee.'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        conversation = ConversationAgent.objects.get(utilisateur=self.user)
        self.assertEqual(response.data, {
            'conversation_id': conversation.id,
            'message': 'Voici ton programme.',
        })

    def test_chat_reuses_only_a_conversation_owned_by_the_user(self):
        own_conversation = ConversationAgent.objects.create(utilisateur=self.user)
        other_conversation = ConversationAgent.objects.create(utilisateur=self.other_user)

        with patch('api.agent_service.appeler_llm', return_value=final_response('Reponse.')):
            own_response = self.client.post(
                '/api/agent/chat/',
                {'conversation_id': own_conversation.id, 'message': 'Continue.'},
                format='json',
            )
            other_response = self.client.post(
                '/api/agent/chat/',
                {'conversation_id': other_conversation.id, 'message': 'Continue.'},
                format='json',
            )

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(own_response.data['conversation_id'], own_conversation.id)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(other_conversation.messages.exists())

    def test_chat_rejects_an_empty_message_without_creating_a_conversation(self):
        response = self.client.post('/api/agent/chat/', {'message': '   '}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'erreur': 'Le message est requis.'})
        self.assertFalse(ConversationAgent.objects.exists())

    def test_chat_returns_a_pending_action_without_its_arguments(self):
        arguments = {
            'titre': 'Tache stockee',
            'priorite': 3,
            'date_echeance': '2026-09-16T10:00:00+02:00',
        }

        with patch(
            'api.agent_service.appeler_llm',
            return_value=tool_response(name='create_task', arguments=arguments),
        ):
            response = self.client.post(
                '/api/agent/chat/',
                {'message': 'Cree cette tache.'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action = ActionEnAttente.objects.get()
        self.assertEqual(response.data['action_en_attente'], {
            'id': action.id,
            'description': response.data['message'],
        })
        self.assertNotIn('arguments', response.data['action_en_attente'])

    def test_conversation_history_returns_messages_and_pending_actions_without_arguments(self):
        conversation = ConversationAgent.objects.create(utilisateur=self.user)
        MessageAgent.objects.create(
            conversation=conversation,
            role=MessageAgent.Role.UTILISATEUR,
            contenu='Cree une tache.',
        )
        proposal = MessageAgent.objects.create(
            conversation=conversation,
            role=MessageAgent.Role.AGENT,
            contenu=(
                'Je propose de creer la tache « Relancer Alice ». '
                "Confirme cette action pour l'executer."
            ),
        )
        action = ActionEnAttente.objects.create(
            conversation=conversation,
            utilisateur=self.user,
            tool_name='create_task',
            arguments={'titre': 'Relancer Alice', 'priorite': 3},
        )

        response = self.client.get(f'/api/agent/conversations/{conversation.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['conversation_id'], conversation.id)
        self.assertEqual(
            [(item['role'], item['contenu']) for item in response.data['messages']],
            [
                ('utilisateur', 'Cree une tache.'),
                ('agent', proposal.contenu),
            ],
        )
        self.assertEqual(response.data['actions_en_attente'], [{
            'id': action.id,
            'description': proposal.contenu,
            'statut': ActionEnAttente.Statut.EN_ATTENTE,
        }])
        self.assertNotIn('arguments', response.data['actions_en_attente'][0])

    def test_conversation_history_is_scoped_to_its_owner(self):
        other_conversation = ConversationAgent.objects.create(utilisateur=self.other_user)

        response = self.client.get(f'/api/agent/conversations/{other_conversation.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_planning_journey_reads_both_sources_then_confirms_and_cancels_writes(self):
        from api import agent_service
        from api.agent_tools import get_applications, get_today_tasks

        today_tasks = Mock(wraps=get_today_tasks)
        applications = Mock(wraps=get_applications)
        create_arguments = {
            'titre': 'Preparer ma journee',
            'priorite': 3,
            'date_echeance': '2026-09-16T10:00:00+02:00',
        }

        with (
            patch.dict(agent_service.TOOL_REGISTRY, {
                'get_today_tasks': today_tasks,
                'get_applications': applications,
            }),
            patch('api.agent_service.appeler_llm', side_effect=[
                tool_response(tool_use_id='tasks', name='get_today_tasks'),
                tool_response(tool_use_id='applications', name='get_applications'),
                tool_response(tool_use_id='create', name='create_task', arguments=create_arguments),
            ]),
        ):
            chat_response = self.client.post(
                '/api/agent/chat/',
                {'message': 'Organise ma journee.'},
                format='json',
            )

        self.assertEqual(chat_response.status_code, status.HTTP_200_OK)
        today_tasks.assert_called_once_with(self.user)
        applications.assert_called_once_with(self.user)
        conversation = ConversationAgent.objects.get(pk=chat_response.data['conversation_id'])
        self.assertEqual(
            list(conversation.messages.filter(role=MessageAgent.Role.OUTIL).values_list('tool_name', flat=True)),
            ['get_today_tasks', 'get_applications'],
        )

        action_id = chat_response.data['action_en_attente']['id']
        confirm_response = self.client.post(
            f'/api/agent/actions/{action_id}/confirmer/',
            {},
            format='json',
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(self.user.taches.values_list('titre', flat=True)), ['Preparer ma journee'])

        cancel_arguments = {
            'titre': 'Ne doit pas etre creee',
            'priorite': 1,
            'date_echeance': '2026-09-17T10:00:00+02:00',
        }
        with patch(
            'api.agent_service.appeler_llm',
            return_value=tool_response(name='create_task', arguments=cancel_arguments),
        ):
            cancel_chat_response = self.client.post(
                '/api/agent/chat/',
                {
                    'conversation_id': conversation.id,
                    'message': 'Ajoute aussi une tache facultative.',
                },
                format='json',
            )

        cancel_action_id = cancel_chat_response.data['action_en_attente']['id']
        cancel_response = self.client.post(
            f'/api/agent/actions/{cancel_action_id}/annuler/',
            {},
            format='json',
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.taches.count(), 1)
        self.assertFalse(self.user.taches.filter(titre='Ne doit pas etre creee').exists())


class AgentActionEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent-action-owner')
        self.other_user = User.objects.create_user(username='agent-action-other')
        self.conversation = ConversationAgent.objects.create(utilisateur=self.user)
        self.token = Token.objects.create(user=self.user)
        self.other_token = Token.objects.create(user=self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def create_pending_action(self, **overrides):
        arguments = {
            'titre': 'Titre stocke cote serveur',
            'priorite': 4,
            'date_echeance': '2026-09-16T10:00:00+02:00',
        }
        arguments.update(overrides.pop('arguments', {}))
        return ActionEnAttente.objects.create(
            conversation=self.conversation,
            utilisateur=self.user,
            tool_name='create_task',
            arguments=arguments,
            **overrides,
        )

    def test_confirm_uses_only_stored_arguments_even_when_request_is_forged(self):
        action = self.create_pending_action()

        response = self.client.post(
            f'/api/agent/actions/{action.id}/confirmer/',
            {
                'arguments': {
                    'titre': 'Titre falsifie',
                    'priorite': 1,
                    'date_echeance': '2030-01-01T00:00:00Z',
                },
                'titre': 'Autre titre falsifie',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task = self.user.taches.get()
        self.assertEqual(task.titre, 'Titre stocke cote serveur')
        self.assertEqual(task.priorite, 4)
        action.refresh_from_db()
        self.assertEqual(action.statut, ActionEnAttente.Statut.CONFIRMEE)
        self.assertIsNotNone(action.date_traitement)

    def test_only_the_owner_can_confirm_an_action(self):
        action = self.create_pending_action()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')

        response = self.client.post(f'/api/agent/actions/{action.id}/confirmer/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(self.user.taches.exists())
        action.refresh_from_db()
        self.assertEqual(action.statut, ActionEnAttente.Statut.EN_ATTENTE)

    def test_only_the_owner_can_cancel_an_action(self):
        action = self.create_pending_action()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')

        response = self.client.post(f'/api/agent/actions/{action.id}/annuler/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        action.refresh_from_db()
        self.assertEqual(action.statut, ActionEnAttente.Statut.EN_ATTENTE)
        self.assertIsNone(action.date_traitement)

    def test_an_action_cannot_be_confirmed_twice(self):
        action = self.create_pending_action()
        url = f'/api/agent/actions/{action.id}/confirmer/'

        first_response = self.client.post(url, {}, format='json')
        second_response = self.client.post(url, {}, format='json')

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.user.taches.count(), 1)

    def test_an_expired_action_cannot_be_confirmed(self):
        action = self.create_pending_action()
        ActionEnAttente.objects.filter(pk=action.pk).update(
            date_creation=timezone.now() - timedelta(hours=24, seconds=1),
        )

        response = self.client.post(
            f'/api/agent/actions/{action.id}/confirmer/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(self.user.taches.exists())
        action.refresh_from_db()
        self.assertEqual(action.statut, ActionEnAttente.Statut.EXPIREE)
        self.assertIsNotNone(action.date_traitement)

    def test_cancel_marks_the_action_without_executing_it(self):
        action = self.create_pending_action()

        cancel_response = self.client.post(
            f'/api/agent/actions/{action.id}/annuler/',
            {'arguments': {'titre': 'Titre falsifie'}},
            format='json',
        )
        confirm_response = self.client.post(
            f'/api/agent/actions/{action.id}/confirmer/',
            {},
            format='json',
        )

        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm_response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(self.user.taches.exists())
        action.refresh_from_db()
        self.assertEqual(action.statut, ActionEnAttente.Statut.ANNULEE)
        self.assertIsNotNone(action.date_traitement)
