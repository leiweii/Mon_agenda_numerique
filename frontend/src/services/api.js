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
  getRecommandationIA: () => api.get('taches/recommandation_ia/'),
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
  create: (data) => api.post('preferences/', data),
  update: (id, data) => api.put(`preferences/${id}/`, data),
};

// Authentification
export const authAPI = {
  login: (identifier, password) =>
    api.post('auth/login/', { identifier, password }),
  register: (data) => api.post('auth/register/', data),
  requestPasswordReset: (email) => api.post('auth/mot-de-passe-oublie/', { email }),
  resetPassword: (data) => api.post('auth/reinitialiser-mot-de-passe/', data),
  logout: () => api.post('auth/logout/'),
  getCurrentUser: () => api.get('auth/user/'),
};

export const candidaturesAPI = {
  getAll: (params) => api.get('candidatures/', { params }),
  exportCsv: (params) => api.get('candidatures/export_csv/', { params, responseType: 'blob' }),
  getById: (id) => api.get(`candidatures/${id}/`),
  importUrl: (url) => api.post('candidatures/import_url/', { url }),
  create: (data) => api.post('candidatures/', data),
  update: (id, data) => api.put(`candidatures/${id}/`, data),
  patch: (id, data) => api.patch(`candidatures/${id}/`, data),
  delete: (id) => api.delete(`candidatures/${id}/`),
  archive: (id) => api.patch(`candidatures/${id}/archiver/`),
  getDefaultCv: () => api.get('candidatures/cv_par_defaut/'),
  replaceDefaultCv: (file) => {
    const data = new FormData();
    data.append('fichier', file);
    return api.put('candidatures/cv_par_defaut/', data, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  getEmails: (id) => api.get(`candidatures/${id}/emails/`),
  prepareEmail: (id, data) => api.post(`candidatures/${id}/preparer_email/`, data),
  updateEmail: (candidatureId, emailId, data) => api.patch(`candidatures/${candidatureId}/emails/${emailId}/`, data),
  cancelEmail: (candidatureId, emailId) => api.post(`candidatures/${candidatureId}/emails/${emailId}/annuler/`),
  prepareEmailSend: (candidatureId, emailId, data) => api.post(`candidatures/${candidatureId}/emails/${emailId}/preparer_envoi/`, data),
  sendEmail: (candidatureId, emailId, cvFingerprint) => api.post(`candidatures/${candidatureId}/emails/${emailId}/envoyer/`, { confirmation: true, cv_fingerprint: cvFingerprint }),
  confirmEmailManually: (candidatureId, emailId) => api.post(`candidatures/${candidatureId}/emails/${emailId}/confirmer_manuellement/`, { confirmation: true }),
  createEmailRetry: (candidatureId, emailId) => api.post(`candidatures/${candidatureId}/emails/${emailId}/nouvelle_tentative/`, { confirmation: true }),
};

export const candidatureActionsAPI = {
  getAll: (candidatureId) => api.get(`candidatures/${candidatureId}/actions/`),
  create: (candidatureId, data) => api.post(`candidatures/${candidatureId}/actions/`, data),
  update: (candidatureId, actionId, data) => api.put(`candidatures/${candidatureId}/actions/${actionId}/`, data),
  delete: (candidatureId, actionId) => api.delete(`candidatures/${candidatureId}/actions/${actionId}/`),
};

export const gmailAPI = {
  connect: () => api.post('gmail/connecter/'),
  getStatus: () => api.get('gmail/statut/'),
  verify: () => api.post('gmail/verifier/'),
};

export const agentAPI = {
  sendMessage: (data) => api.post('agent/chat/', data),
  getConversation: (id) => api.get(`agent/conversations/${id}/`),
  confirmAction: (id) => api.post(`agent/actions/${id}/confirmer/`),
  cancelAction: (id) => api.post(`agent/actions/${id}/annuler/`),
};

export default api;
