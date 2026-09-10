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
  const [periode, setPeriode] = useState('toutes');

  useEffect(() => {
    chargerDonnees();
  }, [periode]);

  const chargerDonnees = async () => {
    const chargerTaches = {
      toutes: tachesAPI.getAll,
      aujourdHui: tachesAPI.getAujourdhui,
      cetteSemaine: tachesAPI.getCetteSemaine,
    }[periode];

    setLoading(true);
    try {
      const [tachesRes, categoriesRes] = await Promise.all([
        chargerTaches(),
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
    await tachesAPI.create(data);
    await chargerDonnees();
  };

  const handleUpdate = async (id, data) => {
    await tachesAPI.update(id, data);
    await chargerDonnees();
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

      <Box display="flex" gap={1} mb={2}>
        <Button
          variant={periode === 'toutes' ? 'contained' : 'outlined'}
          onClick={() => setPeriode('toutes')}
        >
          Toutes les tâches
        </Button>
        <Button
          variant={periode === 'aujourdHui' ? 'contained' : 'outlined'}
          onClick={() => setPeriode('aujourdHui')}
        >
          Aujourd'hui
        </Button>
        <Button
          variant={periode === 'cetteSemaine' ? 'contained' : 'outlined'}
          onClick={() => setPeriode('cetteSemaine')}
        >
          Cette semaine
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
