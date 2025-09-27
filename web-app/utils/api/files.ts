import api from './client';

export async function uploadFile(formData: FormData, onUploadProgress?: (p: number) => void) {
  const res = await api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (evt.total) {
        const pct = Math.round((evt.loaded * 100) / evt.total);
        onUploadProgress?.(pct);
      }
    },
  });
  return res.data as {
    file_id: number;
    filename: string;
    original_filename: string;
  };
}

export async function listFiles() {
  const res = await api.get('/files');
  return res.data;
}
