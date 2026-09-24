import React from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import Candidatures from './Candidatures';
import { candidaturesAPI } from '../services/api';

jest.setTimeout(20000);

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  useSearchParams: () => {
    const React = require('react');
    const [params, setParams] = React.useState(() => new URLSearchParams(global.__candidatureSearch || ''));
    const update = next => {
      const value = next instanceof URLSearchParams ? next : new URLSearchParams(next);
      globalThis.window.history.replaceState({}, '', `/candidatures${value.toString() ? `?${value}` : ''}`);
      setParams(new URLSearchParams(value));
    };
    return [params, update];
  },
}), { virtual: true });

jest.mock('../services/api', () => ({ candidaturesAPI: {
  getAll: jest.fn(), getById: jest.fn(), importUrl: jest.fn(),
  create: jest.fn(), update: jest.fn(), patch: jest.fn(), delete: jest.fn(), exportCsv: jest.fn(),
  prepareEmails: jest.fn(),
} }));

jest.mock('../components/Candidatures/CandidatureKanban', () => ({ candidatures, onStatusChange }) => (
  <section aria-label="Kanban des candidatures">
    {candidatures.map(item => <span key={item.id}>{item.titre} - {item.statut}</span>)}
    <button type="button" onClick={() => onStatusChange(candidatures[0], 'entretien')}>Deplacer vers entretien</button>
  </section>
));

const offre = { url: 'https://example.com/job', titre: 'Dev Django', entreprise: 'Example', statut: 'a_postuler', type_poste: 'cdi', source_extraction: 'scraping' };
beforeEach(() => {
  jest.resetAllMocks();
  candidaturesAPI.getAll.mockResolvedValue({ data: [] });
});

const renderPage = (initialEntry = '/candidatures') => {
  global.__candidatureSearch = initialEntry.split('?')[1] || '';
  window.history.replaceState({}, '', initialEntry);
  return render(<Candidatures />);
};

async function analyser() {
  await screen.findByText('Aucune candidature');
  fireEvent.change(screen.getByLabelText(/Lien de l'offre/), { target: { value: offre.url } });
  fireEvent.click(screen.getByRole('button', { name: 'Analyser' }));
}

test('analysis loading, preview, correction and successful creation', async () => {
  let resolve;
  candidaturesAPI.importUrl.mockReturnValue(new Promise(done => { resolve = done; }));
  candidaturesAPI.create.mockImplementation(data => Promise.resolve({ data: { ...data, id: 1 } }));
  candidaturesAPI.getAll
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [{ ...offre, id: 1, titre: 'Dev Python' }] });
  renderPage();
  await analyser();
  expect(screen.getByRole('button', { name: 'Analyse...' })).toBeDisabled();
  await act(async () => resolve({ data: offre }));
  expect(screen.getByLabelText(/Titre/)).toHaveValue('Dev Django');
  expect(candidaturesAPI.create).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText(/Titre/), { target: { value: 'Dev Python' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument(), { timeout: 5000 });
  expect(screen.getByRole('heading', { name: 'Dev Python' })).toBeInTheDocument();
  expect(candidaturesAPI.create).toHaveBeenCalledWith(expect.objectContaining({ titre: 'Dev Python' }));
});

test('empty extraction opens a manual form with the original URL', async () => {
  candidaturesAPI.importUrl.mockResolvedValue({ data: { url: offre.url, titre: '', source_extraction: '' } });
  renderPage();
  await analyser();
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
  expect(screen.getByLabelText(/Titre/)).toHaveValue('');
  expect(screen.getByLabelText(/URL de l'offre/)).toHaveValue(offre.url);
  expect(candidaturesAPI.create).not.toHaveBeenCalled();
});

test('analysis error is visible and permits retry', async () => {
  candidaturesAPI.importUrl.mockRejectedValueOnce({ response: { data: { detail: 'Service indisponible.' } } }).mockResolvedValueOnce({ data: offre });
  renderPage();
  await analyser();
  expect(await screen.findByText('Service indisponible.')).toBeInTheDocument();
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Analyser' }));
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
});

test('duplicate opens existing candidature for update instead of creating', async () => {
  candidaturesAPI.importUrl.mockResolvedValue({ data: { duplicate: true, candidature_id: 4 } });
  candidaturesAPI.getById.mockResolvedValue({ data: { ...offre, id: 4, notes: 'Deja envoyee' } });
  candidaturesAPI.update.mockResolvedValue({ data: { ...offre, id: 4 } });
  renderPage();
  await analyser();
  expect(await screen.findByDisplayValue('Deja envoyee')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));
  await waitFor(() => expect(candidaturesAPI.update).toHaveBeenCalledWith(4, expect.any(Object)));
  expect(candidaturesAPI.create).not.toHaveBeenCalled();
});

test('manual creation and list loading failure can be recovered', async () => {
  candidaturesAPI.getAll.mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce({ data: [] });
  renderPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Reessayer' }));
  await screen.findByText('Aucune candidature');
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter manuellement' }));
  expect(screen.getByLabelText(/Titre/)).toHaveValue('');
  expect(candidaturesAPI.importUrl).not.toHaveBeenCalled();
});

test('lists statuses and only deletes after confirmation', async () => {
  candidaturesAPI.getAll.mockResolvedValue({ data: [{ ...offre, id: 4, statut: 'entretien' }] });
  candidaturesAPI.delete.mockResolvedValue({});
  renderPage();
  expect(await screen.findByRole('heading', { name: 'Dev Django' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Entretien (1)' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Supprimer Dev Django' }));
  expect(candidaturesAPI.delete).not.toHaveBeenCalled();
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Supprimer' }));
  await screen.findByText('Aucune candidature');
  expect(candidaturesAPI.delete).toHaveBeenCalledWith(4);
});

test('analysis prevents a competing edit or deletion until the preview is ready', async () => {
  candidaturesAPI.getAll.mockResolvedValue({ data: [{ ...offre, id: 1 }] });
  let resolve;
  candidaturesAPI.importUrl.mockReturnValue(new Promise(done => { resolve = done; }));
  renderPage();
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.change(screen.getByLabelText(/Lien de l'offre/), { target: { value: offre.url } });
  fireEvent.click(screen.getByRole('button', { name: 'Analyser' }));
  expect(screen.getByRole('button', { name: 'Dev Django', exact: true })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Modifier Dev Django' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Supprimer Dev Django' })).toBeDisabled();
  await act(async () => resolve({ data: offre }));
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
});

test('reads active filters from the URL and sends repeated query parameters', async () => {
  renderPage('/candidatures?statut=postule&statut=entretien&tags=django&archive=true&ordering=date_limite');
  await screen.findByText('Aucune candidature');
  const params = candidaturesAPI.getAll.mock.calls[0][0];
  expect(params.getAll('statut')).toEqual(['postule', 'entretien']);
  expect(params.getAll('tags')).toEqual(['django']);
  expect(params.get('archive')).toBe('true');
  expect(params.get('ordering')).toBe('date_limite');
  expect(screen.getByLabelText('Inclure les archivees')).toBeChecked();
});

test('updates the browser URL and reloads when a filter changes', async () => {
  renderPage();
  await screen.findByText('Aucune candidature');
  fireEvent.change(screen.getByLabelText('Recherche'), { target: { value: 'django' } });
  await waitFor(() => expect(candidaturesAPI.getAll).toHaveBeenLastCalledWith(expect.any(URLSearchParams)));
  expect(candidaturesAPI.getAll.mock.calls.at(-1)[0].get('search')).toBe('django');
  expect(window.location.search).toContain('search=django');
});

test('bascule en kanban et retire une carte qui ne correspond plus au filtre apres son deplacement', async () => {
  const item = { ...offre, id: 4, statut: 'postule', favori: true };
  candidaturesAPI.getAll.mockResolvedValue({ data: [item] });
  candidaturesAPI.patch.mockResolvedValue({ data: { ...item, statut: 'entretien' } });
  renderPage('/candidatures?tags=django&statut=postule');

  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(screen.getByRole('button', { name: 'Vue Kanban' }));
  expect(screen.getByText('Dev Django - postule')).toBeInTheDocument();
  expect(candidaturesAPI.getAll.mock.calls[0][0].getAll('tags')).toEqual(['django']);
  expect(candidaturesAPI.getAll.mock.calls[0][0].getAll('statut')).toEqual(['postule']);

  fireEvent.click(screen.getByRole('button', { name: 'Deplacer vers entretien' }));

  await waitFor(() => expect(candidaturesAPI.patch).toHaveBeenCalledWith(4, { statut: 'entretien' }));
  await waitFor(() => expect(screen.queryByText(/Dev Django -/)).not.toBeInTheDocument());
});

test('exporte en CSV avec les filtres actifs', async () => {
  const createObjectURL = jest.fn(() => 'blob:candidatures');
  const revokeObjectURL = jest.fn();
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
  const clickDownload = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  candidaturesAPI.exportCsv.mockResolvedValue({ data: new Blob(['csv']) });
  renderPage('/candidatures?statut=postule&tags=django&tags=remote');
  await screen.findByText('Aucune candidature');

  fireEvent.click(screen.getByRole('button', { name: 'Exporter en CSV' }));

  await waitFor(() => expect(candidaturesAPI.exportCsv).toHaveBeenCalled());
  const params = candidaturesAPI.exportCsv.mock.calls[0][0];
  expect(params.getAll('statut')).toEqual(['postule']);
  expect(params.getAll('tags')).toEqual(['django', 'remote']);
  expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
  expect(clickDownload).toHaveBeenCalled();
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:candidatures');
  clickDownload.mockRestore();
});

test('selectionne plusieurs candidatures et prepare des brouillons individuels sans envoi', async () => {
  candidaturesAPI.getAll.mockResolvedValue({ data: [
    { ...offre, id: 1, titre: 'Dev Django', entreprise: 'Entreprise A' },
    { ...offre, id: 2, titre: 'Dev React', entreprise: 'Entreprise B' },
  ] });
  candidaturesAPI.prepareEmails.mockResolvedValue({ data: { emails: [
    { id: 11, candidature: 1, recipient_email: 'a@example.com', status: 'draft' },
    { id: 12, candidature: 2, recipient_email: 'b@example.com', status: 'draft' },
  ] } });
  renderPage();
  await screen.findByRole('heading', { name: 'Dev React' });
  fireEvent.click(screen.getByRole('checkbox', { name: /Selectionner Dev Django/ }));
  fireEvent.click(screen.getByRole('checkbox', { name: /Selectionner Dev React/ }));
  fireEvent.click(screen.getByRole('button', { name: /Preparer les emails/ }));
  const dialog = screen.getByRole('dialog', { name: /Preparer les emails/ });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /Formation/ }), { target: { value: 'Licence web' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /Portfolio/ }), { target: { value: 'https://portfolio.example.com' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /GitHub/ }), { target: { value: 'https://github.com/example' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /Destinataire - Entreprise A/ }), { target: { value: 'a@example.com' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /Destinataire - Entreprise B/ }), { target: { value: 'b@example.com' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Creer les brouillons' }));
  await waitFor(() => expect(candidaturesAPI.prepareEmails).toHaveBeenCalledWith({
    formation: 'Licence web', portfolio_url: 'https://portfolio.example.com', github_url: 'https://github.com/example',
    emails: [
      expect.objectContaining({ candidature_id: 1, recipient_email: 'a@example.com' }),
      expect.objectContaining({ candidature_id: 2, recipient_email: 'b@example.com' }),
    ],
  }));
  expect(await screen.findByText('2 brouillons crees')).toBeInTheDocument();
  expect(screen.getAllByText('Brouillon')).toHaveLength(2);
  const links = screen.getAllByRole('link', { name: /Voir le brouillon/ });
  expect(links).toHaveLength(2);
  expect(links[0]).toHaveAttribute('href', '/candidatures/1?email_id=11');
  expect(links[1]).toHaveAttribute('href', '/candidatures/2?email_id=12');
  expect(links[0]).toHaveAttribute('target', '_blank');
});

test('affiche les erreurs de validation sur les candidatures concernees sans fermer la saisie', async () => {
  candidaturesAPI.getAll.mockResolvedValue({ data: [
    { ...offre, id: 1, titre: 'Dev Django', entreprise: 'Entreprise A' },
    { ...offre, id: 2, titre: 'Dev React', entreprise: 'Entreprise B' },
  ] });
  candidaturesAPI.prepareEmails.mockRejectedValue({ response: { data: { row_errors: [
    { index: 1, candidature_id: 2, errors: { recipient_email: ['Adresse e-mail invalide.'] } },
  ] } } });
  renderPage();
  await screen.findByRole('heading', { name: 'Dev React' });
  fireEvent.click(screen.getByRole('checkbox', { name: /Selectionner Dev Django/ }));
  fireEvent.click(screen.getByRole('checkbox', { name: /Selectionner Dev React/ }));
  fireEvent.click(screen.getByRole('button', { name: /Preparer les emails/ }));
  const dialog = screen.getByRole('dialog', { name: /Preparer les emails/ });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /Destinataire - Entreprise A/ }), { target: { value: 'a@example.com' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: /Destinataire - Entreprise B/ }), { target: { value: 'bad' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Creer les brouillons' }));
  expect(await within(dialog).findByText('Adresse e-mail invalide.')).toBeInTheDocument();
  expect(within(dialog).getByText('Entreprise B')).toBeInTheDocument();
  expect(within(dialog).getByRole('textbox', { name: /Destinataire - Entreprise B/ })).toHaveValue('bad');
  expect(screen.queryByText(/brouillons crees/)).not.toBeInTheDocument();
});

test('associe une erreur de civilite au bon champ de la bonne candidature', async () => {
  candidaturesAPI.getAll.mockResolvedValue({ data: [
    { ...offre, id: 1, titre: 'Dev Django', entreprise: 'Entreprise A' },
    { ...offre, id: 2, titre: 'Dev React', entreprise: 'Entreprise B' },
  ] });
  candidaturesAPI.prepareEmails.mockRejectedValue({ response: { data: { row_errors: [
    { index: 1, candidature_id: 2, errors: { civilite: ['30 caracteres maximum.'] } },
  ] } } });
  renderPage();
  await screen.findByRole('heading', { name: 'Dev React' });
  fireEvent.click(screen.getByRole('checkbox', { name: /Selectionner Dev Django/ }));
  fireEvent.click(screen.getByRole('checkbox', { name: /Selectionner Dev React/ }));
  fireEvent.click(screen.getByRole('button', { name: /Preparer les emails/ }));
  const target = within(screen.getByRole('region', { name: 'Entreprise B' }));
  fireEvent.click(screen.getByRole('button', { name: 'Creer les brouillons' }));
  expect(await target.findByText('30 caracteres maximum.')).toBeInTheDocument();
  expect(target.getByRole('textbox', { name: 'Civilite' })).toHaveAttribute('aria-invalid', 'true');
  expect(target.getByRole('textbox', { name: /Destinataire/ })).toHaveAttribute('aria-invalid', 'false');
  expect(within(screen.getByRole('region', { name: 'Entreprise A' })).queryByText('30 caracteres maximum.')).not.toBeInTheDocument();
});
