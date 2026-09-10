import React, { useState } from 'react';
import { Alert, Box, Button, Container, Paper, TextField, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import { extraireMessageErreur } from '../services/errors';

const MotDePasseOublie = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const response = await authAPI.requestPasswordReset(email);
      setMessage(response.data.message);
    } catch (requestError) {
      setError(extraireMessageErreur(requestError, 'Impossible d’envoyer le lien de réinitialisation.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" bgcolor="primary.lighter">
      <Container maxWidth="sm">
        <Paper elevation={4} sx={{ p: { xs: 3, sm: 4 } }}>
          <Typography variant="h4" fontWeight="bold" gutterBottom>Mot de passe oublié</Typography>
          <Typography color="text.secondary" mb={3}>
            Saisissez votre adresse e-mail pour recevoir un lien de réinitialisation.
          </Typography>
          <form onSubmit={handleSubmit}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
            <TextField
              fullWidth
              required
              autoComplete="email"
              label="E-mail"
              margin="normal"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Button fullWidth disabled={loading} size="large" sx={{ mt: 3 }} type="submit" variant="contained">
              {loading ? 'Envoi...' : 'Envoyer le lien'}
            </Button>
          </form>
          <Box mt={3} textAlign="center">
            <Button onClick={() => navigate('/login')}>Retour à la connexion</Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default MotDePasseOublie;
