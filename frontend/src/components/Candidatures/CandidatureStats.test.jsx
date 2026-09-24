import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import CandidatureStats, { countCandidatureStats } from './CandidatureStats';

test('counts only the displayed candidatures with the existing relance and seven-day rules', () => {
  const candidatures = [
    { statut: 'postule', date_relance: '2026-09-24', date_limite: '2026-09-24' },
    { statut: 'entretien', date_relance: '2026-09-25', date_limite: '2026-10-01' },
    { statut: 'refuse', date_relance: '2026-09-20', date_limite: '2026-10-02' },
    { statut: 'accepte', date_relance: null, date_limite: '2026-09-23' },
  ];

  expect(countCandidatureStats(candidatures, '2026-09-24')).toEqual({
    enCours: 2,
    aRelancer: 2,
    echeance: 2,
  });
});

test('renders the three counters and opens the existing relance filter', () => {
  const onRelance = jest.fn();
  render(<CandidatureStats candidatures={[{ statut: 'postule', date_relance: '2026-09-20' }]}
    today="2026-09-24" onRelance={onRelance} />);

  expect(screen.getByText('En cours')).toBeInTheDocument();
  expect(screen.getByText('À relancer')).toBeInTheDocument();
  expect(screen.getByText('Échéance sous 7 jours')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /À relancer/ }));
  expect(onRelance).toHaveBeenCalledTimes(1);
});
