import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import CandidatureCard from './CandidatureCard';

test('renders job details, expired deadline and working edit/delete actions', () => {
  const candidature = { id: 1, titre: 'Dev Django', entreprise: 'Example', type_poste: 'cdi',
    statut: 'entretien', url: 'https://example.com/job', favori: true, archive: true,
    date_ajout: '2026-09-14T12:00:00Z', date_limite: '2000-01-01', tags: ['python'] };
  const onEdit = jest.fn();
  const onOpen = jest.fn();
  const onDelete = jest.fn();
  render(<CandidatureCard candidature={candidature} onOpen={onOpen} onEdit={onEdit} onDelete={onDelete} />);
  expect(screen.getByText('Example')).toBeInTheDocument();
  expect(screen.getByText('CDI')).toBeInTheDocument();
  expect(screen.getByText('Entretien')).toBeInTheDocument();
  expect(screen.getByText('Archivee')).toBeInTheDocument();
  expect(screen.getByText(/Echeance depassee/)).toBeInTheDocument();
  expect(screen.getByRole('link')).toHaveAttribute('rel', 'noopener noreferrer');
  expect(screen.getByRole('link')).toHaveAttribute('href', candidature.url);
  fireEvent.click(screen.getByRole('button', { name: 'Dev Django' }));
  expect(onOpen).toHaveBeenCalledWith(candidature);
  fireEvent.click(screen.getByRole('button', { name: 'Modifier Dev Django' }));
  expect(onEdit).toHaveBeenCalledWith(candidature);
  fireEvent.click(screen.getByRole('button', { name: 'Supprimer Dev Django' }));
  expect(onDelete).toHaveBeenCalledWith(candidature);
});

test('does not render a link for a non HTTP URL', () => {
  render(<CandidatureCard candidature={{ titre: 'Dev', url: 'javascript:alert(1)' }} onEdit={jest.fn()} onDelete={jest.fn()} />);
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
