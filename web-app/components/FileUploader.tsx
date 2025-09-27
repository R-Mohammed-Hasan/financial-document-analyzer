import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { uploadFile } from '@/utils/api/files';

type Props = {
  onUploaded: (fileName: string) => void;
};

export default function FileUploader({ onUploaded }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [loading, setLoading] = useState(false);

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
  };

  const onUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setLoading(true);
    try {
      const data = await uploadFile(formData, setProgress);
      onUploaded(data.filename || data.original_filename);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <Input type="file" accept=".pdf,.docx,.xlsx,.csv,.txt" onChange={onChange} />
      {loading && <Progress value={progress} />}
      <Button onClick={onUpload} disabled={!file || loading}>Upload</Button>
    </div>
  );
}
