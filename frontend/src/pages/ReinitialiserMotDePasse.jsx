import React, { useState } from 'react';
import { Alert, Box, Button, Container, Paper, TextField, Typography } from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import { authAPI } from '../services/api';
import { extraireMessageErreur } from '../services/errors';

const ReinitialiserMotDePasse = () => {
  const { uid, token } = useParams();
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');

    if (password !== confirmation) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setLoading(true);
    try {
      const response = await authAPI.resetPassword({
        uid,
        token,
        password,
        password_confirmation: confirmation,
      });
      setMessage(response.data.message);
    } catch (requestError) {
      setError(extraireMessageErreur(requestError, 'Impossible de réinitialiser le mot de passe.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" bgcolor="primary.lighter">
      <Container maxWidth="sm">
        <Paper elevation={4} sx={{ p: { xs: 3, sm: 4 } }}>
          <Typography variant="h4" fontWeight="bold" gutterBottom>Choisir un nouveau mot de passe</Typography>
          <form onSubmit={handleSubmit}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
            <TextField
              fullWidth
              required
              autoComplete="new-password"
              label="Nouveau mot de passe"
              margin="normal"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <TextField
              fullWidth
              required
              autoComplete="new-password"
              label="Confirmer le mot de passe"
              margin="normal"
              type="password"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
            <Button fullWidth disabled={loading} size="large" sx={{ mt: 3 }} type="submit" variant="contained">
              {loading ? 'Réinitialisation...' : 'Réinitialiser le mot de passe'}
            </Button>
          </form>
          {message && (
            <Box mt={3} textAlign="center">
              <Button onClick={() => navigate('/login')}>Se connecter</Button>
            </Box>
          )}
        </Paper>
      </Container>
    </Box>
  );
};

export default ReinitialiserMotDePasse;
