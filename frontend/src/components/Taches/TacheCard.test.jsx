import React from 'react';
import { render, screen } from '@testing-library/react';
import TacheCard from './TacheCard';

jest.mock('date-fns', () => ({ format: () => '10 sept. 2026, 09:00' }));
jest.mock('date-fns/locale', () => ({ fr: {} }));

const task = (priorite) => ({
  id: priorite,
  titre: `Tâche ${priorite}`,
  emoji: '📝',
  couleur: '#3498db',
  priorite,
  completee: false,
  date_echeance: '2026-09-10T09:00:00Z',
});

test.each([
  [1, 'Basse'],
  [2, 'Moyenne'],
  [3, 'Haute'],
  [4, 'Urgente'],
])('renders the %s priority with its visual label', (priorite, label) => {
  render(
    <TacheCard
      tache={task(priorite)}
      onUpdate={jest.fn()}
      onDelete={jest.fn()}
      onEdit={jest.fn()}
    />
  );

  expect(screen.getByLabelText(`Priorité ${label}`)).toHaveTextContent(label);
});
