import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid,
  Box,
  Typography,
} from '@mui/material';

const EMOJIS_CATEGORIES = [
  '💼', '🏠', '🎯', '💪', '📚', '🛒', 
  '✈️', '🎨', '💻', '🏃', '🍔', '🎵',
  '📱', '🎮', '🏥', '💰', '🚗', '📧'
];

const COULEURS_CATEGORIES = [
  '#3498db', '#e74c3c', '#2ecc71', '#f39c12', 
  '#9b59b6', '#1abc9c', '#34495e', '#e91e63',
  '#ff5722', '#009688', '#795548', '#607d8b'
];

const CategorieForm = ({ open, onClose, onSubmit, categorie }) => {
  const [formData, setFormData] = useState({
    nom: '',
    couleur: '#3498db',
    emoji: '📁',
  });

  useEffect(() => {
    if (categorie) {
      setFormData(categorie);
    } else {
      setFormData({
        nom: '',
        couleur: '#3498db',
        emoji: '📁',
      });
    }
  }, [categorie, open]);

  const handleChange = (field) => (event) => {
    setFormData({ ...formData, [field]: event.target.value });
  };

  const handleSubmit = () => {
    onSubmit(formData);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {categorie ? 'Modifier la catégorie' : 'Nouvelle catégorie'}
      </DialogTitle>
      
      <DialogContent>
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {/* Nom */}
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Nom de la catégorie"
              value={formData.nom}
              onChange={handleChange('nom')}
              required
              placeholder="Ex: Travail, Personnel, Sport..."
            />
          </Grid>

          {/* Emoji */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Icône
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {EMOJIS_CATEGORIES.map((emoji) => (
                <Button
                  key={emoji}
                  variant={formData.emoji === emoji ? 'contained' : 'outlined'}
                  onClick={() => setFormData({ ...formData, emoji })}
                  sx={{ 
                    minWidth: 50, 
                    height: 50,
                    fontSize: 24,
                  }}
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
              {COULEURS_CATEGORIES.map((couleur) => (
                <Button
                  key={couleur}
                  variant={formData.couleur === couleur ? 'contained' : 'outlined'}
                  onClick={() => setFormData({ ...formData, couleur })}
                  sx={{
                    minWidth: 50,
                    height: 50,
                    bgcolor: couleur,
                    '&:hover': { 
                      bgcolor: couleur, 
                      opacity: 0.8 
                    },
                    border: formData.couleur === couleur ? '3px solid #000' : 'none',
                  }}
                />
              ))}
            </Box>
          </Grid>

          {/* Prévisualisation */}
          <Grid item xs={12}>
            <Box 
              p={2} 
              border="2px dashed #ddd" 
              borderRadius={2}
              textAlign="center"
            >
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Aperçu
              </Typography>
              <Box
                display="inline-flex"
                alignItems="center"
                gap={1}
                p={1.5}
                borderRadius={2}
                sx={{
                  bgcolor: formData.couleur,
                  color: 'white',
                }}
              >
                <Typography variant="h5">{formData.emoji}</Typography>
                <Typography variant="h6" fontWeight="bold">
                  {formData.nom || 'Nom de la catégorie'}
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Annuler</Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained" 
          color="primary"
          disabled={!formData.nom}
        >
          {categorie ? 'Modifier' : 'Créer'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CategorieForm;