import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import ActionTimeline from './ActionTimeline';

test('renders actions newest first and exposes timeline commands', () => {
  const older = { id: 1, type_action: 'envoyee', date_action: '2026-09-12T08:00:00Z', commentaire: 'CV transmis.' };
  const newer = { id: 2, type_action: 'entretien_visio', date_action: '2026-09-14T10:00:00Z', commentaire: 'Entretien produit.' };
  const onAdd = jest.fn();
  const onEdit = jest.fn();
  const onDelete = jest.fn();

  render(<ActionTimeline actions={[older, newer]} onAdd={onAdd} onEdit={onEdit} onDelete={onDelete} />);

  const comments = screen.getAllByText(/CV transmis|Entretien produit/);
  expect(comments.map(node => node.textContent)).toEqual(['Entretien produit.', 'CV transmis.']);
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter une action' }));
  fireEvent.click(screen.getByRole('button', { name: 'Modifier Entretien visio' }));
  fireEvent.click(screen.getByRole('button', { name: 'Supprimer Entretien visio' }));
  expect(onAdd).toHaveBeenCalledTimes(1);
  expect(onEdit).toHaveBeenCalledWith(newer);
  expect(onDelete).toHaveBeenCalledWith(newer);
});

test('interleaves initial and follow-up emails with actions without edit commands on email events', () => {
  const action = { id: 3, type_action: 'envoyee', date_action: '2026-09-14T09:40:00Z', commentaire: 'Email #1 envoye via Gmail.' };
  const initial = {
    id: 1, recipient_email: 'initial@example.com', subject: 'Candidature initiale',
    status: 'sent', created_at: '2026-09-14T09:00:00Z', updated_at: '2026-09-14T09:40:00Z',
    sent_at: '2026-09-14T09:40:00Z',
  };
  const followUp = {
    id: 2, recipient_email: 'relance@example.com', subject: 'Relance 1',
    status: 'draft', created_at: '2026-09-15T10:00:00Z', updated_at: '2026-09-15T11:00:00Z',
    sent_at: null,
  };

  render(<ActionTimeline actions={[action]} emails={[initial, followUp]} onAdd={jest.fn()} onEdit={jest.fn()} onDelete={jest.fn()} />);

  const history = screen.getByRole('region', { name: 'Historique des actions et emails' });
  expect(within(history).getAllByRole('heading', { level: 3 }).map(node => node.textContent)).toEqual([
    'Email mis à jour — Relance 1',
    'Email préparé — Relance 1',
    'Candidature envoyee',
    'Email préparé — Candidature initiale',
  ]);
  expect(within(history).getAllByText('relance@example.com')).toHaveLength(2);
  expect(within(history).getByText('initial@example.com')).toBeInTheDocument();
  expect(within(history).getAllByRole('button', { name: /Modifier/ })).toHaveLength(1);
  expect(within(history).getAllByRole('button', { name: /Supprimer/ })).toHaveLength(1);
});

