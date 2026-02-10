import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  Card,
  CardContent,
  Avatar,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Save as SaveIcon,
//   Person,
  Notifications,
  Palette,
  AccessTime,
} from '@mui/icons-material';
import { preferencesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const Parametres = () => {
  const { user } = useAuth();
  const [preferences, setPreferences] = useState({
    heure_productive_debut: '09:00',
    heure_productive_fin: '17:00',
    theme: 'clair',
    notifications_actives: true,
  });
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    chargerPreferences();
  }, []);

  const chargerPreferences = async () => {
    try {
      const response = await preferencesAPI.get();
      if (response.data.length > 0) {
        setPreferences(response.data[0]);
      }
    } catch (error) {
      console.error('Erreur chargement préférences:', error);
    }
  };

  const handleChange = (field) => (event) => {
    const value = event.target.type === 'checkbox' 
      ? event.target.checked 
      : event.target.value;
    setPreferences({ ...preferences, [field]: value });
  };

  const handleSave = async () => {
    try {
      if (preferences.id) {
        await preferencesAPI.update(preferences.id, preferences);
      } else {
        await preferencesAPI.create(preferences);
      }
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (error) {
      console.error('Erreur sauvegarde:', error);
    }
  };

  return (
    <Box>
      {/* En-tête */}
      <Box mb={4}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          ⚙️ Paramètres
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Personnalisez votre expérience
        </Typography>
      </Box>

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Paramètres sauvegardés avec succès !
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Profil */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box textAlign="center">
                <Avatar
                  sx={{
                    width: 100,
                    height: 100,
                    bgcolor: 'primary.main',
                    fontSize: '3rem',
                    margin: '0 auto',
                    mb: 2,
                  }}
                >
                  {user?.username?.charAt(0).toUpperCase()}
                </Avatar>
                <Typography variant="h6" fontWeight="bold">
                  {user?.username}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {user?.email}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Préférences */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            {/* Heures productives */}
            <Box mb={4}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <AccessTime color="primary" />
                <Typography variant="h6" fontWeight="bold">
                  Heures productives
                </Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Heure de début"
                    type="time"
                    value={preferences.heure_productive_debut}
                    onChange={handleChange('heure_productive_debut')}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Heure de fin"
                    type="time"
                    value={preferences.heure_productive_fin}
                    onChange={handleChange('heure_productive_fin')}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              </Grid>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Définissez vos heures de travail préférées pour des recommandations personnalisées
              </Typography>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Thème */}
            <Box mb={4}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Palette color="primary" />
                <Typography variant="h6" fontWeight="bold">
                  Apparence
                </Typography>
              </Box>
              <FormControl fullWidth>
                <InputLabel>Thème</InputLabel>
                <Select
                  value={preferences.theme}
                  onChange={handleChange('theme')}
                  label="Thème"
                >
                  <MenuItem value="clair">☀️ Clair</MenuItem>
                  <MenuItem value="sombre">🌙 Sombre</MenuItem>
                  <MenuItem value="auto">🔄 Automatique</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Notifications */}
            <Box mb={4}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <Notifications color="primary" />
                <Typography variant="h6" fontWeight="bold">
                  Notifications
                </Typography>
              </Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={preferences.notifications_actives}
                    onChange={handleChange('notifications_actives')}
                    color="primary"
                  />
                }
                label="Activer les notifications"
              />
              <Typography variant="caption" color="text.secondary" display="block">
                Recevez des rappels pour vos tâches importantes
              </Typography>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Bouton de sauvegarde */}
            <Box textAlign="right">
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                size="large"
              >
                Enregistrer les modifications
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Statistiques du compte */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              📈 Statistiques du compte
            </Typography>
            <Grid container spacing={2} mt={1}>
              <Grid item xs={12} sm={4}>
                <Box textAlign="center" p={2} bgcolor="primary.lighter" borderRadius={2}>
                  <Typography variant="h4" fontWeight="bold" color="primary">
                    {Math.floor(Math.random() * 50) + 20}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Jours d'utilisation
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box textAlign="center" p={2} bgcolor="success.lighter" borderRadius={2}>
                  <Typography variant="h4" fontWeight="bold" color="success.main">
                    {Math.floor(Math.random() * 100) + 50}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Tâches complétées
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Box textAlign="center" p={2} bgcolor="warning.lighter" borderRadius={2}>
                  <Typography variant="h4" fontWeight="bold" color="warning.main">
                    {Math.floor(Math.random() * 20) + 5}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Catégories créées
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Parametres;