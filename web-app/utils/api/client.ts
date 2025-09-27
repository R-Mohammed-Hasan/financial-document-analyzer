import axios from 'axios';

const baseURL = process.env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${baseURL}/api/v1`,
});

let ensureUser: (() => Promise<void>) | null = null;
export function setEnsureUser(cb: () => Promise<void>) {
  ensureUser = cb;
}

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers = config.headers || {};
      config.headers['Authorization'] = `Bearer ${token}`;
      // Ensure user is fetched before proceeding
      if (ensureUser) {
        return ensureUser().then(() => config);
      }
    }
  }
  return config;
});

let onAuthInvalid: (() => void) | null = null;
export function setOnAuthInvalid(cb: () => void) {
  onAuthInvalid = cb;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      // Clear token and notify
      if (typeof window !== 'undefined') {
        localStorage.removeItem('authToken');
      }
      if (onAuthInvalid) onAuthInvalid();
      // Fallback redirect if no handler
      if (typeof window !== 'undefined') {
        if (window.location.pathname !== '/users/login') {
          window.location.href = '/users/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
