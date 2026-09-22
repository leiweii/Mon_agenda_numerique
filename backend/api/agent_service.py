import json
import logging
import time
from dataclasses import dataclass

import anthropic
from django.conf import settings
from django.utils import timezone

from api.agent_tools import create_task, get_applications, get_today_tasks, update_task
from api.llm_service import (
    MODELE_PAR_DEFAUT,
    NOMBRE_TENTATIVES,
    TIMEOUT_SECONDES,
    _erreur_transitoire,
)
from api.models import ActionEnAttente, MessageAgent


logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 5
MAX_AGENT_TOKENS = 1024
MESSAGE_REPLI = (
    "Je n'ai pas reussi a conclure en un nombre raisonnable d'etapes. "
    "Peux-tu reformuler ta demande de facon plus precise ?"
)

TOOL_DEFINITIONS = [
    {
        'name': 'get_today_tasks',
        'description': "Retourne les taches du jour de l'utilisateur.",
        'input_schema': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': 'get_applications',
        'description': "Retourne les candidatures actives de l'utilisateur.",
        'input_schema': {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        },
    },
    {
        'name': 'create_task',
        'description': "Propose la creation d'une tache pour l'utilisateur.",
        'input_schema': {
            'type': 'object',
            'properties': {
                'titre': {'type': 'string'},
                'priorite': {'type': 'integer', 'minimum': 1, 'maximum': 4},
                'date_echeance': {'type': 'string', 'format': 'date-time'},
                'categorie_id': {'type': ['integer', 'null']},
            },
            'required': ['titre', 'priorite', 'date_echeance'],
            'additionalProperties': False,
        },
    },
    {
        'name': 'update_task',
        'description': "Propose la modification d'une tache existante.",
        'input_schema': {
            'type': 'object',
            'properties': {
                'tache_id': {'type': 'integer'},
                'titre': {'type': 'string'},
                'description': {'type': 'string'},
                'date_echeance': {'type': 'string', 'format': 'date-time'},
                'priorite': {'type': 'integer', 'minimum': 1, 'maximum': 4},
                'categorie_id': {'type': ['integer', 'null']},
                'couleur': {'type': 'string'},
                'emoji': {'type': 'string'},
                'completee': {'type': 'boolean'},
            },
            'required': ['tache_id'],
            'additionalProperties': False,
        },
    },
]

TOOL_REGISTRY = {
    'get_today_tasks': get_today_tasks,
    'get_applications': get_applications,
    'create_task': create_task,
    'update_task': update_task,
}

WRITE_TOOL_NAMES = {'create_task', 'update_task'}


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class AgentLLMResponse:
    text: str
    tool_call: ToolCall | None
    content: list


@dataclass(frozen=True)
class PendingActionProposal:
    action_id: int
    message: str


def _system_prompt(date_du_jour):
    return (
        'Tu es un assistant de planification personnelle. '
        f'La date du jour est {date_du_jour.isoformat()}. '
        "Utilise les outils de lecture lorsque les donnees de l'utilisateur "
        'sont necessaires et reponds en francais.'
    )


def _normalize_response(response):
    text_parts = []
    tool_call = None
    content = []

    for block in response.content:
        block_type = getattr(block, 'type', None)
        if block_type == 'text':
            text = getattr(block, 'text', '')
            text_parts.append(text)
            content.append({'type': 'text', 'text': text})
        elif block_type == 'tool_use':
            block_input = getattr(block, 'input', {})
            normalized_input = block_input if isinstance(block_input, dict) else {}
            normalized_block = {
                'type': 'tool_use',
                'id': block.id,
                'name': block.name,
                'input': normalized_input,
            }
            content.append(normalized_block)
            if tool_call is None:
                tool_call = ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=normalized_input,
                )

    return AgentLLMResponse(
        text=''.join(text_parts).strip(),
        tool_call=tool_call,
        content=content,
    )


def appeler_llm(*, messages, tools, date_du_jour):
    if not settings.LLM_API_KEY:
        logger.warning('Appel agent LLM ignore: cle API absente')
        return None

    client = anthropic.Anthropic(
        api_key=settings.LLM_API_KEY,
        timeout=TIMEOUT_SECONDES,
        max_retries=0,
    )
    for tentative in range(1, NOMBRE_TENTATIVES + 1):
        try:
            response = client.messages.create(
                model=MODELE_PAR_DEFAUT,
                max_tokens=MAX_AGENT_TOKENS,
                system=_system_prompt(date_du_jour),
                messages=messages,
                tools=tools,
                tool_choice={'type': 'auto', 'disable_parallel_tool_use': True},
            )
            return _normalize_response(response)
        except Exception as error:
            transient = _erreur_transitoire(error)
            logger.warning(
                'Appel agent LLM echoue tentative=%s transitoire=%s',
                tentative,
                transient,
            )
            if not transient or tentative == NOMBRE_TENTATIVES:
                return None
            time.sleep(0.2)

    return None


def _load_history(conversation):
    role_mapping = {
        MessageAgent.Role.UTILISATEUR: 'user',
        MessageAgent.Role.AGENT: 'assistant',
    }
    history = []
    for message in conversation.messages.order_by('date_creation', 'id'):
        role = role_mapping.get(message.role)
        if role:
            history.append({'role': role, 'content': message.contenu})
        elif message.role == MessageAgent.Role.OUTIL:
            history.append({
                'role': 'user',
                'content': f'Resultat de l\'outil {message.tool_name}: {message.contenu}',
            })
    return history


def _save_fallback(conversation):
    MessageAgent.objects.create(
        conversation=conversation,
        role=MessageAgent.Role.AGENT,
        contenu=MESSAGE_REPLI,
    )
    return MESSAGE_REPLI


def formater_proposition(tool_name, arguments):
    if tool_name == 'create_task':
        title = str(arguments.get('titre') or 'sans titre')[:200]
        return f'Je propose de creer la tache « {title} ». Confirme cette action pour l\'executer.'
    task_id = arguments.get('tache_id', '?')
    return f'Je propose de modifier la tache n°{task_id}. Confirme cette action pour l\'executer.'


def _create_pending_action(conversation, user, tool_call):
    action = ActionEnAttente.objects.create(
        conversation=conversation,
        utilisateur=user,
        tool_name=tool_call.name,
        arguments=tool_call.arguments,
    )
    proposal_message = formater_proposition(tool_call.name, tool_call.arguments)
    MessageAgent.objects.create(
        conversation=conversation,
        role=MessageAgent.Role.AGENT,
        contenu=proposal_message,
    )
    return PendingActionProposal(action_id=action.id, message=proposal_message)


def executer_agent(conversation, message_utilisateur, user):
    messages = _load_history(conversation)
    messages.append({'role': 'user', 'content': message_utilisateur})
    MessageAgent.objects.create(
        conversation=conversation,
        role=MessageAgent.Role.UTILISATEUR,
        contenu=message_utilisateur,
    )
    conversation.save(update_fields=['date_derniere_activite'])
    current_date = timezone.localdate()

    for _ in range(MAX_AGENT_STEPS):
        response = appeler_llm(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            date_du_jour=current_date,
        )
        if response is None:
            return _save_fallback(conversation)

        if response.tool_call is None:
            MessageAgent.objects.create(
                conversation=conversation,
                role=MessageAgent.Role.AGENT,
                contenu=response.text,
            )
            return response.text

        if response.tool_call.name in WRITE_TOOL_NAMES:
            return _create_pending_action(conversation, user, response.tool_call)

        tool_function = TOOL_REGISTRY[response.tool_call.name]
        tool_result = tool_function(user)
        serialized_result = json.dumps(tool_result, ensure_ascii=False, default=str)
        MessageAgent.objects.create(
            conversation=conversation,
            role=MessageAgent.Role.OUTIL,
            contenu=serialized_result,
            tool_name=response.tool_call.name,
        )
        messages.append({'role': 'assistant', 'content': response.content})
        messages.append({
            'role': 'user',
            'content': [{
                'type': 'tool_result',
                'tool_use_id': response.tool_call.id,
                'content': serialized_result,
            }],
        })

    return _save_fallback(conversation)
