import React, { useState } from 'react';
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, TextField, Typography } from '@mui/material';
import { candidaturesAPI } from '../../services/api';
import { extraireMessageErreur } from '../../services/errors';

const initialCommon = { formation: '', portfolio_url: '', github_url: '' };

const labels = {
  candidature_id: 'Candidature', recipient_email: 'Destinataire', civilite: 'Civilite',
  prenom_contact: 'Prenom du contact', nom_contact: 'Nom du contact',
  formation: 'Formation', portfolio_url: 'Portfolio', github_url: 'GitHub',
};

function fieldMessage(errors, field) {
  const value = errors?.[field];
  return Array.isArray(value) ? value.map(String).join(' ') : value ? String(value) : '';
}

function messages(errors) {
  return Object.keys(errors || {}).map(field => `${labels[field] || field} : ${fieldMessage(errors, field)}`).join(' ');
}

export default function PreparationEmailsMasseDialog({ candidatures, onClose, onSuccess }) {
  const [common, setCommon] = useState(initialCommon);
  const [rows, setRows] = useState(() => candidatures.map(candidature => ({
    candidature_id: candidature.id, recipient_email: '', civilite: '', prenom_contact: '', nom_contact: '',
  })));
  const [rowErrors, setRowErrors] = useState({});
  const [commonError, setCommonError] = useState('');
  const [busy, setBusy] = useState(false);

  const updateRow = (index, field, value) => {
    setRows(current => current.map((row, position) => position === index ? { ...row, [field]: value } : row));
    setRowErrors(current => ({ ...current, [index]: { ...current[index], [field]: undefined } }));
  };

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    setCommonError('');
    setRowErrors({});
    try {
      const { data } = await candidaturesAPI.prepareEmails({ ...common, emails: rows });
      onSuccess(data.emails);
    } catch (error) {
      const payload = error?.response?.data;
      if (Array.isArray(payload?.row_errors)) {
        setRowErrors(Object.fromEntries(payload.row_errors.map(row => [row.index, row.errors])));
        setCommonError('Aucun brouillon cree. Corrigez les candidatures signalees.');
      } else if (payload?.common_errors) {
        setCommonError(messages(payload.common_errors));
      } else if (error?.response?.status >= 500) {
        setCommonError(`Erreur du serveur (HTTP ${error.response.status}). Vérifiez les brouillons existants avant de réessayer pour éviter les doublons. Consultez le terminal du backend et les migrations.`);
      } else {
        setCommonError(extraireMessageErreur(error, 'Impossible de preparer les brouillons.'));
      }
    } finally {
      setBusy(false);
    }
  };

  return <Dialog open onClose={busy ? undefined : onClose} aria-labelledby="bulk-email-title" fullWidth maxWidth="md">
    <DialogTitle id="bulk-email-title">Preparer les emails</DialogTitle>
    <DialogContent>
      <Typography sx={{ mb: 2 }}>
        Un brouillon distinct sera cree pour chaque candidature. Aucun email ne sera envoye.
      </Typography>
      {commonError && <Alert severity="error" sx={{ mb: 2 }}>{commonError}</Alert>}
      <Grid container spacing={2} sx={{ pt: 1, mb: 3 }}>
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth required label="Formation" value={common.formation} onChange={event => setCommon(current => ({ ...current, formation: event.target.value }))} disabled={busy} /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth required type="url" label="Portfolio" value={common.portfolio_url} onChange={event => setCommon(current => ({ ...current, portfolio_url: event.target.value }))} disabled={busy} /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth required type="url" label="GitHub" value={common.github_url} onChange={event => setCommon(current => ({ ...current, github_url: event.target.value }))} disabled={busy} /></Grid>
      </Grid>
      {candidatures.map((candidature, index) => <Box component="section" aria-label={candidature.entreprise || candidature.titre} key={candidature.id} sx={{ borderTop: 1, borderColor: 'divider', py: 2 }}>
        <Typography component="h3" variant="subtitle1">{candidature.entreprise || candidature.titre}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{candidature.titre}</Typography>
        {(rowErrors[index]?.candidature_id || rowErrors[index]?.non_field_errors) && <Alert severity="error" sx={{ mb: 1 }}>{messages(rowErrors[index])}</Alert>}
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth required type="email" label={`Destinataire - ${candidature.entreprise || candidature.titre}`} value={rows[index].recipient_email} onChange={event => updateRow(index, 'recipient_email', event.target.value)} disabled={busy} error={Boolean(fieldMessage(rowErrors[index], 'recipient_email'))} helperText={fieldMessage(rowErrors[index], 'recipient_email')} /></Grid>
          <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Civilite" value={rows[index].civilite} onChange={event => updateRow(index, 'civilite', event.target.value)} disabled={busy} error={Boolean(fieldMessage(rowErrors[index], 'civilite'))} helperText={fieldMessage(rowErrors[index], 'civilite')} /></Grid>
          <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Prenom du contact" value={rows[index].prenom_contact} onChange={event => updateRow(index, 'prenom_contact', event.target.value)} disabled={busy} error={Boolean(fieldMessage(rowErrors[index], 'prenom_contact'))} helperText={fieldMessage(rowErrors[index], 'prenom_contact')} /></Grid>
          <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Nom du contact" value={rows[index].nom_contact} onChange={event => updateRow(index, 'nom_contact', event.target.value)} disabled={busy} error={Boolean(fieldMessage(rowErrors[index], 'nom_contact'))} helperText={fieldMessage(rowErrors[index], 'nom_contact')} /></Grid>
        </Grid>
      </Box>)}
    </DialogContent>
    <DialogActions>
      <Button onClick={onClose} disabled={busy}>Annuler</Button>
      <Button variant="contained" onClick={submit} disabled={busy}>{busy ? 'Preparation...' : 'Creer les brouillons'}</Button>
    </DialogActions>
  </Dialog>;
}
