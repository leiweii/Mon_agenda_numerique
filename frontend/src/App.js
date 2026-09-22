import React, { useEffect, useMemo, useState } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from 'react-router-dom';
import {
  Box,
  CssBaseline,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  ThemeProvider,
  createTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Assignment,
  Category,
  Settings,
  Home as HomeIcon,
  WorkOutline,
  SmartToyOutlined,
} from '@mui/icons-material';

import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Layout/Navbar';
import Dashboard from './components/Statistiques/Dashboard';
import TacheListe from './components/Taches/TacheListe';
import CategorieListe from './components/Categories/CategorieListe';
import Parametres from './pages/Parametres';
import Inscription from './pages/Inscription';
import Login from './pages/Login';
import MotDePasseOublie from './pages/MotDePasseOublie';
import ReinitialiserMotDePasse from './pages/ReinitialiserMotDePasse';
import Home from './pages/Home';
import Candidatures from './pages/Candidatures';
import CandidatureDetail from './pages/CandidatureDetail';
import AgentChat from './components/Agent/AgentChat';
import { preferencesAPI } from './services/api';

const DRAWER_WIDTH = 240;

// Thème personnalisé
const createAppTheme = (themeName) => createTheme({
  palette: {
    mode: themeName === 'sombre' ? 'dark' : 'light',
    primary: {
      main: '#667eea',
      lighter: '#e8eaf6',
    },
    secondary: {
      main: '#764ba2',
    },
    success: {
      main: '#2ecc71',
      lighter: '#e8f5e9',
    },
    warning: {
      main: '#f39c12',
      lighter: '#fff3e0',
    },
    error: {
      main: '#e74c3c',
      lighter: '#ffebee',
    },
    info: {
      main: '#3498db',
      lighter: '#e3f2fd',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 700,
    },
    h6: {
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
});

// Menu de navigation
const menuItems = [
  { text: 'Accueil', icon: <HomeIcon />, path: '/' },
  { text: 'Tableau de bord', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Mes tâches', icon: <Assignment />, path: '/taches' },
  { text: 'Candidatures', icon: <WorkOutline />, path: '/candidatures' },
  { text: 'Assistant', icon: <SmartToyOutlined />, path: '/agent' },
  { text: 'Catégories', icon: <Category />, path: '/categories' },
  { text: 'Paramètres', icon: <Settings />, path: '/parametres' },
];

// Sidebar Component
const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div>
      <Toolbar />
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              onClick={() => navigate(item.path)}
              selected={location.pathname === item.path}
              sx={{
                '&:hover': {
                  bgcolor: 'primary.lighter',
                },
                '&.Mui-selected': {
                  bgcolor: 'primary.lighter',
                  '&:hover': {
                    bgcolor: 'primary.lighter',
                  },
                },
              }}
            >
              <ListItemIcon sx={{ color: 'primary.main' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  );
};

// Layout principal
const MainLayout = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <Navbar onMenuClick={handleDrawerToggle} />
      
      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
        >
          <Sidebar />
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
          open
        >
          <Sidebar />
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3 },
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: 8,
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

// Route protégée
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        Chargement...
      </Box>
    );
  }

  return user ? children : <Navigate to="/login" />;
};

// Composant principal
function AppContent({ onThemeChange }) {
  return (
    <Router>
      <Routes>
        {/* Routes publiques */}
        <Route path="/login" element={<Login />} />
        <Route path="/inscription" element={<Inscription />} />
        <Route path="/mot-de-passe-oublie" element={<MotDePasseOublie />} />
        <Route path="/reinitialiser-mot-de-passe/:uid/:token" element={<ReinitialiserMotDePasse />} />
        
        {/* Routes protégées avec layout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout>
                <Home />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <MainLayout>
                <Dashboard />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/taches"
          element={
            <ProtectedRoute>
              <MainLayout>
                <TacheListe />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/categories"
          element={
            <ProtectedRoute>
              <MainLayout>
                <CategorieListe />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/parametres"
          element={
            <ProtectedRoute>
              <MainLayout>
                <Parametres onThemeChange={onThemeChange} />
              </MainLayout>
            </ProtectedRoute>
          }
        />
        <Route path="/candidatures" element={
          <ProtectedRoute><MainLayout><Candidatures /></MainLayout></ProtectedRoute>
        } />
        <Route path="/candidatures/:id" element={
          <ProtectedRoute><MainLayout><CandidatureDetail /></MainLayout></ProtectedRoute>
        } />
        <Route path="/agent" element={
          <ProtectedRoute><MainLayout><AgentChat /></MainLayout></ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
}

function AuthenticatedApp() {
  const { user } = useAuth();
  const [themeName, setThemeName] = useState('clair');
  const theme = useMemo(() => createAppTheme(themeName), [themeName]);

  useEffect(() => {
    if (!user) {
      setThemeName('clair');
      return;
    }

    const chargerTheme = async () => {
      try {
        const response = await preferencesAPI.get();
        const preference = response.data[0];
        setThemeName(preference?.theme === 'sombre' ? 'sombre' : 'clair');
      } catch (error) {
        console.error('Erreur chargement thème:', error);
      }
    };

    chargerTheme();
  }, [user]);

  useEffect(() => {
    document.documentElement.dataset.theme = themeName;
  }, [themeName]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppContent onThemeChange={(theme) => setThemeName(theme === 'sombre' ? 'sombre' : 'clair')} />
    </ThemeProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}

export default App;
