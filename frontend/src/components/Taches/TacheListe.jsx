import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  Paper,
  CircularProgress,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import TacheCard from './TacheCard';
import TacheForm from './TacheForm';
import { tachesAPI, categoriesAPI } from '../../services/api';

const TacheListe = () => {
  const [taches, setTaches] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openForm, setOpenForm] = useState(false);
  const [tacheSelectionnee, setTacheSelectionnee] = useState(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    chargerDonnees();
  }, []);

  const chargerDonnees = async () => {
    try {
      const [tachesRes, categoriesRes] = await Promise.all([
        tachesAPI.getAll(),
        categoriesAPI.getAll(),
      ]);
      setTaches(tachesRes.data);
      setCategories(categoriesRes.data);
    } catch (error) {
      console.error('Erreur de chargement:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (data) => {
    try {
      await tachesAPI.create(data);
      chargerDonnees();
    } catch (error) {
      console.error('Erreur de création:', error);
    }
  };

  const handleUpdate = async (id, data) => {
    try {
      await tachesAPI.update(id, data);
      chargerDonnees();
    } catch (error) {
      console.error('Erreur de mise à jour:', error);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cette tâche ?')) {
      try {
        await tachesAPI.delete(id);
        chargerDonnees();
      } catch (error) {
        console.error('Erreur de suppression:', error);
      }
    }
  };

  const handleEdit = (tache) => {
    setTacheSelectionnee(tache);
    setOpenForm(true);
  };

  const handleCloseForm = () => {
    setOpenForm(false);
    setTacheSelectionnee(null);
  };

  const filtrerTaches = () => {
    switch (tabValue) {
      case 0:
        return taches.filter(t => !t.completee);
      case 1:
        return taches.filter(t => t.completee);
      case 2:
        return taches;
      default:
        return taches;
    }
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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">
          Mes Tâches
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenForm(true)}
        >
          Nouvelle tâche
        </Button>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label={`En cours (${taches.filter(t => !t.completee).length})`} />
          <Tab label={`Terminées (${taches.filter(t => t.completee).length})`} />
          <Tab label={`Toutes (${taches.length})`} />
        </Tabs>
      </Paper>

      {filtrerTaches().length === 0 ? (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" color="text.secondary">
            Aucune tâche pour le moment
          </Typography>
        </Box>
      ) : (
        filtrerTaches().map((tache) => (
          <TacheCard
            key={tache.id}
            tache={tache}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
            onEdit={handleEdit}
          />
        ))
      )}

      <TacheForm
        open={openForm}
        onClose={handleCloseForm}
        onSubmit={tacheSelectionnee ? 
          (data) => handleUpdate(tacheSelectionnee.id, data) : 
          handleCreate
        }
        tache={tacheSelectionnee}
        categories={categories}
      />
    </Box>
  );
};

export default TacheListe;