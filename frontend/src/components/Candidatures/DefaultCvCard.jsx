import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, CardContent, Stack, Typography } from '@mui/material';
import { candidaturesAPI } from '../../services/api';
import { extraireMessageErreur } from '../../services/errors';

const MAX_CV_BYTES = 5 * 1024 * 1024;

export default function DefaultCvCard() {
  const [filename, setFilename] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    candidaturesAPI.getDefaultCv()
      .then(response => { if (active) setFilename(response.data.filename); })
      .catch(failure => {
        if (active) setError(extraireMessageErreur(failure, 'Impossible de charger le CV par défaut.'));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const selectFile = event => {
    const file = event.target.files?.[0] || null;
    setError('');
    setSelected(null);
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf') || file.size > MAX_CV_BYTES) {
      setError('Sélectionnez un fichier PDF de 5 Mio maximum.');
      return;
    }
    setSelected(file);
  };

  const upload = async () => {
    if (!selected || busy) return;
    setBusy(true);
    setError('');
    try {
      const response = await candidaturesAPI.replaceDefaultCv(selected);
      setFilename(response.data.filename);
      setSelected(null);
    } catch (failure) {
      setError(failure?.response?.status === 405
        ? 'Le backend lancé ne prend pas en charge l’upload du CV. Lancez le backend de cette version de l’application sur le port 8000.'
        : extraireMessageErreur(failure, 'Impossible de téléverser le CV.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card component="section" aria-label="CV par défaut">
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="h6">CV par défaut</Typography>
          {loading ? <Typography>Chargement du CV...</Typography> : (
            <Typography>{filename || 'Aucun CV par défaut.'}</Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            Un seul CV est utilisé pour les emails de candidature en V1. Fichier PDF, 5 Mio maximum.
          </Typography>
          <label htmlFor="default-cv-file">Choisir un CV PDF</label>
          <input id="default-cv-file" type="file" accept=".pdf,application/pdf" onChange={selectFile} disabled={busy} />
          {error && <Alert severity="error">{error}</Alert>}
          <Button variant="contained" onClick={upload} disabled={!selected || busy} sx={{ alignSelf: 'flex-start' }}>
            {busy ? 'Téléversement...' : filename ? 'Remplacer le CV' : 'Ajouter le CV'}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
