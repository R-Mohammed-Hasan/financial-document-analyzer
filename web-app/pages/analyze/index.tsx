import React, { useState } from 'react';
import SidebarLayout from '@/components/layout/SidebarLayout';
import FileUploader from '@/components/FileUploader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { analyzeDocument } from '@/utils/api/analysis';
import { toast } from 'react-toastify';

export default function AnalyzePage() {
  const [lastUploaded, setLastUploaded] = useState<string | null>(null);
  const [query, setQuery] = useState('Summarize key financial insights.');
  const [loading, setLoading] = useState(false);

  const triggerAnalysis = async () => {
    if (!lastUploaded) {
      toast.warn('Upload a file first');
      return;
    }
    setLoading(true);
    try {
      await analyzeDocument({ file_name: lastUploaded, query });
      toast.success('Analysis started in background');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to start analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SidebarLayout>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload Financial Document</CardTitle>
          </CardHeader>
          <CardContent>
            <FileUploader onUploaded={setLastUploaded} />
            {lastUploaded && (
              <p className="text-sm text-muted-foreground mt-2">Last uploaded: {lastUploaded}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Run Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <textarea
              className="w-full rounded-md border border-input bg-transparent p-3 text-sm"
              rows={4}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="mt-3">
              <Button onClick={triggerAnalysis} disabled={loading}>
                {loading ? 'Starting...' : 'Start Analysis'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </SidebarLayout>
  );
}
