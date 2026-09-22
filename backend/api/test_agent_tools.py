import importlib.util
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from api import models as api_models
from api import agent_tools
from api.models import ActionCandidature, Candidature
from agenda.models import Categorie, Tache


class AgentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent-owner')

    def test_conversation_belongs_to_its_user(self):
        conversation_model = getattr(api_models, 'ConversationAgent', None)
        self.assertIsNotNone(conversation_model)

        conversation = conversation_model.objects.create(utilisateur=self.user)

        self.assertEqual(list(self.user.conversations_agent.all()), [conversation])

    def test_message_records_its_role_and_optional_tool_name(self):
        conversation_model = getattr(api_models, 'ConversationAgent', None)
        message_model = getattr(api_models, 'MessageAgent', None)
        self.assertIsNotNone(conversation_model)
        self.assertIsNotNone(message_model)
        conversation = conversation_model.objects.create(utilisateur=self.user)

        message = message_model.objects.create(
            conversation=conversation,
            role=message_model.Role.OUTIL,
            contenu='2 taches trouvees',
            tool_name='get_today_tasks',
        )

        self.assertEqual(list(conversation.messages.all()), [message])
        self.assertEqual(message.role, 'outil')
        self.assertEqual(message.tool_name, 'get_today_tasks')

    def test_pending_action_stores_exact_arguments_and_defaults_to_pending(self):
        conversation_model = getattr(api_models, 'ConversationAgent', None)
        action_model = getattr(api_models, 'ActionEnAttente', None)
        self.assertIsNotNone(conversation_model)
        self.assertIsNotNone(action_model)
        conversation = conversation_model.objects.create(utilisateur=self.user)
        arguments = {'titre': 'Preparer entretien', 'priorite': 4}

        action = action_model.objects.create(
            conversation=conversation,
            utilisateur=self.user,
            tool_name='create_task',
            arguments=arguments,
        )

        self.assertEqual(action.arguments, arguments)
        self.assertEqual(action.statut, 'en_attente')
        self.assertIsNone(action.date_traitement)
        self.assertEqual(list(conversation.actions_en_attente.all()), [action])
        self.assertEqual(list(self.user.actions_agent_en_attente.all()), [action])


class AgentReadToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tools-owner')
        self.other_user = User.objects.create_user(username='tools-other')

    def test_get_today_tasks_returns_only_the_users_tasks_due_today(self):
        today = timezone.localdate()
        due_today = timezone.make_aware(datetime.combine(today, time(9, 30)))
        due_tomorrow = timezone.make_aware(datetime.combine(today + timedelta(days=1), time(9, 30)))
        category = Categorie.objects.create(
            utilisateur=self.user,
            nom='Recherche emploi',
            couleur='#123456',
            emoji='💼',
        )
        own_task = Tache.objects.create(
            utilisateur=self.user,
            titre='Preparer entretien',
            description='Relire les notes Django',
            date_echeance=due_today,
            priorite=4,
            completee=False,
            categorie=category,
        )
        Tache.objects.create(
            utilisateur=self.user,
            titre='Tache de demain',
            date_echeance=due_tomorrow,
        )
        Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tache privee autre utilisateur',
            date_echeance=due_today,
        )
        self.assertIsNotNone(importlib.util.find_spec('api.agent_tools'))
        from api.agent_tools import get_today_tasks

        result = get_today_tasks(self.user)

        self.assertEqual(result, {
            'succes': True,
            'taches': [{
                'id': own_task.id,
                'titre': 'Preparer entretien',
                'description': 'Relire les notes Django',
                'date_echeance': timezone.localtime(due_today).isoformat(),
                'priorite': 4,
                'completee': False,
                'categorie_id': category.id,
                'categorie_nom': 'Recherche emploi',
            }],
        })

    def test_get_applications_returns_only_active_applications_with_latest_action(self):
        own_application = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/jobs/owner',
            titre='Developpeuse Django',
            entreprise='Example',
            description='Construire une API REST.',
            type_poste=Candidature.TypePoste.ALTERNANCE,
            statut=Candidature.Statut.POSTULE,
            source_canal=Candidature.SourceCanal.LINKEDIN,
            tags=['django', 'react'],
            favori=True,
            date_limite='2026-09-30',
            date_relance='2026-09-20',
        )
        latest_action_at = timezone.make_aware(datetime(2026, 9, 15, 14, 0))
        ActionCandidature.objects.create(
            candidature=own_application,
            type_action=ActionCandidature.TypeAction.CANDIDATURE_ENVOYEE,
            date_action=latest_action_at - timedelta(days=1),
        )
        ActionCandidature.objects.create(
            candidature=own_application,
            type_action=ActionCandidature.TypeAction.RELANCE,
            date_action=latest_action_at,
        )
        Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/jobs/archived',
            titre='Candidature archivee',
            archive=True,
        )
        Candidature.objects.create(
            utilisateur=self.other_user,
            url='https://example.com/jobs/other',
            titre='Candidature privee autre utilisateur',
        )
        self.assertIsNotNone(importlib.util.find_spec('api.agent_tools'))
        from api.agent_tools import get_applications

        result = get_applications(self.user)

        self.assertEqual(result, {
            'succes': True,
            'candidatures': [{
                'id': own_application.id,
                'titre': 'Developpeuse Django',
                'entreprise': 'Example',
                'description': 'Construire une API REST.',
                'type_poste': 'alternance',
                'statut': 'postule',
                'source_canal': 'linkedin',
                'tags': ['django', 'react'],
                'favori': True,
                'date_limite': '2026-09-30',
                'date_relance': '2026-09-20',
                'date_derniere_action': timezone.localtime(latest_action_at).isoformat(),
            }],
        })


class AgentWriteToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='write-tools-owner')
        self.other_user = User.objects.create_user(username='write-tools-other')

    def test_create_task_creates_a_task_owned_by_the_user(self):
        create_task = getattr(agent_tools, 'create_task', None)
        self.assertTrue(callable(create_task))
        category = Categorie.objects.create(
            utilisateur=self.user,
            nom='Travail',
        )

        result = create_task(
            self.user,
            titre='Preparer le dossier',
            priorite=3,
            date_echeance='2026-09-16T10:00:00+02:00',
            categorie_id=category.id,
        )

        task = Tache.objects.get()
        self.assertTrue(result['succes'])
        self.assertEqual(result['tache']['id'], task.id)
        self.assertEqual(task.utilisateur, self.user)
        self.assertEqual(task.titre, 'Preparer le dossier')
        self.assertEqual(task.priorite, 3)
        self.assertEqual(task.categorie, category)

    def test_create_task_rejects_a_category_owned_by_another_user(self):
        create_task = getattr(agent_tools, 'create_task', None)
        self.assertTrue(callable(create_task))
        other_category = Categorie.objects.create(
            utilisateur=self.other_user,
            nom='Privee',
        )

        result = create_task(
            self.user,
            titre='Ne doit pas etre creee',
            priorite=2,
            date_echeance='2026-09-16T10:00:00+02:00',
            categorie_id=other_category.id,
        )

        self.assertEqual(result, {'succes': False, 'erreur': 'Categorie introuvable.'})
        self.assertFalse(Tache.objects.exists())

    def test_update_task_changes_an_owned_task(self):
        update_task = getattr(agent_tools, 'update_task', None)
        self.assertTrue(callable(update_task))
        task = Tache.objects.create(
            utilisateur=self.user,
            titre='Ancien titre',
            date_echeance=timezone.now(),
        )

        result = update_task(
            self.user,
            tache_id=task.id,
            titre='Nouveau titre',
            completee=True,
        )

        task.refresh_from_db()
        self.assertTrue(result['succes'])
        self.assertEqual(task.titre, 'Nouveau titre')
        self.assertTrue(task.completee)

    def test_update_task_cannot_modify_another_users_task(self):
        update_task = getattr(agent_tools, 'update_task', None)
        self.assertTrue(callable(update_task))
        other_task = Tache.objects.create(
            utilisateur=self.other_user,
            titre='Tache privee',
            date_echeance=timezone.now(),
        )

        result = update_task(
            self.user,
            tache_id=other_task.id,
            titre='Titre falsifie',
        )

        other_task.refresh_from_db()
        self.assertEqual(result, {'succes': False, 'erreur': 'Tache introuvable.'})
        self.assertEqual(other_task.titre, 'Tache privee')
