import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle,
  Grid, Stack, TextField, Typography,
} from '@mui/material';

const editableFields = ['recipient_email', 'subject', 'body'];

export default function EmailBrouillonDialog({ open, draft, cvName, busy = false, error = '', onSave, onCancel, onSend }) {
  const [values, setValues] = useState({ recipient_email: '', subject: '', body: '' });

  useEffect(() => {
    setValues({
      recipient_email: draft?.recipient_email || '',
      subject: draft?.subject || '',
      body: draft?.body || '',
    });
  }, [draft]);

  const change = field => event => setValues(current => ({ ...current, [field]: event.target.value }));
  const payload = () => Object.fromEntries(editableFields.map(field => [field, values[field]]));
  const valid = values.recipient_email.trim() && values.subject.trim() && values.body.trim();

  return (
    <Dialog open={Boolean(open && draft)} fullWidth maxWidth="md" aria-labelledby="email-draft-title">
      <DialogTitle id="email-draft-title">Prévisualiser le brouillon</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <Grid container spacing={2}>
            <Grid size={12}>
              <TextField fullWidth required type="email" label="Destinataire" value={values.recipient_email} onChange={change('recipient_email')} disabled={busy} />
            </Grid>
            <Grid size={12}>
              <TextField fullWidth required label="Objet" value={values.subject} onChange={change('subject')} disabled={busy} />
            </Grid>
            <Grid size={12}>
              <TextField fullWidth required multiline minRows={8} label="Message" value={values.body} onChange={change('body')} disabled={busy} />
            </Grid>
          </Grid>
          <Box>
            <Typography variant="subtitle2">Pièce jointe prévue</Typography>
            <Typography color="text.secondary">{cvName || 'Aucun CV par défaut configuré'}</Typography>
            <Typography variant="caption" color="text.secondary">« Envoyer » prépare l’envoi sans transmettre d’email.</Typography>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={() => onCancel(draft.id)} disabled={busy}>Annuler</Button>
        <Button onClick={() => onSave(draft.id, payload())} disabled={busy || !valid}>Enregistrer</Button>
        <Button variant="contained" onClick={() => onSend(draft.id, payload())} disabled={busy || !valid || !cvName}>Envoyer</Button>
      </DialogActions>
    </Dialog>
  );
}
