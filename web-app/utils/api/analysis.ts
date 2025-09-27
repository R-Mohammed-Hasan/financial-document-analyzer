import api from './client';

export async function analyzeDocument(payload: { file_name: string; query: string }) {
  const res = await api.post('/analysis/analyze', payload);
  return res.data;
}
