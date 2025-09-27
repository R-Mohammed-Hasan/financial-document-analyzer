import api from './client';

export async function postLogin(payload: { email: string; password: string }) {
  const res = await api.post('/login', payload);
  return res.data;
}

export async function postRegister(payload: {
  email: string;
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  accept_terms: boolean;
}) {
  const res = await api.post('/register', payload);
  return res.data;
}

export async function getMe() {
  const res = await api.get('/me');
  return res.data as {
    id: number;
    email: string;
    username: string;
    first_name?: string;
    last_name?: string;
    is_active: boolean;
    is_superuser?: boolean;
  };
}
