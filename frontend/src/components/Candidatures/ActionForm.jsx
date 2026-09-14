import React, { useEffect, useRef, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField } from '@mui/material';
import { Save } from '@mui/icons-material';
import { format, isValid, parseISO } from 'date-fns';
import { extraireMessageErreur } from '../../services/errors';
import { TYPES_ACTION } from './options';

function localDateTime(value) {
  const parsed = value ? parseISO(value) : new Date();
  return isValid(parsed) ? format(parsed, "yyyy-MM-dd'T'HH:mm") : '';
}

export default function ActionForm({ open, action, onClose, onSubmit }) {
  const [form, setForm] = useState({ type_action: 'note', date_action: localDateTime(), commentaire: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submitting = useRef(false);

  useEffect(() => {
    if (open) {
      setForm({
        type_action: action?.type_action || 'note',
        date_action: localDateTime(action?.date_action),
        commentaire: action?.commentaire || '',
      });
      setError('');
    }
  }, [open, action]);

  const submit = async event => {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setSaving(true);
    setError('');
    try {
      await onSubmit(form);
      onClose();
    } catch (failure) {
      setError(extraireMessageErreur(failure, "Impossible d'enregistrer cette action."));
    } finally {
      submitting.current = false;
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => { if (!submitting.current) onClose(); }} fullWidth maxWidth="sm" aria-labelledby="action-form-title">
      <form onSubmit={submit}>
        <DialogTitle id="action-form-title">{action ? "Modifier l'action" : 'Ajouter une action'}</DialogTitle>
        <DialogContent dividers sx={{ display: 'grid', gap: 2 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField select required size="small" label="Type d'action" value={form.type_action} disabled={saving}
            onChange={event => setForm(current => ({ ...current, type_action: event.target.value }))}>
            {Object.entries(TYPES_ACTION).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
          </TextField>
          <TextField required size="small" type="datetime-local" label="Date de l'action" value={form.date_action} disabled={saving}
            onChange={event => setForm(current => ({ ...current, date_action: event.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }} />
          <TextField size="small" multiline minRows={3} label="Commentaire" value={form.commentaire} disabled={saving}
            onChange={event => setForm(current => ({ ...current, commentaire: event.target.value }))} />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={onClose} disabled={saving}>Annuler</Button>
          <Button type="submit" variant="contained" startIcon={<Save />} disabled={saving}>{saving ? 'Enregistrement...' : 'Enregistrer'}</Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

