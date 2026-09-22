import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, CardContent, CircularProgress, Stack, Typography } from '@mui/material';
import { gmailAPI } from '../../services/api';
import { extraireMessageErreur } from '../../services/errors';

export default function GmailConnectionCard({ navigateToOAuth = url => window.location.assign(url) }) {
  const [status, setStatus] = useState('loading');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(() => new URLSearchParams(window.location.search).get('gmail') === 'error'
    ? 'La connexion Gmail n’a pas abouti. Réessayez.' : '');

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await gmailAPI.getStatus();
        if (!active) return;
        setStatus(response.data.status);
        if (response.data.status === 'connected') {
          try {
            const verification = await gmailAPI.verify();
            if (active) setStatus(verification.data.status);
          } catch (failure) {
            if (active) setError(extraireMessageErreur(failure, 'Verification Gmail momentanement indisponible.'));
          }
        }
      } catch (failure) {
        if (active) {
          setStatus('disconnected');
          setError(extraireMessageErreur(failure, 'Impossible de lire la connexion Gmail.'));
        }
      }
    };
    load();
    return () => { active = false; };
  }, []);

  const connect = async () => {
    setBusy(true);
    setError('');
    try {
      const response = await gmailAPI.connect();
      const url = new URL(response.data.authorization_url);
      if (url.protocol !== 'https:' || url.hostname !== 'accounts.google.com') {
        throw new Error('invalid_oauth_url');
      }
      navigateToOAuth(url.toString());
    } catch (failure) {
      setError(extraireMessageErreur(failure, 'Impossible de démarrer la connexion Gmail.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card component="section" aria-label="Compte Gmail">
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="h6">Compte Gmail</Typography>
          {status === 'loading' && <CircularProgress size={24} aria-label="Chargement du compte Gmail" />}
          {status === 'connected' && <Alert severity="success">Compte Gmail connecté</Alert>}
          {status === 'reconnect_required' && <Alert severity="warning">Reconnectez votre compte Gmail pour continuer.</Alert>}
          {status === 'disconnected' && <Typography color="text.secondary">Aucun compte Gmail connecté.</Typography>}
          {error && <Alert severity="error">{error}</Alert>}
          {(status === 'disconnected' || status === 'reconnect_required') && (
            <Button variant="contained" onClick={connect} disabled={busy} sx={{ alignSelf: 'flex-start' }}>
              {status === 'reconnect_required' ? 'Reconnecter mon compte Gmail' : 'Connecter mon compte Gmail'}
            </Button>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
