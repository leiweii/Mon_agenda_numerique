import axios from 'axios';

const API_URL = 'http://localhost:8000/api/';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token d'authentification
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Services pour les tâches
export const tachesAPI = {
  getAll: () => api.get('taches/'),
  getById: (id) => api.get(`taches/${id}/`),
  create: (data) => api.post('taches/', data),
  update: (id, data) => api.put(`taches/${id}/`, data),
  delete: (id) => api.delete(`taches/${id}/`),
  getAujourdhui: () => api.get('taches/aujourd_hui/'),
  getCetteSemaine: () => api.get('taches/cette_semaine/'),
  getStatistiques: () => api.get('taches/statistiques/'),
  getMeilleurMoment: () => api.get('taches/meilleur_moment/'),
};

// Services pour les catégories
export const categoriesAPI = {
  getAll: () => api.get('categories/'),
  create: (data) => api.post('categories/', data),
  update: (id, data) => api.put(`categories/${id}/`, data),
  delete: (id) => api.delete(`categories/${id}/`),
};

// Services pour les préférences
export const preferencesAPI = {
  get: () => api.get('preferences/'),
  update: (id, data) => api.put(`preferences/${id}/`, data),
};

// Authentification
export const authAPI = {
  login: (username, password) => 
    api.post('auth/login/', { username, password }),
  logout: () => api.post('auth/logout/'),
  getCurrentUser: () => api.get('auth/user/'),
};

export default api;