import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  Alert,
} from '@mui/material';
import {
  TrendingUp,
  CheckCircle,
  Schedule,
  Warning,
  EmojiEvents,
} from '@mui/icons-material';
import GraphiquesPriorite from './GraphiquesPriorite';
import { tachesAPI } from '../../services/api';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [meilleurMoment, setMeilleurMoment] = useState(null);
  const [tachesAujourdhui, setTachesAujourdhui] = useState([]);
  const [tachesSemaine, setTachesSemaine] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    chargerStatistiques();
  }, []);

  const chargerStatistiques = async () => {
    try {
      const [statsRes, momentRes, jourRes, semaineRes] = await Promise.all([
        tachesAPI.getStatistiques(),
        tachesAPI.getMeilleurMoment(),
        tachesAPI.getAujourdhui(),
        tachesAPI.getCetteSemaine(),
      ]);
      
      setStats(statsRes.data);
      setMeilleurMoment(momentRes.data);
      setTachesAujourdhui(jourRes.data);
      setTachesSemaine(semaineRes.data);
    } catch (error) {
      console.error('Erreur chargement stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon, color, subtitle }) => (
    <Card sx={{ height: '100%', position: 'relative', overflow: 'visible' }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography color="text.secondary" variant="subtitle2" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h3" fontWeight="bold" color={color}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              bgcolor: `${color}.lighter`,
              borderRadius: 2,
              p: 1.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 2 }}>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* En-tête */}
      <Box mb={4}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          📊 Tableau de Bord
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Vue d'ensemble de votre productivité
        </Typography>
      </Box>

      {/* Cartes de statistiques */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total de tâches"
            value={stats?.total || 0}
            icon={<Schedule sx={{ fontSize: 40, color: 'primary.main' }} />}
            color="primary"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Terminées"
            value={stats?.completees || 0}
            icon={<CheckCircle sx={{ fontSize: 40, color: 'success.main' }} />}
            color="success"
            subtitle={`${stats?.taux_completion?.toFixed(0)}% de réussite`}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="En cours"
            value={stats?.en_cours || 0}
            icon={<TrendingUp sx={{ fontSize: 40, color: 'warning.main' }} />}
            color="warning"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Aujourd'hui"
            value={tachesAujourdhui.length}
            icon={<Warning sx={{ fontSize: 40, color: 'error.main' }} />}
            color="error"
          />
        </Grid>
      </Grid>

      {/* Recommandation meilleur moment */}
      {meilleurMoment?.heures_recommandees && (
        <Alert 
          icon={<EmojiEvents />} 
          severity="info" 
          sx={{ mb: 4, fontSize: '1rem' }}
        >
          <Typography variant="subtitle1" fontWeight="bold">
            💡 {meilleurMoment.message}
          </Typography>
          <Typography variant="body2">
            Heures optimales : {meilleurMoment.heures_recommandees.map(h => `${h}h`).join(', ')}
          </Typography>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Graphique des priorités */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom fontWeight="bold">
              Répartition par priorité
            </Typography>
            <GraphiquesPriorite data={stats?.par_priorite || []} />
          </Paper>
        </Grid>

        {/* Progression hebdomadaire */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom fontWeight="bold">
              Progression de la semaine
            </Typography>
            
            <Box mt={3}>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Tâches complétées</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {tachesSemaine.filter(t => t.completee).length} / {tachesSemaine.length}
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={
                  tachesSemaine.length > 0 
                    ? (tachesSemaine.filter(t => t.completee).length / tachesSemaine.length) * 100 
                    : 0
                }
                sx={{ height: 10, borderRadius: 5 }}
              />
            </Box>

            <Box mt={4}>
              <Typography variant="subtitle2" gutterBottom>
                Tâches de cette semaine
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap" mt={2}>
                {tachesSemaine.slice(0, 5).map((tache) => (
                  <Chip
                    key={tache.id}
                    label={`${tache.emoji} ${tache.titre}`}
                    color={tache.completee ? 'success' : 'default'}
                    variant={tache.completee ? 'filled' : 'outlined'}
                    size="small"
                  />
                ))}
                {tachesSemaine.length > 5 && (
                  <Chip label={`+${tachesSemaine.length - 5} autres`} size="small" />
                )}
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Tâches urgentes */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom fontWeight="bold">
              🔥 Tâches prioritaires aujourd'hui
            </Typography>
            
            {tachesAujourdhui.length === 0 ? (
              <Box textAlign="center" py={4}>
                <Typography color="text.secondary">
                  Aucune tâche pour aujourd'hui ! 🎉
                </Typography>
              </Box>
            ) : (
              <Grid container spacing={2} mt={1}>
                {tachesAujourdhui
                  .filter(t => !t.completee)
                  .sort((a, b) => b.priorite - a.priorite)
                  .slice(0, 3)
                  .map((tache) => (
                    <Grid item xs={12} md={4} key={tache.id}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6">
                            {tache.emoji} {tache.titre}
                          </Typography>
                          <Chip
                            label={
                              tache.priorite === 4 ? 'Urgente' :
                              tache.priorite === 3 ? 'Haute' :
                              tache.priorite === 2 ? 'Moyenne' : 'Basse'
                            }
                            color={
                              tache.priorite === 4 ? 'error' :
                              tache.priorite === 3 ? 'warning' : 'info'
                            }
                            size="small"
                            sx={{ mt: 1 }}
                          />
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
              </Grid>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;