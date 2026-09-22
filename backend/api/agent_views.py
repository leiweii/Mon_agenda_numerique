from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.agent_retention import expirer_action_si_necessaire, purger_actions_si_necessaire
from api.agent_service import (
    PendingActionProposal,
    TOOL_REGISTRY,
    WRITE_TOOL_NAMES,
    executer_agent,
    formater_proposition,
)
from api.models import ActionEnAttente, ConversationAgent


class AgentChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        purger_actions_si_necessaire()
        message = request.data.get('message')
        if not isinstance(message, str) or not message.strip():
            return Response(
                {'erreur': 'Le message est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation_id = request.data.get('conversation_id')
        if conversation_id is None:
            conversation = ConversationAgent.objects.create(utilisateur=request.user)
        else:
            conversation = get_object_or_404(
                ConversationAgent,
                pk=conversation_id,
                utilisateur=request.user,
            )

        result = executer_agent(conversation, message.strip(), request.user)
        response_data = {
            'conversation_id': conversation.id,
            'message': result.message if isinstance(result, PendingActionProposal) else result,
        }
        if isinstance(result, PendingActionProposal):
            response_data['action_en_attente'] = {
                'id': result.action_id,
                'description': result.message,
            }
        return Response(response_data)


class AgentConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        purger_actions_si_necessaire()
        conversation = get_object_or_404(
            ConversationAgent,
            pk=conversation_id,
            utilisateur=request.user,
        )
        messages = [
            {
                'id': message.id,
                'role': message.role,
                'contenu': message.contenu,
                'tool_name': message.tool_name,
                'date_creation': message.date_creation,
            }
            for message in conversation.messages.order_by('date_creation', 'id')
        ]
        pending_actions = [
            {
                'id': action.id,
                'description': formater_proposition(action.tool_name, action.arguments),
                'statut': action.statut,
            }
            for action in conversation.actions_en_attente.filter(
                utilisateur=request.user,
                statut=ActionEnAttente.Statut.EN_ATTENTE,
            ).order_by('date_creation', 'id')
        ]
        return Response({
            'conversation_id': conversation.id,
            'messages': messages,
            'actions_en_attente': pending_actions,
        })


def _locked_owned_action(user, action_id):
    return get_object_or_404(
        ActionEnAttente.objects.select_for_update(),
        pk=action_id,
        utilisateur=user,
        conversation__utilisateur=user,
    )


def _already_processed_response():
    return Response(
        {'erreur': 'Cette action a deja ete traitee.'},
        status=status.HTTP_409_CONFLICT,
    )


class AgentActionConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        purger_actions_si_necessaire()
        with transaction.atomic():
            action = _locked_owned_action(request.user, action_id)
            if expirer_action_si_necessaire(action):
                return _already_processed_response()
            if action.statut != ActionEnAttente.Statut.EN_ATTENTE:
                return _already_processed_response()
            if action.tool_name not in WRITE_TOOL_NAMES:
                return Response(
                    {'erreur': "L'action demandee n'est pas executable."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = TOOL_REGISTRY[action.tool_name](request.user, **action.arguments)
            action.statut = ActionEnAttente.Statut.CONFIRMEE
            action.date_traitement = timezone.now()
            action.save(update_fields=['statut', 'date_traitement'])

        return Response({
            'action_id': action.id,
            'statut': action.statut,
            'resultat': result,
        })


class AgentActionCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        purger_actions_si_necessaire()
        with transaction.atomic():
            action = _locked_owned_action(request.user, action_id)
            if expirer_action_si_necessaire(action):
                return _already_processed_response()
            if action.statut != ActionEnAttente.Statut.EN_ATTENTE:
                return _already_processed_response()

            action.statut = ActionEnAttente.Statut.ANNULEE
            action.date_traitement = timezone.now()
            action.save(update_fields=['statut', 'date_traitement'])

        return Response({
            'action_id': action.id,
            'statut': action.statut,
        })
