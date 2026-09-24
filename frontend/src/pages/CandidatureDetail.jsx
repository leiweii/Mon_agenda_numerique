import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert, Autocomplete, Box, Button, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Divider, FormControl,
  Grid, IconButton, InputLabel, Link, MenuItem, Select, Stack, TextField,
  Tooltip, Typography,
} from '@mui/material';
import {
  ArchiveOutlined, ArrowBack, DeleteOutline, EditOutlined, OpenInNew,
  Save, Star, StarBorder,
} from '@mui/icons-material';
import { format, isValid, parseISO } from 'date-fns';
import ActionForm from '../components/Candidatures/ActionForm';
import ActionTimeline from '../components/Candidatures/ActionTimeline';
import CandidatureForm from '../components/Candidatures/CandidatureForm';
import EmailBrouillonDialog from '../components/Candidatures/EmailBrouillonDialog';
import { MODES_TRAVAIL, SOURCES_CANAL, STATUTS, TYPES_POSTE } from '../components/Candidatures/options';
import { candidatureActionsAPI, candidaturesAPI } from '../services/api';
import { extraireMessageErreur } from '../services/errors';

function dateLabel(value, withTime = false) {
  const parsed = value ? parseISO(value) : null;
  return parsed && isValid(parsed) ? format(parsed, withTime ? 'dd/MM/yyyy HH:mm' : 'dd/MM/yyyy') : 'Non renseignee';
}

function Info({ label, children }) {
  return <Box><Typography variant="caption" color="text.secondary">{label}</Typography><Typography sx={{ overflowWrap: 'anywhere' }}>{children || 'Non renseigne'}</Typography></Box>;
}

function reconciliationAvailable(email, now) {
  return email.status === 'sending' && (
    Boolean(email.error_message) || new Date(email.updated_at).getTime() <= now - 5 * 60 * 1000
  );
}

function hasMultipleConfirmedEmails(emails) {
  const byId = new Map(emails.map(email => [email.id, email]));
  const sentCounts = new Map();
  for (const email of emails) {
    if (email.status !== 'sent') continue;
    let root = email;
    const seen = new Set();
    while (root.retry_of && byId.has(root.retry_of) && !seen.has(root.id)) {
      seen.add(root.id);
      root = byId.get(root.retry_of);
    }
    const count = (sentCounts.get(root.id) || 0) + 1;
    if (count >= 2) return true;
    sentCounts.set(root.id, count);
  }
  return false;
}

export default function CandidatureDetail() {
  const { id } = useParams();
  const candidatureId = Number(id);
  const requestedEmailId = Number(new URLSearchParams(window.location.search).get('email_id'));
  const navigate = useNavigate();
  const openedEmailId = useRef(null);
  const [candidature, setCandidature] = useState(null);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [actionEditor, setActionEditor] = useState(undefined);
  const [confirmation, setConfirmation] = useState('');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [emails, setEmails] = useState([]);
  const [cvName, setCvName] = useState('');
  const [preparationOpen, setPreparationOpen] = useState(false);
  const [preparationValues, setPreparationValues] = useState({
    recipient_email: '', civilite: '', prenom_contact: '', nom_contact: '',
    formation: '', portfolio_url: '', github_url: '',
  });
  const [emailDraft, setEmailDraft] = useState(null);
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [emailNotice, setEmailNotice] = useState('');
  const [sendTarget, setSendTarget] = useState(null);
  const [sendUnknownId, setSendUnknownId] = useState(null);
  const [retryTarget, setRetryTarget] = useState(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!emails.some(email => email.status === 'sending' && !email.error_message)) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(timer);
  }, [emails]);

  const applyCandidature = data => {
    setCandidature(data);
    setTags(data.tags || []);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [candidatureResponse, actionsResponse, emailsResponse, cvResponse] = await Promise.all([
        candidaturesAPI.getById(candidatureId),
        candidatureActionsAPI.getAll(candidatureId),
        candidaturesAPI.getEmails(candidatureId),
        candidaturesAPI.getDefaultCv(),
      ]);
      applyCandidature(candidatureResponse.data);
      setActions(actionsResponse.data);
      setEmails(emailsResponse.data);
      setCvName(cvResponse.data.filename || '');
    } catch (failure) {
      setError(extraireMessageErreur(failure, 'Impossible de charger cette candidature.'));
    } finally {
      setLoading(false);
    }
  }, [candidatureId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!requestedEmailId || openedEmailId.current === requestedEmailId) return;
    const requestedDraft = emails.find(email => email.id === requestedEmailId && email.status === 'draft');
    if (requestedDraft) {
      openedEmailId.current = requestedEmailId;
      setEmailDraft(requestedDraft);
    }
  }, [emails, requestedEmailId]);

  const patchCandidature = async data => {
    setBusy(true);
    setError('');
    try {
      const response = await candidaturesAPI.patch(candidatureId, data);
      applyCandidature(response.data);
    } catch (failure) {
      setError(extraireMessageErreur(failure, 'Impossible de modifier la candidature.'));
    } finally {
      setBusy(false);
    }
  };

  const saveGeneral = async data => {
    const response = await candidaturesAPI.update(candidatureId, data);
    applyCandidature(response.data);
  };

  const saveAction = async data => {
    const response = actionEditor
      ? await candidatureActionsAPI.update(candidatureId, actionEditor.id, data)
      : await candidatureActionsAPI.create(candidatureId, data);
    setActions(current => actionEditor
      ? current.map(item => item.id === response.data.id ? response.data : item)
      : [response.data, ...current]);
  };

  const deleteAction = async item => {
    if (!window.confirm('Supprimer cette action ?')) return;
    await candidatureActionsAPI.delete(candidatureId, item.id);
    setActions(current => current.filter(action => action.id !== item.id));
  };

  const changePreparation = field => event => {
    setPreparationValues(current => ({ ...current, [field]: event.target.value }));
  };

  const prepareEmail = async () => {
    setEmailBusy(true);
    setEmailError('');
    setEmailNotice('');
    try {
      const response = await candidaturesAPI.prepareEmail(candidatureId, preparationValues);
      setEmails(current => [response.data, ...current]);
      setPreparationOpen(false);
      setEmailDraft(response.data);
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible de préparer le brouillon.'));
    } finally {
      setEmailBusy(false);
    }
  };

  const saveEmail = async (emailId, values) => {
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.updateEmail(candidatureId, emailId, values);
      setEmails(current => current.map(item => item.id === emailId ? response.data : item));
      setEmailDraft(response.data);
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible d’enregistrer le brouillon.'));
    } finally {
      setEmailBusy(false);
    }
  };

  const cancelEmail = async emailId => {
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.cancelEmail(candidatureId, emailId);
      setEmails(current => current.map(item => item.id === emailId ? response.data : item));
      setEmailDraft(null);
      setEmailNotice('Brouillon annulé.');
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible d’annuler le brouillon.'));
    } finally {
      setEmailBusy(false);
    }
  };

  const prepareSend = async (emailId, values) => {
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.prepareEmailSend(candidatureId, emailId, values);
      setEmails(current => current.map(item => item.id === emailId ? response.data : item));
      setEmailDraft(null);
      setEmailNotice('Envoi préparé. Aucun email n’a été envoyé.');
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible de préparer l’envoi.'));
    } finally {
      setEmailBusy(false);
    }
  };

  const replaceEmail = updated => {
    setEmails(current => current.map(item => item.id === updated.id ? updated : item));
  };

  const refreshEmailHistory = async () => {
    try {
      const response = await candidatureActionsAPI.getAll(candidatureId);
      setActions(response.data);
    } catch (_failure) {
      setEmailError('Le statut de l’email est enregistré, mais l’historique est momentanément indisponible. Rechargez la page.');
    }
  };

  const openSendConfirmation = async email => {
    if (emailBusy || sendUnknownId === email.id) return;
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.getDefaultCv();
      const { filename, fingerprint } = response.data;
      setCvName(filename || '');
      if (!filename || !fingerprint) {
        setEmailError('Configurez un CV PDF accessible avant de confirmer l’envoi.');
        return;
      }
      setSendTarget({ ...email, confirmedCvName: filename, cvFingerprint: fingerprint });
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible de vérifier le CV avant l’envoi.'));
    } finally {
      setEmailBusy(false);
    }
  };

  const reconcileSendStatus = async (emailId, { allowReady = false, definitePreSend = false } = {}) => {
    try {
      const response = await candidaturesAPI.getEmails(candidatureId);
      setEmails(response.data);
      const current = response.data.find(email => email.id === emailId);
      if (current?.status === 'sent') {
        setSendUnknownId(null);
        setEmailNotice('Email envoyé via Gmail.');
        await refreshEmailHistory();
      } else if (current?.status === 'sending') {
        setSendUnknownId(null);
        setEmailNotice('Résultat incertain : vérifiez le dossier Envoyés avant toute nouvelle tentative.');
      } else if (current?.status === 'failed') {
        setSendUnknownId(null);
        setEmailError('L’envoi a échoué. Vous pouvez créer une nouvelle tentative.');
      } else if (current?.status === 'ready' && (allowReady || definitePreSend)) {
        setSendUnknownId(null);
        if (allowReady) setEmailNotice('Aucun envoi confirmé : relisez le brouillon avant une nouvelle confirmation.');
      } else {
        setSendUnknownId(emailId);
      }
      return current;
    } catch (_failure) {
      setSendUnknownId(emailId);
      return null;
    }
  };

  const refreshUnknownSend = async emailId => {
    if (emailBusy) return;
    setEmailBusy(true);
    setEmailError('');
    try {
      await reconcileSendStatus(emailId, { allowReady: true });
    } finally {
      setEmailBusy(false);
    }
  };

  const sendReadyEmail = async () => {
    if (!sendTarget || emailBusy) return;
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.sendEmail(candidatureId, sendTarget.id, sendTarget.cvFingerprint);
      replaceEmail(response.data);
      setEmailNotice(response.data.status === 'sent'
        ? 'Email envoyé via Gmail.'
        : 'Résultat incertain : vérifiez le dossier Envoyés avant toute nouvelle tentative.');
      setSendTarget(null);
      await refreshEmailHistory();
    } catch (failure) {
      const emailId = sendTarget.id;
      setSendTarget(null);
      if (failure.response?.data?.id) {
        replaceEmail(failure.response.data);
        setEmailError(extraireMessageErreur(failure, 'L’envoi a échoué. Vous pouvez créer une nouvelle tentative.'));
      } else {
        const detail = failure.response?.data?.detail || '';
        const cvChanged = failure.response?.status === 409 && detail.includes('Le CV a change');
        const definitePreSend = failure.response?.status === 400 || cvChanged;
        if (cvChanged) {
          try {
            const cvResponse = await candidaturesAPI.getDefaultCv();
            setCvName(cvResponse.data.filename || '');
          } catch (_cvFailure) {
            // La prochaine ouverture de confirmation reverifiera le CV.
          }
        }
        const current = await reconcileSendStatus(emailId, { definitePreSend });
        if (definitePreSend && current?.status === 'ready') {
          setEmailError(detail || 'La validation avant l’envoi a échoué. Vérifiez le brouillon.');
        }
      }
    } finally {
      setEmailBusy(false);
    }
  };

  const confirmManual = async email => {
    if (emailBusy) return;
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.confirmEmailManually(candidatureId, email.id);
      replaceEmail(response.data);
      setEmailNotice('Envoi confirmé manuellement après vérification de Gmail.');
      await refreshEmailHistory();
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible de confirmer cet envoi.'));
    } finally {
      setEmailBusy(false);
    }
  };

  const createRetry = async () => {
    if (!retryTarget || emailBusy) return;
    setEmailBusy(true);
    setEmailError('');
    try {
      const response = await candidaturesAPI.createEmailRetry(candidatureId, retryTarget.id);
      setEmails(current => current.some(item => item.id === response.data.id)
        ? current.map(item => item.id === response.data.id ? response.data : item)
        : [response.data, ...current]);
      setRetryTarget(null);
      setEmailDraft(response.data);
      setEmailNotice('Nouvelle tentative créée en brouillon : relisez et préparez-la avant de confirmer l’envoi.');
    } catch (failure) {
      setEmailError(extraireMessageErreur(failure, 'Impossible de créer une nouvelle tentative.'));
      setRetryTarget(null);
    } finally {
      setEmailBusy(false);
    }
  };

  const twoConfirmedAttempts = hasMultipleConfirmedEmails(emails);

  const confirm = async () => {
    setBusy(true);
    setError('');
    try {
      if (confirmation === 'archive') {
        const response = await candidaturesAPI.archive(candidatureId);
        applyCandidature(response.data);
        setConfirmation('');
      } else {
        await candidaturesAPI.delete(candidatureId);
        navigate('/candidatures');
      }
    } catch (failure) {
      setError(extraireMessageErreur(failure, "L'action n'a pas pu etre effectuee."));
      setConfirmation('');
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Box role="status" aria-label="Chargement de la candidature" sx={{ py: 8, textAlign: 'center' }}><CircularProgress /></Box>;
  if (!candidature) return <Alert severity="error" action={<Button onClick={load}>Reessayer</Button>}>{error || 'Candidature introuvable.'}</Alert>;

  return (
    <Box sx={{ maxWidth: 1100, mx: 'auto', minWidth: 0 }}>
      <Button startIcon={<ArrowBack />} onClick={() => navigate('/candidatures')} sx={{ mb: 2 }}>Candidatures</Button>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography component="h1" variant="h4" sx={{ fontSize: '1.75rem', overflowWrap: 'anywhere' }}>{candidature.titre}</Typography>
            {candidature.archive && <Chip size="small" label="Archivee" variant="outlined" />}
          </Stack>
          <Typography color="text.secondary">{candidature.entreprise || 'Entreprise non renseignee'}</Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
            <Chip size="small" label={TYPES_POSTE[candidature.type_poste] || 'Autre'} variant="outlined" />
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel id="detail-statut-label">Statut</InputLabel>
              <Select labelId="detail-statut-label" label="Statut" value={candidature.statut} disabled={busy}
                onChange={event => patchCandidature({ statut: event.target.value })}>
                {Object.entries(STATUTS).map(([value, option]) => <MenuItem key={value} value={value}>{option.label}</MenuItem>)}
              </Select>
            </FormControl>
            <Tooltip title={candidature.favori ? 'Retirer des favoris' : 'Ajouter aux favoris'}>
              <span><IconButton disabled={busy} color={candidature.favori ? 'warning' : 'default'}
                aria-label={candidature.favori ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                onClick={() => patchCandidature({ favori: !candidature.favori })}>
                {candidature.favori ? <Star /> : <StarBorder />}
              </IconButton></span>
            </Tooltip>
          </Stack>
        </Box>
        <Stack direction="row" useFlexGap flexWrap="wrap" alignContent="flex-start" spacing={1}>
          <Button component={Link} href={candidature.url} target="_blank" rel="noopener noreferrer" startIcon={<OpenInNew />}>Voir l'annonce</Button>
          <Button startIcon={<EditOutlined />} onClick={() => setEditorOpen(true)} disabled={busy}>Modifier</Button>
          <Button startIcon={<ArchiveOutlined />} onClick={() => setConfirmation('archive')} disabled={busy || candidature.archive}>Archiver</Button>
          <Button color="error" startIcon={<DeleteOutline />} onClick={() => setConfirmation('delete')} disabled={busy}>Supprimer</Button>
        </Stack>
      </Stack>

      <Divider />
      <Box component="section" sx={{ py: 3 }}>
        <Typography component="h2" variant="h6" sx={{ mb: 2 }}>Informations generales</Typography>
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Entreprise">{candidature.entreprise}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Lieu">{candidature.lieu}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Mode de travail">{MODES_TRAVAIL[candidature.mode_travail]}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Source du canal">{SOURCES_CANAL[candidature.source_canal]}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="CV utilise">{candidature.cv_utilise}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Source extraction">{candidature.source_extraction}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Date limite">{dateLabel(candidature.date_limite)}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Date de relance">{dateLabel(candidature.date_relance)}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Date d'ajout">{dateLabel(candidature.date_ajout, true)}</Info></Grid>
        </Grid>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'flex-start' }} sx={{ mt: 3 }}>
          <Autocomplete multiple freeSolo fullWidth options={[]} value={tags} inputValue={tagInput}
            onChange={(_, value) => setTags(value)} onInputChange={(_, value) => setTagInput(value)} disabled={busy}
            renderInput={params => <TextField {...params} size="small" label="Tags" />} />
          <Button variant="outlined" startIcon={<Save />} disabled={busy || JSON.stringify(tags) === JSON.stringify(candidature.tags || [])}
            onClick={() => patchCandidature({ tags: [...new Set(tags.map(tag => tag.trim()).filter(Boolean))] })}
            sx={{ flexShrink: 0 }}>Enregistrer les tags</Button>
        </Stack>
      </Box>

      <Divider />
      <Box component="section" sx={{ py: 3 }}>
        <Typography component="h2" variant="h6">Description</Typography>
        <Typography sx={{ mt: 1, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{candidature.description || 'Aucune description.'}</Typography>
        <Typography component="h2" variant="h6" sx={{ mt: 3 }}>Notes</Typography>
        <Typography sx={{ mt: 1, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{candidature.notes || 'Aucune note.'}</Typography>
      </Box>

      <Divider sx={{ mb: 3 }} />
      <Box component="section" aria-labelledby="emails-title" sx={{ pb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} spacing={2}>
          <Typography id="emails-title" component="h2" variant="h6">Emails de candidature</Typography>
          <Button variant="outlined" onClick={() => { setEmailError(''); setPreparationOpen(true); }} disabled={emailBusy}>Préparer un email</Button>
        </Stack>
        <Typography color="text.secondary" sx={{ mt: 1 }}>CV par défaut : {cvName || 'Aucun CV configuré'}</Typography>
        {emailNotice && <Alert severity="info" sx={{ mt: 2 }}>{emailNotice}</Alert>}
        {emailError && !preparationOpen && !emailDraft && <Alert severity="error" sx={{ mt: 2 }}>{emailError}</Alert>}
        {twoConfirmedAttempts && <Alert severity="warning" sx={{ mt: 2 }}>Deux envois confirmés pour cette chaîne de tentatives.</Alert>}
        {emails.length === 0 && <Typography color="text.secondary" sx={{ mt: 2 }}>Aucun brouillon préparé.</Typography>}
        <Stack spacing={1} sx={{ mt: 2 }}>
          {emails.map(email => (
            <Stack key={email.id} spacing={1} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} spacing={1}>
                <Typography sx={{ overflowWrap: 'anywhere' }}>{email.subject} — {email.recipient_email}</Typography>
                <Chip size="small" label={{ draft: 'Brouillon', ready: 'Prêt à envoyer', cancelled: 'Annulé', sent: 'Envoyé', failed: 'Échec', sending: 'En cours' }[email.status] || email.status} />
                {email.status === 'draft' && <Button onClick={() => { setEmailError(''); setEmailDraft(email); }} disabled={emailBusy} aria-label={`Voir le brouillon ${email.subject}`}>Voir</Button>}
                {email.status === 'ready' && sendUnknownId !== email.id && <Button onClick={() => openSendConfirmation(email)} disabled={emailBusy} aria-label={`Envoyer l’email ${email.subject}`}>Envoyer via Gmail</Button>}
              </Stack>
              {sendUnknownId === email.id && <Alert severity="warning" action={<Button onClick={() => refreshUnknownSend(email.id)} disabled={emailBusy}>Actualiser le statut</Button>}>Issue de l’envoi inconnue. Aucun renvoi automatique ; actualisez le statut avant toute nouvelle confirmation.</Alert>}
              {email.retry_of && <Typography variant="caption">Nouvelle tentative de l’email #{email.retry_of}</Typography>}
              {emails.some(next => next.retry_of === email.id) && (
                <Typography variant="caption">Tentative suivante : email #{emails.find(next => next.retry_of === email.id).id}</Typography>
              )}
              {email.status === 'sending' && (reconciliationAvailable(email, now) ? (
                <>
                  <Alert severity="warning">Résultat incertain : Gmail a peut-être envoyé ce message. Vérifiez le dossier Envoyés (destinataire, objet et date). Aucun renvoi automatique n’aura lieu.</Alert>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                    <Button onClick={() => confirmManual(email)} disabled={emailBusy}>J’ai vérifié : email envoyé</Button>
                    {!emails.some(next => next.retry_of === email.id) && <Button onClick={() => setRetryTarget(email)} disabled={emailBusy} aria-label={`Créer une nouvelle tentative pour ${email.subject}`}>Créer une nouvelle tentative</Button>}
                  </Stack>
                </>
              ) : <Typography>Envoi en cours</Typography>)}
              {email.status === 'failed' && (
                <>
                  <Alert severity="error">{email.error_message === 'reconnect_required'
                    ? 'Reconnectez votre compte Gmail avant une nouvelle tentative.'
                    : 'Échec d’envoi. Vérifiez la connexion Gmail ou créez une nouvelle tentative.'}</Alert>
                  {!emails.some(next => next.retry_of === email.id) && <Button onClick={() => setRetryTarget(email)} disabled={emailBusy} aria-label={`Créer une nouvelle tentative pour ${email.subject}`} sx={{ alignSelf: 'flex-start' }}>Créer une nouvelle tentative</Button>}
                </>
              )}
              {email.status === 'cancelled' && email.retry_of && !emails.some(next => next.retry_of === email.id) && (
                <Button onClick={() => setRetryTarget(email)} disabled={emailBusy} aria-label={`Relancer la tentative annulée #${email.id}`} sx={{ alignSelf: 'flex-start' }}>Créer une nouvelle tentative</Button>
              )}
            </Stack>
          ))}
        </Stack>
      </Box>

      <Divider sx={{ mb: 3 }} />
      <ActionTimeline actions={actions} emails={emails} disabled={busy} onAdd={() => setActionEditor(null)}
        onEdit={setActionEditor} onDelete={deleteAction} />

      <CandidatureForm open={editorOpen} candidature={candidature} onClose={() => setEditorOpen(false)} onSubmit={saveGeneral} />
      <ActionForm open={actionEditor !== undefined} action={actionEditor || null} onClose={() => setActionEditor(undefined)} onSubmit={saveAction} />
      <Dialog open={preparationOpen} onClose={() => { if (!emailBusy) setPreparationOpen(false); }} fullWidth maxWidth="sm" aria-labelledby="prepare-email-title">
        <DialogTitle id="prepare-email-title">Préparer un email</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {emailError && <Grid size={12}><Alert severity="error">{emailError}</Alert></Grid>}
            <Grid size={12}><TextField fullWidth required type="email" label="Destinataire" value={preparationValues.recipient_email} onChange={changePreparation('recipient_email')} disabled={emailBusy} /></Grid>
            <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth label="Civilité" value={preparationValues.civilite} onChange={changePreparation('civilite')} disabled={emailBusy} /></Grid>
            <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth label="Prénom du contact" value={preparationValues.prenom_contact} onChange={changePreparation('prenom_contact')} disabled={emailBusy} /></Grid>
            <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth label="Nom du contact" value={preparationValues.nom_contact} onChange={changePreparation('nom_contact')} disabled={emailBusy} /></Grid>
            <Grid size={12}><TextField fullWidth required label="Formation" value={preparationValues.formation} onChange={changePreparation('formation')} disabled={emailBusy} /></Grid>
            <Grid size={12}><TextField fullWidth required type="url" label="Portfolio" value={preparationValues.portfolio_url} onChange={changePreparation('portfolio_url')} disabled={emailBusy} /></Grid>
            <Grid size={12}><TextField fullWidth required type="url" label="GitHub" value={preparationValues.github_url} onChange={changePreparation('github_url')} disabled={emailBusy} /></Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreparationOpen(false)} disabled={emailBusy}>Fermer</Button>
          <Button variant="contained" onClick={prepareEmail} disabled={emailBusy || !preparationValues.recipient_email.trim() || !preparationValues.formation.trim() || !preparationValues.portfolio_url.trim() || !preparationValues.github_url.trim()}>Créer le brouillon</Button>
        </DialogActions>
      </Dialog>
      <EmailBrouillonDialog open={Boolean(emailDraft)} draft={emailDraft} cvName={cvName} busy={emailBusy} error={emailError} onSave={saveEmail} onCancel={cancelEmail} onSend={prepareSend} />
      <Dialog open={Boolean(sendTarget)} onClose={() => { if (!emailBusy) setSendTarget(null); }} aria-labelledby="confirm-email-send-title" fullWidth maxWidth="sm">
        <DialogTitle id="confirm-email-send-title">Confirmer l’envoi Gmail</DialogTitle>
        <DialogContent>
          <Stack spacing={1}>
            <Typography>Un email réel sera envoyé à ce destinataire avec ce CV.</Typography>
            <Typography>{sendTarget?.recipient_email}</Typography>
            <Typography>{sendTarget?.subject}</Typography>
            <Typography>{sendTarget?.confirmedCvName || 'Aucun CV configuré'}</Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSendTarget(null)} disabled={emailBusy}>Annuler</Button>
          <Button variant="contained" onClick={sendReadyEmail} disabled={emailBusy || !sendTarget?.cvFingerprint}>
            {emailBusy ? 'Envoi...' : 'Confirmer l’envoi'}
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(retryTarget)} onClose={() => { if (!emailBusy) setRetryTarget(null); }} aria-labelledby="retry-email-title" fullWidth maxWidth="sm">
        <DialogTitle id="retry-email-title">Risque de double envoi</DialogTitle>
        <DialogContent><Typography>Le premier email a peut-être été envoyé. Vérifiez Gmail avant de créer un nouveau brouillon ; celui-ci ne sera pas envoyé automatiquement.</Typography></DialogContent>
        <DialogActions>
          <Button onClick={() => setRetryTarget(null)} disabled={emailBusy}>Annuler</Button>
          <Button variant="contained" onClick={createRetry} disabled={emailBusy}>{emailBusy ? 'Création...' : 'Créer le brouillon'}</Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(confirmation)} onClose={() => { if (!busy) setConfirmation(''); }}>
        <DialogTitle>{confirmation === 'archive' ? 'Archiver la candidature ?' : 'Supprimer la candidature ?'}</DialogTitle>
        <DialogContent><Typography>{confirmation === 'archive' ? 'Elle ne figurera plus dans la liste active.' : 'Cette suppression est definitive et effacera son historique.'}</Typography></DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmation('')} disabled={busy}>Annuler</Button>
          <Button color={confirmation === 'delete' ? 'error' : 'primary'} variant="contained" onClick={confirm} disabled={busy}>
            {confirmation === 'archive' ? 'Archiver' : 'Supprimer definitivement'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

