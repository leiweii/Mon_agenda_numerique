import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Box,
  Typography,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { fr } from 'date-fns/locale';

const EMOJIS_POPULAIRES = ['📝', '💼', '🏠', '🎯', '💪', '📚', '🛒', '✈️', '🎨', '💻'];
const COULEURS_POPULAIRES = [
  '#3498db', '#e74c3c', '#2ecc71', '#f39c12', 
  '#9b59b6', '#1abc9c', '#34495e', '#e91e63'
];

const TacheForm = ({ open, onClose, onSubmit, tache, categories }) => {
  const [formData, setFormData] = useState({
    titre: '',
    description: '',
    date_echeance: new Date(),
    priorite: 2,
    couleur: '#3498db',
    emoji: '📝',
    categorie: '',
  });

  useEffect(() => {
    if (tache) {
      setFormData({
        ...tache,
        date_echeance: new Date(tache.date_echeance),
      });
    } else {
      setFormData({
        titre: '',
        description: '',
        date_echeance: new Date(),
        priorite: 2,
        couleur: '#3498db',
        emoji: '📝',
        categorie: '',
      });
    }
  }, [tache, open]);

  const handleChange = (field) => (event) => {
    setFormData({ ...formData, [field]: event.target.value });
  };

  const handleDateChange = (newDate) => {
    setFormData({ ...formData, date_echeance: newDate });
  };

  const handleSubmit = () => {
    onSubmit(formData);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {tache ? 'Modifier la tâche' : 'Nouvelle tâche'}
      </DialogTitle>
      
      <DialogContent>
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {/* Titre */}
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Titre"
              value={formData.titre}
              onChange={handleChange('titre')}
              required
            />
          </Grid>

          {/* Description */}
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Description"
              multiline
              rows={3}
              value={formData.description}
              onChange={handleChange('description')}
            />
          </Grid>

          {/* Date et heure */}
          <Grid item xs={12} md={6}>
            <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={fr}>
              <DateTimePicker
                label="Date d'échéance"
                value={formData.date_echeance}
                onChange={handleDateChange}
                renderInput={(params) => <TextField {...params} fullWidth />}
              />
            </LocalizationProvider>
          </Grid>

          {/* Priorité */}
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Priorité</InputLabel>
              <Select
                value={formData.priorite}
                onChange={handleChange('priorite')}
                label="Priorité"
              >
                <MenuItem value={1}>🟢 Basse</MenuItem>
                <MenuItem value={2}>🔵 Moyenne</MenuItem>
                <MenuItem value={3}>🟠 Haute</MenuItem>
                <MenuItem value={4}>🔴 Urgente</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Catégorie */}
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Catégorie</InputLabel>
              <Select
                value={formData.categorie}
                onChange={handleChange('categorie')}
                label="Catégorie"
              >
                <MenuItem value="">Aucune</MenuItem>
                {categories.map((cat) => (
                  <MenuItem key={cat.id} value={cat.id}>
                    {cat.emoji} {cat.nom}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Emoji */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Emoji
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {EMOJIS_POPULAIRES.map((emoji) => (
                <Button
                  key={emoji}
                  variant={formData.emoji === emoji ? 'contained' : 'outlined'}
                  onClick={() => setFormData({ ...formData, emoji })}
                  sx={{ minWidth: 50, fontSize: 24 }}
                >
                  {emoji}
                </Button>
              ))}
            </Box>
          </Grid>

          {/* Couleur */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Couleur
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {COULEURS_POPULAIRES.map((couleur) => (
                <Button
                  key={couleur}
                  variant={formData.couleur === couleur ? 'contained' : 'outlined'}
                  onClick={() => setFormData({ ...formData, couleur })}
                  sx={{
                    minWidth: 50,
                    height: 50,
                    bgcolor: couleur,
                    '&:hover': { bgcolor: couleur, opacity: 0.8 },
                    border: formData.couleur === couleur ? '3px solid #000' : 'none',
                  }}
                />
              ))}
            </Box>
          </Grid>
        </Grid>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Annuler</Button>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          {tache ? 'Modifier' : 'Créer'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TacheForm;