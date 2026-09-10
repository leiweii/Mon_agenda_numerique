import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { extraireMessageErreur } from '../services/errors';

const Inscription = () => {
  const [form, setForm] = useState({
    email: '',
    password: '',
    confirmation: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (field) => (event) => {
    setForm({ ...form, [field]: event.target.value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (form.password !== form.confirmation) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setLoading(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        password_confirmation: form.confirmation,
      });
      navigate('/dashboard');
    } catch (requestError) {
      setError(extraireMessageErreur(requestError, 'Impossible de créer votre compte.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" bgcolor="primary.lighter">
      <Container maxWidth="sm">
        <Paper elevation={4} sx={{ p: { xs: 3, sm: 4 } }}>
          <Box mb={3} textAlign="center">
            <Typography variant="h4" fontWeight="bold" gutterBottom>
              Créer un compte
            </Typography>
            <Typography color="text.secondary">
              Commencez à organiser vos tâches.
            </Typography>
          </Box>

          <form onSubmit={handleSubmit}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <TextField
              fullWidth
              required
              autoComplete="email"
              label="E-mail"
              margin="normal"
              type="email"
              value={form.email}
              onChange={handleChange('email')}
            />
            <TextField
              fullWidth
              required
              autoComplete="new-password"
              label="Mot de passe"
              margin="normal"
              type="password"
              value={form.password}
              onChange={handleChange('password')}
            />
            <TextField
              fullWidth
              required
              autoComplete="new-password"
              label="Confirmer le mot de passe"
              margin="normal"
              type="password"
              value={form.confirmation}
              onChange={handleChange('confirmation')}
            />
            <Button
              fullWidth
              disabled={loading}
              size="large"
              sx={{ mt: 3 }}
              type="submit"
              variant="contained"
            >
              {loading ? 'Création...' : 'Créer mon compte'}
            </Button>
          </form>

          <Box mt={3} textAlign="center">
            <Button onClick={() => navigate('/login')}>Déjà un compte ? Se connecter</Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default Inscription;
