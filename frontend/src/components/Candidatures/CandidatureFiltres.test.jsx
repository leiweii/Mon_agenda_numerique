import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import CandidatureFiltres, { DEFAULT_FILTERS } from './CandidatureFiltres';

const renderFilters = (filters = DEFAULT_FILTERS) => {
  const onChange = jest.fn();
  render(<CandidatureFiltres filters={filters} onChange={onChange} tagsDisponibles={['django', 'react']} />);
  return onChange;
};

test('exposes every filter from the candidature design', () => {
  renderFilters();
  expect(screen.getByLabelText('Recherche')).toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: 'Statut' })).toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: 'Type de poste' })).toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: 'Source du canal' })).toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: 'Tags' })).toBeInTheDocument();
  expect(screen.getByLabelText('Favoris uniquement')).toBeInTheDocument();
  expect(screen.getByLabelText('Inclure les archivees')).not.toBeChecked();
  expect(screen.getByLabelText("Date d'ajout minimale")).toBeInTheDocument();
  expect(screen.getByLabelText("Date d'ajout maximale")).toBeInTheDocument();
  expect(screen.getByLabelText('Echeance sous 7 jours')).toBeInTheDocument();
  expect(screen.getByLabelText('A relancer')).toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: 'Tri' })).toBeInTheDocument();
});

test('updates multi choice and binary filters', () => {
  const onChange = renderFilters();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Statut' }));
  fireEvent.click(screen.getByRole('option', { name: 'Postule' }));
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ statut: ['postule'] }));
  fireEvent.click(screen.getByLabelText('Inclure les archivees'));
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ archive: true }));
});

test('clear button restores the defaults', () => {
  const onChange = renderFilters({ ...DEFAULT_FILTERS, search: 'django', favori: true });
  fireEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }));
  expect(onChange).toHaveBeenCalledWith(DEFAULT_FILTERS);
});
