import React from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
//   Paper,
} from '@mui/material';
import {
  CheckCircle,
  TrendingUp,
  Schedule,
  EmojiEvents,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const features = [
    {
      icon: <CheckCircle sx={{ fontSize: 50, color: 'success.main' }} />,
      title: 'Gestion Simple',
      description: 'Créez et organisez vos tâches en quelques clics',
    },
    {
      icon: <TrendingUp sx={{ fontSize: 50, color: 'primary.main' }} />,
      title: 'Statistiques',
      description: 'Suivez votre productivité avec des graphiques détaillés',
    },
    {
      icon: <Schedule sx={{ fontSize: 50, color: 'warning.main' }} />,
      title: 'Rappels Intelligents',
      description: 'Ne manquez jamais une échéance importante',
    },
    {
      icon: <EmojiEvents sx={{ fontSize: 50, color: 'error.main' }} />,
      title: 'Personnalisation',
      description: 'Emojis, couleurs et catégories à votre goût',
    },
  ];

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Hero Section */}
      <Container maxWidth="lg" sx={{ pt: 10, pb: 8 }}>
        <Box textAlign="center" color="white" mb={8}>
          <Typography variant="h2" fontWeight="bold" gutterBottom>
            📅 Mon Agenda Numérique
          </Typography>
          <Typography variant="h5" sx={{ mb: 4, opacity: 0.9 }}>
            Organisez votre vie, une tâche à la fois
          </Typography>
          
          {user ? (
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/dashboard')}
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.9)',
                },
              }}
            >
              Accéder à mon tableau de bord
            </Button>
          ) : (
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/login')}
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.9)',
                },
              }}
            >
              Commencer maintenant
            </Button>
          )}
        </Box>

        {/* Features */}
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card
                sx={{
                  height: '100%',
                  textAlign: 'center',
                  transition: 'transform 0.3s',
                  '&:hover': {
                    transform: 'translateY(-8px)',
                  },
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box mb={2}>{feature.icon}</Box>
                  <Typography variant="h6" fontWeight="bold" gutterBottom>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Footer */}
      <Box
        component="footer"
        sx={{
          bgcolor: 'rgba(0,0,0,0.1)',
          color: 'white',
          py: 3,
          textAlign: 'center',
        }}
      >
        <Typography variant="body2">
          © 2026 Mon Agenda Numérique - Fait avec ❤️
        </Typography>
      </Box>
    </Box>
  );
};

export default Home;