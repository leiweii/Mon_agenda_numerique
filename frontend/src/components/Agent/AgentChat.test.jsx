import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import AgentChat from './AgentChat';
import { agentAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
  agentAPI: {
    getConversation: jest.fn(),
    sendMessage: jest.fn(),
    confirmAction: jest.fn(),
    cancelAction: jest.fn(),
  },
}));

beforeEach(() => {
  jest.resetAllMocks();
  localStorage.clear();
});

test('reloads the recent conversation and shows readable messages without raw tool JSON', async () => {
  localStorage.setItem('agentConversationId', '12');
  agentAPI.getConversation.mockResolvedValue({ data: {
    conversation_id: 12,
    messages: [
      { id: 1, role: 'utilisateur', contenu: 'Que dois-je faire ?' },
      { id: 2, role: 'outil', contenu: '{"taches":[{"id":99}]}', tool_name: 'get_today_tasks' },
      { id: 3, role: 'agent', contenu: 'Commence par préparer ton entretien.' },
    ],
    actions_en_attente: [],
  } });

  render(<AgentChat />);

  expect(await screen.findByText('Que dois-je faire ?')).toBeInTheDocument();
  expect(screen.getByText('Tâches du jour consultées.')).toBeInTheDocument();
  expect(screen.getByText('Commence par préparer ton entretien.')).toBeInTheDocument();
  expect(screen.queryByText(/"taches"/)).not.toBeInTheDocument();
  expect(agentAPI.getConversation).toHaveBeenCalledWith(12);
});

test('sends a message, displays the answer and disables input while generating', async () => {
  let resolveRequest;
  agentAPI.sendMessage.mockReturnValue(new Promise(resolve => { resolveRequest = resolve; }));
  render(<AgentChat />);

  const input = screen.getByLabelText('Votre message');
  fireEvent.change(input, { target: { value: 'Planifie ma journée.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }));

  expect(input).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Génération en cours' })).toBeDisabled();
  expect(agentAPI.sendMessage).toHaveBeenCalledWith({ message: 'Planifie ma journée.' });

  await act(async () => resolveRequest({ data: {
    conversation_id: 7,
    message: 'Voici ton programme.',
  } }));

  expect(await screen.findByText('Voici ton programme.')).toBeInTheDocument();
  expect(input).toBeEnabled();
  expect(localStorage.getItem('agentConversationId')).toBe('7');
});

test('confirms a proposed action by id only', async () => {
  agentAPI.sendMessage.mockResolvedValue({ data: {
    conversation_id: 7,
    message: 'Je propose de créer la tâche « Préparer entretien ».',
    action_en_attente: {
      id: 31,
      description: 'Créer la tâche « Préparer entretien ».',
    },
  } });
  agentAPI.confirmAction.mockResolvedValue({ data: { action_id: 31, statut: 'confirmee' } });
  render(<AgentChat />);

  fireEvent.change(screen.getByLabelText('Votre message'), { target: { value: 'Crée une tâche.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmer' }));

  await waitFor(() => expect(agentAPI.confirmAction).toHaveBeenCalledWith(31));
  expect(agentAPI.confirmAction).toHaveBeenCalledTimes(1);
  expect(await screen.findByText('Action confirmée.')).toBeInTheDocument();
});

test('cancels a reloaded pending action by id only', async () => {
  localStorage.setItem('agentConversationId', '12');
  agentAPI.getConversation.mockResolvedValue({ data: {
    conversation_id: 12,
    messages: [],
    actions_en_attente: [{ id: 44, description: 'Modifier la tâche n°8.', statut: 'en_attente' }],
  } });
  agentAPI.cancelAction.mockResolvedValue({ data: { action_id: 44, statut: 'annulee' } });
  render(<AgentChat />);

  fireEvent.click(await screen.findByRole('button', { name: 'Annuler' }));

  await waitFor(() => expect(agentAPI.cancelAction).toHaveBeenCalledWith(44));
  expect(agentAPI.cancelAction).toHaveBeenCalledTimes(1);
  expect(await screen.findByText('Action annulée.')).toBeInTheDocument();
});
