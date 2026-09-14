import React, { useEffect, useRef, useState } from 'react';
import {
  Alert, Autocomplete, Box, Button, Checkbox, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControlLabel, Grid, MenuItem, TextField,
  Typography, useMediaQuery, useTheme,
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { extraireMessageErreur } from '../../services/errors';
import { FORM_DEFAULTS, MODES_TRAVAIL, SOURCES_CANAL, STATUTS, TYPES_POSTE } from './options';

export default function CandidatureForm({ open, onClose, onSubmit, candidature, message = '' }) {
  const [form, setForm] = useState(FORM_DEFAULTS);
  const [tagInput, setTagInput] = useState('');
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const submitting = useRef(false);
  const fullScreen = useMediaQuery(useTheme().breakpoints.down('sm'));

  useEffect(() => {
    if (open) {
      setForm(Object.fromEntries(Object.entries(FORM_DEFAULTS).map(([key, fallback]) => [key, candidature?.[key] ?? fallback])));
      setTagInput('');
      setErrors({});
      setError('');
    }
  }, [open, candidature]);

  const change = key => event => {
    setForm(current => ({ ...current, [key]: event.target.value }));
    setErrors(current => ({ ...current, [key]: '' }));
  };

  const submit = async event => {
    event.preventDefault();
    if (submitting.current) return;
    const tags = [...new Set([...form.tags, tagInput].map(tag => tag.trim()).filter(Boolean))];
    const validation = {};
    if (!form.titre.trim()) validation.titre = 'Le titre est requis.';
    try {
      const url = new URL(form.url);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error();
    } catch { validation.url = 'Une URL HTTP(S) valide sans identifiants est requise.'; }
    if (tags.some(tag => tag.length > 50)) validation.tags = 'Chaque tag est limite a 50 caracteres.';
    setErrors(validation);
    setError('');
    if (Object.keys(validation).length) return;
    submitting.current = true;
    setSaving(true);
    try {
      await onSubmit({ ...form, titre: form.titre.trim(), url: form.url.trim(), tags,
        date_limite: form.date_limite || null, date_relance: form.date_relance || null });
      onClose();
    } catch (failure) {
      const data = failure?.response?.data;
      setErrors(Object.fromEntries(Object.keys(FORM_DEFAULTS).map(key => [key,
        Array.isArray(data?.[key]) ? data[key].join(' ') : typeof data?.[key] === 'string' ? data[key] : '',
      ])));
      setError(extraireMessageErreur(failure, "Impossible d'enregistrer la candidature."));
    } finally {
      submitting.current = false;
      setSaving(false);
    }
  };

  const field = (key, label, props = {}) => (
    <TextField fullWidth size="small" label={label} value={form[key]} onChange={change(key)}
      disabled={saving} error={Boolean(errors[key])} helperText={errors[key]} {...props} />
  );
  const select = (key, label, options) => field(key, label, {
    select: true,
    children: Object.entries(options).map(([value, option]) => <MenuItem key={value} value={value}>{option.label || option}</MenuItem>),
  });
  const readonly = (label, value) => <TextField fullWidth size="small" label={label} value={value ?? ''} slotProps={{ input: { readOnly: true } }} />;

  return (
    <Dialog open={open} onClose={() => { if (!submitting.current) onClose(); }} fullWidth maxWidth="md"
      fullScreen={fullScreen} aria-labelledby="candidature-form-title">
      <Box component="form" onSubmit={submit} sx={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <DialogTitle id="candidature-form-title">{candidature?.id ? 'Modifier la candidature' : 'Nouvelle candidature'}</DialogTitle>
        <DialogContent dividers>
          {message && <Alert severity="info" sx={{ mb: 2 }}>{message}</Alert>}
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Grid container spacing={2}>
            <Grid size={12}>{field('url', "URL de l'offre", { required: true, type: 'url', slotProps: { htmlInput: { maxLength: 1000 } } })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{field('titre', 'Titre', { required: true, slotProps: { htmlInput: { maxLength: 255 } } })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{field('entreprise', 'Entreprise', { slotProps: { htmlInput: { maxLength: 255 } } })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{field('lieu', 'Lieu', { slotProps: { htmlInput: { maxLength: 255 } } })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{select('mode_travail', 'Mode de travail', MODES_TRAVAIL)}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{select('type_poste', 'Type de poste', TYPES_POSTE)}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{select('statut', 'Statut', STATUTS)}</Grid>
            <Grid size={12}>{field('description', 'Description', { multiline: true, minRows: 4, maxRows: 10 })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{select('source_canal', 'Source du canal', SOURCES_CANAL)}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{field('cv_utilise', 'CV utilise', { slotProps: { htmlInput: { maxLength: 255 } } })}</Grid>
            <Grid size={12}>
              <Autocomplete multiple freeSolo options={[]} value={form.tags} inputValue={tagInput} disabled={saving}
                onChange={(_, tags) => setForm(current => ({ ...current, tags }))}
                onInputChange={(_, value) => setTagInput(value)}
                renderInput={params => <TextField {...params} label="Tags" size="small" error={Boolean(errors.tags)} helperText={errors.tags} />}
                sx={{ '& .MuiChip-root': { maxWidth: '100%' }, minWidth: 0 }} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{field('date_limite', 'Date limite', { type: 'date', slotProps: { inputLabel: { shrink: true } } })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{field('date_relance', 'Date de relance', { type: 'date', slotProps: { inputLabel: { shrink: true } } })}</Grid>
            <Grid size={12}>
              <FormControlLabel label="Favori" control={<Checkbox checked={form.favori} disabled={saving} onChange={event => setForm(current => ({ ...current, favori: event.target.checked }))} />} />
              <FormControlLabel label="Archivee" control={<Checkbox checked={form.archive} disabled={saving} onChange={event => setForm(current => ({ ...current, archive: event.target.checked }))} />} />
            </Grid>
            <Grid size={12}>{field('notes', 'Notes', { multiline: true, minRows: 2, maxRows: 8 })}</Grid>
            <Grid size={12}><Typography variant="subtitle2">Informations de suivi</Typography></Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{readonly('Source extraction', form.source_extraction)}</Grid>
            {candidature?.id && <>
              <Grid size={{ xs: 12, sm: 6 }}>{readonly('Identifiant', candidature.id)}</Grid>
              <Grid size={{ xs: 12, sm: 6 }}>{readonly('Utilisateur', candidature.utilisateur)}</Grid>
              <Grid size={{ xs: 12, sm: 6 }}>{readonly("Date d'ajout", candidature.date_ajout ? new Date(candidature.date_ajout).toLocaleString('fr-FR') : '')}</Grid>
              <Grid size={{ xs: 12, sm: 6 }}>{readonly('Derniere modification', candidature.date_modification ? new Date(candidature.date_modification).toLocaleString('fr-FR') : '')}</Grid>
            </>}
          </Grid>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={onClose} disabled={saving}>Annuler</Button>
          <Button type="submit" variant="contained" startIcon={<Save />} disabled={saving}>{saving ? 'Enregistrement...' : 'Enregistrer'}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}
