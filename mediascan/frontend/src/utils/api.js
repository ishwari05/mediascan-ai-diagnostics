import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5001/api',
  timeout: 30000, // Standard timeout
});

// Create a specialized instance for analysis (long timeout)
const analysisApi = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5001/api',
  timeout: 120000, 
});

// Request Interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mediascan_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

analysisApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('mediascan_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor
const handleAuthError = (error) => {
  if (error.response && error.response.status === 401) {
    localStorage.removeItem('mediascan_token');
    window.location.href = '/login';
  }
  return Promise.reject(error);
};

api.interceptors.response.use(res => res, handleAuthError);
analysisApi.interceptors.response.use(res => res, handleAuthError);

export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  signup: (data) => api.post('/auth/signup', data),
  getMe: () => api.get('/auth/me'),
  update: (data) => api.put('/auth/update-profile', data),
};

export const predictionsAPI = {
  analyze: (formData) => analysisApi.post('/predictions/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getHistory: (page = 1, limit = 10) => api.get(`/predictions/history?page=${page}&limit=${limit}`),
  getById: (id) => api.get(`/predictions/${id}`),
  getPrevious: (id) => api.get(`/predictions/compare/${id}`),
  delete: (id) => api.delete(`/predictions/${id}`),
  getStats: () => api.get('/predictions/stats'),
};

export const reportsAPI = {
  downloadPDF: (id) => api.get(`/reports/download/${id}`, { responseType: 'blob' }),
};

export const adminAPI = {
  getStats: () => api.get('/admin/stats'),
  getUsers: (page = 1) => api.get(`/admin/users?page=${page}`),
  getPredictions: (page = 1) => api.get(`/admin/predictions?page=${page}`),
  toggleUser: (id) => api.post(`/admin/users/${id}/toggle`),
};

export const mlAPI = {
  getMetrics: () => api.get('/ml/metrics'),
  predict: (formData) => api.post('/ml/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  generateGradcam: (formData) => api.post('/ml/gradcam', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
};

export const chatbotAPI = {
  sendMessage: (message) => api.post('/chatbot/message', { message }),
  getSuggestions: () => api.get('/chatbot/suggestions'),
};

export default api;
