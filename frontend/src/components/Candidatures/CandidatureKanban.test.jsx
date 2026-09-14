import React from 'react';
import { act, render, screen } from '@testing-library/react';
import CandidatureKanban from './CandidatureKanban';

let onDragEnd;

jest.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children, onDragEnd: handler }) => {
    onDragEnd = handler;
    return children;
  },
  Droppable: ({ children, droppableId }) => children({
    innerRef: jest.fn(),
    droppableProps: { 'data-testid': `colonne-${droppableId}` },
    placeholder: null,
  }, { isDraggingOver: false }),
  Draggable: ({ children, draggableId }) => children({
    innerRef: jest.fn(),
    draggableProps: { 'data-testid': `carte-${draggableId}` },
    dragHandleProps: {},
  }, { isDragging: false }),
}));

const candidature = {
  id: 12,
  titre: 'Developpeuse Django',
  entreprise: 'Example',
  statut: 'postule',
  type_poste: 'cdi',
  favori: true,
};

test('affiche une colonne par statut et les candidatures fournies', () => {
  render(<CandidatureKanban candidatures={[candidature]} onStatusChange={jest.fn()} onOpen={jest.fn()} />);

  expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(5);
  expect(screen.getByRole('heading', { name: 'A postuler (0)' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Postule (1)' })).toBeInTheDocument();
  expect(screen.getByText('Developpeuse Django')).toBeInTheDocument();
  expect(screen.getByText('Example')).toBeInTheDocument();
  expect(screen.getByText('CDI')).toBeInTheDocument();
  expect(screen.getByLabelText('Candidature favorite')).toBeInTheDocument();
});

test('demande le changement de statut apres un depot dans une autre colonne', () => {
  const handleStatusChange = jest.fn();
  render(<CandidatureKanban candidatures={[candidature]} onStatusChange={handleStatusChange} onOpen={jest.fn()} />);

  act(() => onDragEnd({
    draggableId: '12',
    source: { droppableId: 'postule', index: 0 },
    destination: { droppableId: 'entretien', index: 0 },
  }));

  expect(handleStatusChange).toHaveBeenCalledWith(candidature, 'entretien');
});

test('ignore un depot annule ou dans la colonne d origine', () => {
  const handleStatusChange = jest.fn();
  render(<CandidatureKanban candidatures={[candidature]} onStatusChange={handleStatusChange} onOpen={jest.fn()} />);

  act(() => onDragEnd({ draggableId: '12', source: { droppableId: 'postule', index: 0 }, destination: null }));
  act(() => onDragEnd({
    draggableId: '12',
    source: { droppableId: 'postule', index: 0 },
    destination: { droppableId: 'postule', index: 0 },
  }));

  expect(handleStatusChange).not.toHaveBeenCalled();
});
