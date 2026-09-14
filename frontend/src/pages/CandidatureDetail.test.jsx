import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import CandidatureDetail from './CandidatureDetail';
import { candidatureActionsAPI, candidaturesAPI } from '../services/api';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useParams: () => ({ id: '7' }),
}), { virtual: true });

jest.mock('../services/api', () => ({
  candidaturesAPI: {
    getById: jest.fn(), update: jest.fn(), patch: jest.fn(), archive: jest.fn(), delete: jest.fn(),
  },
  candidatureActionsAPI: {
    getAll: jest.fn(), create: jest.fn(), update: jest.fn(), delete: jest.fn(),
  },
}));

const candidature = {
  id: 7, utilisateur: 1, url: 'https://example.com/job', titre: 'Dev Django',
  entreprise: 'Example', lieu: 'Lyon', mode_travail: 'hybride',
  description: 'Concevoir une API metier.', type_poste: 'cdi', statut: 'postule',
  source_extraction: 'scraping', source_canal: 'linkedin', tags: ['django'],
  favori: false, archive: false, cv_utilise: 'CV_backend.pdf',
  date_limite: '2026-09-30', date_relance: '2026-09-20',
  notes: 'Equipe interessante.', date_ajout: '2026-09-14T09:00:00Z',
  date_modification: '2026-09-14T10:00:00Z',
};
const existingAction = {
  id: 3, candidature: 7, type_action: 'envoyee',
  date_action: '2026-09-14T09:30:00Z', commentaire: 'CV transmis.',
  date_creation: '2026-09-14T09:31:00Z',
};

beforeEach(() => {
  jest.resetAllMocks();
  candidaturesAPI.getById.mockResolvedValue({ data: candidature });
  candidatureActionsAPI.getAll.mockResolvedValue({ data: [existingAction] });
});

test('renders general information and adds an action to the timeline', async () => {
  const created = {
    id: 4, candidature: 7, type_action: 'relance',
    date_action: '2026-09-15T10:30:00Z', commentaire: 'Message LinkedIn envoye.',
    date_creation: '2026-09-15T10:31:00Z',
  };
  candidatureActionsAPI.create.mockResolvedValue({ data: created });
  render(<CandidatureDetail />);

  expect(await screen.findByRole('heading', { name: 'Dev Django' })).toBeInTheDocument();
  expect(screen.getByText('Lyon')).toBeInTheDocument();
  expect(screen.getByText('Hybride')).toBeInTheDocument();
  expect(screen.getByText('CV transmis.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter une action' }));
  const dialog = screen.getByRole('dialog');
  fireEvent.mouseDown(within(dialog).getByRole('combobox', { name: "Type d'action" }));
  fireEvent.click(screen.getByRole('option', { name: 'Relance' }));
  fireEvent.change(within(dialog).getByLabelText(/Date de l'action/), { target: { value: '2026-09-15T10:30' } });
  fireEvent.change(within(dialog).getByLabelText('Commentaire'), { target: { value: 'Message LinkedIn envoye.' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

  await waitFor(() => expect(candidatureActionsAPI.create).toHaveBeenCalledWith(7, {
    type_action: 'relance', date_action: '2026-09-15T10:30', commentaire: 'Message LinkedIn envoye.',
  }));
  expect(await screen.findByText('Message LinkedIn envoye.')).toBeInTheDocument();
});

test('updates status favorite and tags inline', async () => {
  candidaturesAPI.patch
    .mockImplementationOnce((id, data) => Promise.resolve({ data: { ...candidature, ...data } }))
    .mockImplementationOnce((id, data) => Promise.resolve({ data: { ...candidature, statut: 'entretien', ...data } }))
    .mockImplementationOnce((id, data) => Promise.resolve({ data: { ...candidature, statut: 'entretien', favori: true, ...data } }));
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.mouseDown(screen.getByLabelText('Statut'));
  fireEvent.click(screen.getByRole('option', { name: 'Entretien' }));
  await waitFor(() => expect(candidaturesAPI.patch).toHaveBeenCalledWith(7, { statut: 'entretien' }));
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter aux favoris' }));
  await waitFor(() => expect(candidaturesAPI.patch).toHaveBeenCalledWith(7, { favori: true }));
  fireEvent.change(screen.getByLabelText('Tags'), { target: { value: 'react' } });
  fireEvent.keyDown(screen.getByLabelText('Tags'), { key: 'Enter' });
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer les tags' }));
  await waitFor(() => expect(candidaturesAPI.patch).toHaveBeenCalledWith(7, { tags: ['django', 'react'] }));
});

test('archives and deletes from the header after confirmation', async () => {
  candidaturesAPI.archive.mockResolvedValue({ data: { ...candidature, archive: true } });
  candidaturesAPI.delete.mockResolvedValue({});
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(screen.getByRole('button', { name: 'Archiver' }));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Archiver' }));
  await waitFor(() => expect(candidaturesAPI.archive).toHaveBeenCalledWith(7));
  expect(screen.getByText('Archivee')).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

  fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Supprimer definitivement' }));
  await waitFor(() => expect(candidaturesAPI.delete).toHaveBeenCalledWith(7));
  expect(mockNavigate).toHaveBeenCalledWith('/candidatures');
});
