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

export async function getFile(fileId: string | number) {
  const res = await api.get(`/files/${encodeURIComponent(String(fileId))}`);
  return res.data;
}

// Download a file as Blob and return both blob and suggested filename (if provided)
export async function downloadFileById(fileId: string | number) {
  const res = await api.get(`/files/${encodeURIComponent(String(fileId))}/download`, {
    responseType: 'blob',
  });
  // Try to parse filename from Content-Disposition
  const disposition = res.headers?.['content-disposition'] as string | undefined;
  let filename: string | undefined;
  if (disposition) {
    const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
    filename = decodeURIComponent(match?.[1] || match?.[2] || '');
  }
  return { blob: res.data as Blob, filename };
}

// Delete a file by ID
export async function deleteFileById(fileId: string | number) {
  const res = await api.delete(`/files/${encodeURIComponent(String(fileId))}`);
  return res.data as { message?: string };
}
