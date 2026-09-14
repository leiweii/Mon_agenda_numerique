import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import CandidatureForm from './CandidatureForm';

const candidature = {
  id: 12, utilisateur: 7, url: 'https://example.com/job', titre: 'Dev Django',
  entreprise: 'Example', description: 'Une offre de developpement.',
  lieu: 'Lyon', mode_travail: 'hybride',
  type_poste: 'cdi', statut: 'entretien', source_canal: 'linkedin',
  source_extraction: 'llm', tags: ['django'], favori: true, archive: true,
  cv_utilise: 'CV_v3.pdf', date_limite: '2026-10-20', date_relance: '2026-10-10',
  notes: 'Entretien technique', date_ajout: '2026-09-14T10:00:00Z',
  date_modification: '2026-09-14T11:00:00Z',
};

test('prefills and submits every writable field without automatic metadata', async () => {
  const onSubmit = jest.fn().mockResolvedValue();
  render(<CandidatureForm open candidature={candidature} onSubmit={onSubmit} onClose={jest.fn()} />);
  expect(screen.getByLabelText('CV utilise')).toHaveValue('CV_v3.pdf');
  expect(screen.getByLabelText('Lieu')).toHaveValue('Lyon');
  expect(screen.getByLabelText('Mode de travail')).toHaveTextContent('Hybride');
  expect(screen.getByLabelText('Favori')).toBeChecked();
  expect(screen.getByLabelText('Archivee')).toBeChecked();
  expect(screen.getByLabelText('Date de relance')).toHaveValue('2026-10-10');
  expect(screen.getByLabelText('Source extraction')).toHaveAttribute('readonly');
  fireEvent.change(screen.getByLabelText(/Titre/), { target: { value: 'Dev Python' } });
  fireEvent.change(screen.getByLabelText('Tags'), { target: { value: 'react' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
  const { id, utilisateur, date_ajout, date_modification, ...payload } = candidature;
  await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ ...payload, titre: 'Dev Python', tags: ['django', 'react'] }));
});

test('manual creation sends defaults and null dates', async () => {
  const onSubmit = jest.fn().mockResolvedValue();
  render(<CandidatureForm open onSubmit={onSubmit} onClose={jest.fn()} />);
  fireEvent.change(screen.getByLabelText(/Titre/), { target: { value: 'Dev React' } });
  fireEvent.change(screen.getByLabelText(/URL de l'offre/), { target: { value: 'https://example.com/job' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
  await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ date_limite: null, date_relance: null, tags: [], archive: false, favori: false, type_poste: 'autre', statut: 'a_postuler', source_canal: 'autre', lieu: '', mode_travail: '' })));
});

test('retains entered values on API error and displays field errors', async () => {
  const onClose = jest.fn();
  const onSubmit = jest.fn().mockRejectedValue({ response: { data: { url: ['Cette URL existe deja.'] } } });
  render(<CandidatureForm open candidature={candidature} onSubmit={onSubmit} onClose={onClose} />);
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
  expect(await screen.findByText('Cette URL existe deja.')).toBeInTheDocument();
  expect(screen.getByLabelText(/Titre/)).toHaveValue('Dev Django');
  expect(onClose).not.toHaveBeenCalled();
});

test('prevents repeat submission and closing during save', async () => {
  let resolve;
  const onSubmit = jest.fn(() => new Promise(done => { resolve = done; }));
  const onClose = jest.fn();
  render(<CandidatureForm open candidature={candidature} onSubmit={onSubmit} onClose={onClose} />);
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
  expect(screen.getByRole('button', { name: 'Enregistrement...' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Annuler' })).toBeDisabled();
  resolve();
  await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  expect(onSubmit).toHaveBeenCalledTimes(1);
});
