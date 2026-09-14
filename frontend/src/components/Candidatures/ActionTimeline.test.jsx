import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
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

