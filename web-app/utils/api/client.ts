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
    const originalRequest = error?.config;
    if (status === 401 && typeof window !== 'undefined') {
      // Attempt token refresh once per failing request chain
      if (!originalRequest._retry) {
        originalRequest._retry = true;
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          // Use a bare axios call to avoid interceptor recursion
          return axios
            .post(`${baseURL}/api/v1/refresh`, { refresh_token: refreshToken })
            .then((res) => {
              const newAccess = res?.data?.access_token || res?.data?.token;
              const newRefresh = res?.data?.refresh_token || refreshToken;
              if (!newAccess) throw new Error('No access token in refresh response');
              localStorage.setItem('authToken', newAccess);
              localStorage.setItem('refreshToken', newRefresh);
              // Update authorization header and retry
              originalRequest.headers = originalRequest.headers || {};
              originalRequest.headers['Authorization'] = `Bearer ${newAccess}`;
              return api.request(originalRequest);
            })
            .catch((refreshErr) => {
              // If refresh fails, clear tokens and notify
              localStorage.removeItem('authToken');
              localStorage.removeItem('refreshToken');
              if (onAuthInvalid) onAuthInvalid();
              if (window.location.pathname !== '/users/login') {
                window.location.href = '/users/login';
              }
              return Promise.reject(refreshErr);
            });
        }
      }
      // No refresh token or already retried: clear and redirect
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      if (onAuthInvalid) onAuthInvalid();
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
