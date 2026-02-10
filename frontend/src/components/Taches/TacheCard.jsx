import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  IconButton,
  Chip,
  Box,
  Checkbox,
  Stack,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  CalendarToday,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';

const TacheCard = ({ tache, onUpdate, onDelete, onEdit }) => {
  const getPrioriteColor = (priorite) => {
    const colors = {
      1: '#95a5a6',
      2: '#3498db',
      3: '#f39c12',
      4: '#e74c3c',
    };
    return colors[priorite] || '#3498db';
  };

  const getPrioriteLabel = (priorite) => {
    const labels = {
      1: 'Basse',
      2: 'Moyenne',
      3: 'Haute',
      4: 'Urgente',
    };
    return labels[priorite] || 'Moyenne';
  };

  const handleToggleComplete = async () => {
    await onUpdate(tache.id, { ...tache, completee: !tache.completee });
  };

  return (
    <Card
      sx={{
        mb: 2,
        borderLeft: `4px solid ${tache.couleur || getPrioriteColor(tache.priorite)}`,
        opacity: tache.completee ? 0.6 : 1,
        transition: 'all 0.3s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        },
      }}
    >
      <CardContent>
        <Stack spacing={2}>
          {/* En-tête avec emoji et titre */}
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box display="flex" alignItems="center" gap={1}>
              <Checkbox
                checked={tache.completee}
                onChange={handleToggleComplete}
                color="success"
              />
              <Typography
                variant="h6"
                sx={{
                  textDecoration: tache.completee ? 'line-through' : 'none',
                }}
              >
                {tache.emoji} {tache.titre}
              </Typography>
            </Box>
            
            <Box>
              <IconButton size="small" onClick={() => onEdit(tache)} color="primary">
                <EditIcon fontSize="small" />
              </IconButton>
              <IconButton size="small" onClick={() => onDelete(tache.id)} color="error">
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>

          {/* Description */}
          {tache.description && (
            <Typography variant="body2" color="text.secondary">
              {tache.description}
            </Typography>
          )}

          {/* Métadonnées */}
          <Box display="flex" gap={1} flexWrap="wrap" alignItems="center">
            <Chip
              label={getPrioriteLabel(tache.priorite)}
              size="small"
              sx={{
                bgcolor: getPrioriteColor(tache.priorite),
                color: 'white',
                fontWeight: 'bold',
              }}
            />
            
            {tache.categorie_nom && (
              <Chip
                label={tache.categorie_nom}
                size="small"
                variant="outlined"
              />
            )}
            
            <Box display="flex" alignItems="center" gap={0.5}>
              <CalendarToday sx={{ fontSize: 16, color: 'text.secondary' }} />
              <Typography variant="caption" color="text.secondary">
                {format(new Date(tache.date_echeance), 'dd MMM yyyy, HH:mm', { locale: fr })}
              </Typography>
            </Box>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default TacheCard;