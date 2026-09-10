import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  IconButton,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import CategorieForm from './CategorieForm';
import { categoriesAPI, tachesAPI } from '../../services/api';

const CategorieListe = () => {
  const [categories, setCategories] = useState([]);
  const [taches, setTaches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openForm, setOpenForm] = useState(false);
  const [categorieSelectionnee, setCategorieSelectionnee] = useState(null);

  useEffect(() => {
    chargerDonnees();
  }, []);

  const chargerDonnees = async () => {
    try {
      const [categoriesRes, tachesRes] = await Promise.all([
        categoriesAPI.getAll(),
        tachesAPI.getAll(),
      ]);
      setCategories(categoriesRes.data);
      setTaches(tachesRes.data);
    } catch (error) {
      console.error('Erreur de chargement:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (data) => {
    await categoriesAPI.create(data);
    await chargerDonnees();
  };

  const handleUpdate = async (data) => {
    await categoriesAPI.update(categorieSelectionnee.id, data);
    await chargerDonnees();
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cette catégorie ?')) {
      try {
        await categoriesAPI.delete(id);
        chargerDonnees();
      } catch (error) {
        console.error('Erreur de suppression:', error);
      }
    }
  };

  const handleEdit = (categorie) => {
    setCategorieSelectionnee(categorie);
    setOpenForm(true);
  };

  const handleCloseForm = () => {
    setOpenForm(false);
    setCategorieSelectionnee(null);
  };

  const compterTachesParCategorie = (categorieId) => {
    return taches.filter(t => t.categorie === categorieId).length;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* En-tête */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            📁 Mes Catégories
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Organisez vos tâches par catégorie
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenForm(true)}
        >
          Nouvelle catégorie
        </Button>
      </Box>

      {/* Liste des catégories */}
      {categories.length === 0 ? (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Aucune catégorie créée
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={3}>
            Commencez par créer votre première catégorie
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenForm(true)}
          >
            Créer une catégorie
          </Button>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {categories.map((categorie) => (
            <Grid item xs={12} sm={6} md={4} key={categorie.id}>
              <Card
                sx={{
                  height: '100%',
                  borderLeft: `4px solid ${categorie.couleur}`,
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="h4">{categorie.emoji}</Typography>
                      <Typography variant="h6" fontWeight="bold">
                        {categorie.nom}
                      </Typography>
                    </Box>
                    <Box>
                      <IconButton 
                        size="small" 
                        onClick={() => handleEdit(categorie)}
                        color="primary"
                        aria-label={`Modifier ${categorie.nom}`}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton 
                        size="small" 
                        onClick={() => handleDelete(categorie.id)}
                        color="error"
                        aria-label={`Supprimer ${categorie.nom}`}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </Box>

                  <Box
                    p={1}
                    borderRadius={1}
                    sx={{ bgcolor: `${categorie.couleur}20` }}
                  >
                    <Chip
                      label={`${compterTachesParCategorie(categorie.id)} tâche${compterTachesParCategorie(categorie.id) > 1 ? 's' : ''}`}
                      size="small"
                      sx={{
                        bgcolor: categorie.couleur,
                        color: 'white',
                        fontWeight: 'bold',
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Formulaire */}
      <CategorieForm
        open={openForm}
        onClose={handleCloseForm}
        onSubmit={categorieSelectionnee ? handleUpdate : handleCreate}
        categorie={categorieSelectionnee}
      />
    </Box>
  );
};

export default CategorieListe;
