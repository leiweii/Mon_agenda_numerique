import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Paper,
  Skeleton,
  Typography,
} from '@mui/material';
import { AutoAwesome, Refresh } from '@mui/icons-material';

import { tachesAPI } from '../services/api';


const RecommandationsIA = () => {
  const [recommandation, setRecommandation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const chargerRecommandation = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await tachesAPI.getRecommandationIA();
      setRecommandation(response.data);
    } catch (requestError) {
      setError('Impossible de charger la recommandation IA.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    chargerRecommandation();
  }, [chargerRecommandation]);

  if (loading) {
    return (
      <Paper aria-label="Chargement de la recommandation IA" sx={{ p: 3 }}>
        <Skeleton width="45%" height={28} />
        <Skeleton width="90%" />
        <Skeleton width="55%" />
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert
        severity="error"
        action={(
          <Button color="inherit" size="small" startIcon={<Refresh />} onClick={chargerRecommandation}>
            Réessayer
          </Button>
        )}
      >
        {error}
      </Alert>
    );
  }

  const heures = recommandation?.heures_recommandees || [];

  return (
    <Paper sx={{ p: 3 }}>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <AutoAwesome color="primary" />
        <Typography variant="h6" fontWeight="bold">
          Recommandation IA
        </Typography>
      </Box>
      <Typography variant="body1">{recommandation?.message}</Typography>
      {heures.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Heures recommandées : {heures.map((heure) => `${heure}h`).join(', ')}
        </Typography>
      )}
    </Paper>
  );
};


export default RecommandationsIA;
