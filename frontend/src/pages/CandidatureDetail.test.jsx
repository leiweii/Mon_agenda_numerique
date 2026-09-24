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
    getDefaultCv: jest.fn(), getEmails: jest.fn(), prepareEmail: jest.fn(),
    updateEmail: jest.fn(), cancelEmail: jest.fn(), prepareEmailSend: jest.fn(),
    sendEmail: jest.fn(), confirmEmailManually: jest.fn(), createEmailRetry: jest.fn(),
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
  candidaturesAPI.getDefaultCv.mockResolvedValue({ data: { filename: 'CV_backend.pdf', fingerprint: 'cv-original' } });
  candidaturesAPI.getEmails.mockResolvedValue({ data: [] });
});

async function openSendDialog() {
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer l’email Candidature Django' }));
  return screen.findByRole('dialog', { name: 'Confirmer l’envoi Gmail' });
}

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
  expect(await screen.findByText('Archivee')).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

  fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Supprimer definitivement' }));
  await waitFor(() => expect(candidaturesAPI.delete).toHaveBeenCalledWith(7));
  expect(mockNavigate).toHaveBeenCalledWith('/candidatures');
});

test('prepares then edits and saves a draft without sending it', async () => {
  const draft = { id: 18, recipient_email: 'first@example.com', subject: 'First', body: 'First body', status: 'draft' };
  candidaturesAPI.prepareEmail.mockResolvedValue({ data: draft });
  candidaturesAPI.updateEmail.mockResolvedValue({ data: { ...draft, subject: 'Updated subject' } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(screen.getByRole('button', { name: 'Préparer un email' }));
  const preparation = screen.getByRole('dialog', { name: 'Préparer un email' });
  fireEvent.change(within(preparation).getByRole('textbox', { name: 'Destinataire' }), { target: { value: 'first@example.com' } });
  fireEvent.change(within(preparation).getByRole('textbox', { name: 'Formation' }), { target: { value: 'Licence professionnelle' } });
  fireEvent.change(within(preparation).getByRole('textbox', { name: 'Portfolio' }), { target: { value: 'https://portfolio.example.com' } });
  fireEvent.change(within(preparation).getByRole('textbox', { name: 'GitHub' }), { target: { value: 'https://github.com/example' } });
  fireEvent.click(within(preparation).getByRole('button', { name: 'Créer le brouillon' }));

  await waitFor(() => expect(candidaturesAPI.prepareEmail).toHaveBeenCalledWith(7, expect.objectContaining({
    recipient_email: 'first@example.com', formation: 'Licence professionnelle',
  })));
  const preview = await screen.findByRole('dialog', { name: 'Prévisualiser le brouillon' });
  expect(within(preview).getByText('CV_backend.pdf')).toBeInTheDocument();
  fireEvent.change(within(preview).getByRole('textbox', { name: 'Objet' }), { target: { value: 'Updated subject' } });
  fireEvent.click(within(preview).getByRole('button', { name: 'Enregistrer' }));

  await waitFor(() => expect(candidaturesAPI.updateEmail).toHaveBeenCalledWith(7, 18, {
    recipient_email: 'first@example.com', subject: 'Updated subject', body: 'First body',
  }));
  expect(candidaturesAPI.prepareEmailSend).not.toHaveBeenCalled();
}, 20000);

test('annuls an existing draft and leaves it visible with cancelled status', async () => {
  const draft = { id: 19, recipient_email: 'first@example.com', subject: 'First', body: 'First body', status: 'draft' };
  candidaturesAPI.getEmails.mockResolvedValue({ data: [draft] });
  candidaturesAPI.cancelEmail.mockResolvedValue({ data: { ...draft, status: 'cancelled' } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(screen.getByRole('button', { name: 'Voir le brouillon First' }));
  fireEvent.click(within(screen.getByRole('dialog', { name: 'Prévisualiser le brouillon' })).getByRole('button', { name: 'Annuler' }));

  await waitFor(() => expect(candidaturesAPI.cancelEmail).toHaveBeenCalledWith(7, 19));
  expect(await screen.findByText('Annulé')).toBeInTheDocument();
});

const readyEmail = {
  id: 25, candidature: 7, recipient_email: 'jobs@example.com',
  subject: 'Candidature Django', body: 'Bonjour,', status: 'ready',
  created_at: '2026-09-23T09:00:00Z', updated_at: '2026-09-23T09:00:00Z', retry_of: null,
};

test('shows separate confirmation for a ready email and cancellation does not send', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  const dialog = await openSendDialog();
  expect(within(dialog).getByText('jobs@example.com')).toBeInTheDocument();
  expect(within(dialog).getByText('Candidature Django')).toBeInTheDocument();
  expect(within(dialog).getByText('CV_backend.pdf')).toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));

  expect(candidaturesAPI.sendEmail).not.toHaveBeenCalled();
});

test('confirms actual send once and refreshes the timeline', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  let resolveSend;
  candidaturesAPI.sendEmail.mockReturnValue(new Promise(resolve => { resolveSend = resolve; }));
  candidatureActionsAPI.getAll
    .mockResolvedValueOnce({ data: [existingAction] })
    .mockResolvedValueOnce({ data: [existingAction, { ...existingAction, id: 40, commentaire: 'Email #25 envoye via Gmail.' }] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));
  expect(screen.getByRole('button', { name: 'Envoi...' })).toBeDisabled();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);

  resolveSend({ data: { ...readyEmail, status: 'sent', gmail_message_id: 'gmail-25' } });
  expect(await screen.findByText('Email #25 envoye via Gmail.')).toBeInTheDocument();
  expect(screen.getByText('Envoyé')).toBeInTheDocument();
});

test('refreshes the CV before confirmation and sends its confirmed fingerprint', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  candidaturesAPI.getDefaultCv
    .mockResolvedValueOnce({ data: { filename: 'ancien.pdf', fingerprint: 'cv-old' } })
    .mockResolvedValueOnce({ data: { filename: 'nouveau.pdf', fingerprint: 'cv-new' } });
  candidaturesAPI.sendEmail.mockResolvedValue({ data: { ...readyEmail, status: 'sent' } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  const dialog = await openSendDialog();
  expect(within(dialog).getByText('nouveau.pdf')).toBeInTheDocument();
  expect(within(dialog).queryByText('ancien.pdf')).not.toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole('button', { name: 'Confirmer l’envoi' }));

  await waitFor(() => expect(candidaturesAPI.sendEmail).toHaveBeenCalledWith(7, 25, 'cv-new'));
});

test('a lost send response reloads sending and never offers a second immediate send', async () => {
  candidaturesAPI.getEmails
    .mockResolvedValueOnce({ data: [readyEmail] })
    .mockResolvedValueOnce({ data: [{ ...readyEmail, status: 'sending', error_message: 'network_outcome_unknown' }] });
  candidaturesAPI.sendEmail.mockRejectedValue(new Error('network response lost'));
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText(/Résultat incertain : Gmail a peut-être envoyé ce message/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Envoyer l’email Candidature Django' })).not.toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);
});

test('a lost send response can reveal an already sent email and refresh history', async () => {
  candidaturesAPI.getEmails
    .mockResolvedValueOnce({ data: [readyEmail] })
    .mockResolvedValueOnce({ data: [{ ...readyEmail, status: 'sent', gmail_message_id: 'gmail-25' }] });
  candidaturesAPI.sendEmail.mockRejectedValue(new Error('network response lost'));
  candidatureActionsAPI.getAll
    .mockResolvedValueOnce({ data: [existingAction] })
    .mockResolvedValueOnce({ data: [existingAction, { ...existingAction, id: 40, commentaire: 'Email #25 envoye via Gmail.' }] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText('Email #25 envoye via Gmail.')).toBeInTheDocument();
  expect(screen.getByText('Envoyé')).toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);
});

test('a lost send response and failed status reload block another send', async () => {
  candidaturesAPI.getEmails
    .mockResolvedValueOnce({ data: [readyEmail] })
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ data: [{ ...readyEmail, status: 'sending', error_message: 'network_outcome_unknown' }] });
  candidaturesAPI.sendEmail.mockRejectedValue(new Error('network response lost'));
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText(/Issue de l’envoi inconnue/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Envoyer l’email Candidature Django' })).not.toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Confirmer l’envoi Gmail', hidden: true })).not.toBeInTheDocument());
  fireEvent.click(await screen.findByRole('button', { name: 'Actualiser le statut' }));
  expect(await screen.findByText(/Résultat incertain : Gmail a peut-être envoyé ce message/)).toBeInTheDocument();
}, 10000);

test('a 409 without serialized email reloads the current sending status', async () => {
  candidaturesAPI.getEmails
    .mockResolvedValueOnce({ data: [readyEmail] })
    .mockResolvedValueOnce({ data: [{ ...readyEmail, status: 'sending', error_message: 'network_outcome_unknown' }] });
  candidaturesAPI.sendEmail.mockRejectedValue({ response: { status: 409, data: { detail: 'Deja en cours.' } } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText(/Résultat incertain : Gmail a peut-être envoyé ce message/)).toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);
});

test('a CV replacement during confirmation requires a new confirmation', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  candidaturesAPI.getDefaultCv
    .mockResolvedValueOnce({ data: { filename: 'ancien.pdf', fingerprint: 'cv-old' } })
    .mockResolvedValueOnce({ data: { filename: 'ancien.pdf', fingerprint: 'cv-old' } })
    .mockResolvedValueOnce({ data: { filename: 'nouveau.pdf', fingerprint: 'cv-new' } });
  candidaturesAPI.sendEmail.mockRejectedValue({ response: { status: 409, data: {
    detail: 'Le CV a change depuis votre confirmation. Verifiez-le avant l’envoi.',
  } } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText(/Le CV a change depuis votre confirmation/)).toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledWith(7, 25, 'cv-old');
  expect(screen.getByText('Prêt à envoyer')).toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);
});

test('a server validation error before reservation keeps ready with its explanation', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  candidaturesAPI.sendEmail.mockRejectedValue({ response: { status: 400, data: {
    detail: 'Adresse du destinataire invalide.',
  } } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText('Adresse du destinataire invalide.')).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Confirmer l’envoi Gmail', hidden: true })).not.toBeInTheDocument());
  fireEvent.click(await screen.findByRole('button', { name: 'Envoyer l’email Candidature Django' }));
  expect(await screen.findByRole('dialog', { name: 'Confirmer l’envoi Gmail' })).toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).toHaveBeenCalledTimes(1);
});

test('uncertain sending offers manual confirmation and a new editable draft', async () => {
  const uncertain = { ...readyEmail, status: 'sending', error_message: 'network_outcome_unknown' };
  candidaturesAPI.getEmails.mockResolvedValue({ data: [uncertain] });
  candidaturesAPI.createEmailRetry.mockResolvedValue({ data: { ...readyEmail, id: 26, status: 'draft', retry_of: 25 } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  expect(screen.getByText(/Résultat incertain/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Créer une nouvelle tentative pour Candidature Django' }));
  expect(screen.getByRole('dialog', { name: 'Risque de double envoi' })).toBeInTheDocument();
  fireEvent.click(within(screen.getByRole('dialog', { name: 'Risque de double envoi' })).getByRole('button', { name: 'Créer le brouillon' }));

  await waitFor(() => expect(candidaturesAPI.createEmailRetry).toHaveBeenCalledWith(7, 25));
  expect(await screen.findByRole('dialog', { name: 'Prévisualiser le brouillon' })).toBeInTheDocument();
  expect(screen.getByText('Nouvelle tentative de l’email #25')).toBeInTheDocument();
});

test('a fresh sending attempt is not manually actionable before five minutes', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [{
    ...readyEmail, status: 'sending', error_message: '', updated_at: new Date().toISOString(),
  }] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  expect(screen.getByText('Envoi en cours')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /J’ai vérifié/ })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Créer une nouvelle tentative/ })).not.toBeInTheDocument();
});

test('two linked sent attempts and their history remain visible with a warning', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [
    { ...readyEmail, status: 'sent' },
    { ...readyEmail, id: 26, status: 'sent', retry_of: 25 },
  ] });
  candidatureActionsAPI.getAll.mockResolvedValue({ data: [
    { ...existingAction, id: 40, commentaire: 'Email #25 confirme manuellement.' },
    { ...existingAction, id: 41, commentaire: 'Email #26 envoye via Gmail.' },
  ] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  expect(screen.getByText('Deux envois confirmés pour cette chaîne de tentatives.')).toBeInTheDocument();
  expect(screen.getByText('Email #25 confirme manuellement.')).toBeInTheDocument();
  expect(screen.getByText('Email #26 envoye via Gmail.')).toBeInTheDocument();
});

test('a cancelled retry can open another draft without branching from the first attempt', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [
    { ...readyEmail, status: 'sending', error_message: 'network_outcome_unknown' },
    { ...readyEmail, id: 26, status: 'cancelled', retry_of: 25 },
  ] });
  candidaturesAPI.createEmailRetry.mockResolvedValue({ data: { ...readyEmail, id: 27, status: 'draft', retry_of: 26 } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  expect(screen.queryByRole('button', { name: 'Créer une nouvelle tentative pour Candidature Django' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Relancer la tentative annulée #26' }));
  fireEvent.click(within(screen.getByRole('dialog', { name: 'Risque de double envoi' })).getByRole('button', { name: 'Créer le brouillon' }));

  await waitFor(() => expect(candidaturesAPI.createEmailRetry).toHaveBeenCalledWith(7, 26));
  expect(await screen.findByRole('dialog', { name: 'Prévisualiser le brouillon' })).toBeInTheDocument();
});

test('warns about two sent emails in one chain even with a failed attempt between them', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [
    { ...readyEmail, id: 25, status: 'sent', retry_of: null },
    { ...readyEmail, id: 26, status: 'failed', retry_of: 25 },
    { ...readyEmail, id: 27, status: 'sent', retry_of: 26 },
  ] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  expect(screen.getByText('Deux envois confirmés pour cette chaîne de tentatives.')).toBeInTheDocument();
});

test('preparing a draft does not call the Gmail send endpoint', async () => {
  const draft = { ...readyEmail, status: 'draft' };
  candidaturesAPI.getEmails.mockResolvedValue({ data: [draft] });
  candidaturesAPI.prepareEmailSend.mockResolvedValue({ data: readyEmail });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(screen.getByRole('button', { name: 'Voir le brouillon Candidature Django' }));
  fireEvent.click(within(screen.getByRole('dialog', { name: 'Prévisualiser le brouillon' })).getByRole('button', { name: 'Préparer l’envoi' }));

  await waitFor(() => expect(candidaturesAPI.prepareEmailSend).toHaveBeenCalledWith(7, 25, expect.any(Object)));
  expect(candidaturesAPI.sendEmail).not.toHaveBeenCalled();
});

test('a definite Gmail failure shows failed status and retry action', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  candidaturesAPI.sendEmail.mockRejectedValue({ response: { status: 502, data: {
    ...readyEmail, status: 'failed', error_message: 'gmail_rejected',
  } } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText('Échec')).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Confirmer l’envoi Gmail' })).not.toBeInTheDocument());
  expect(screen.getByRole('button', { name: 'Créer une nouvelle tentative pour Candidature Django' })).toBeInTheDocument();
});

test('a revoked Gmail token shows an explicit reconnect message', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  candidaturesAPI.sendEmail.mockRejectedValue({ response: { status: 502, data: {
    ...readyEmail, status: 'failed', error_message: 'reconnect_required',
  } } });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText('Reconnectez votre compte Gmail avant une nouvelle tentative.')).toBeInTheDocument();
});

test('manual confirmation of uncertain send refreshes history without Gmail send', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [{ ...readyEmail, status: 'sending', error_message: 'network_outcome_unknown' }] });
  candidaturesAPI.confirmEmailManually.mockResolvedValue({ data: { ...readyEmail, status: 'sent', manual_confirmation_at: new Date().toISOString() } });
  candidatureActionsAPI.getAll
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [{ ...existingAction, id: 44, commentaire: 'Email #25 confirme manuellement.' }] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(screen.getByRole('button', { name: 'J’ai vérifié : email envoyé' }));

  expect(await screen.findByText('Email #25 confirme manuellement.')).toBeInTheDocument();
  expect(screen.getByText('Envoyé')).toBeInTheDocument();
  expect(candidaturesAPI.sendEmail).not.toHaveBeenCalled();
});

test('a sending email older than five minutes becomes manually actionable on display', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [{
    ...readyEmail, status: 'sending', error_message: '',
    updated_at: new Date(Date.now() - 6 * 60 * 1000).toISOString(),
  }] });
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });

  expect(screen.getByText(/Résultat incertain/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'J’ai vérifié : email envoyé' })).toBeInTheDocument();
});

test('a sent email remains sent if history refresh fails', async () => {
  candidaturesAPI.getEmails.mockResolvedValue({ data: [readyEmail] });
  candidaturesAPI.sendEmail.mockResolvedValue({ data: { ...readyEmail, status: 'sent', gmail_message_id: 'gmail-25' } });
  candidatureActionsAPI.getAll
    .mockResolvedValueOnce({ data: [] })
    .mockRejectedValueOnce(new Error('history offline'));
  render(<CandidatureDetail />);
  await screen.findByRole('heading', { name: 'Dev Django' });
  fireEvent.click(within(await openSendDialog()).getByRole('button', { name: 'Confirmer l’envoi' }));

  expect(await screen.findByText('Envoyé')).toBeInTheDocument();
  expect(screen.queryByText(/L’envoi a échoué/)).not.toBeInTheDocument();
});
