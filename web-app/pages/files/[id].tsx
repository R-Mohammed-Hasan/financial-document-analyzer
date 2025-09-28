import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import SidebarLayout from '@/components/layout/SidebarLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { getFile } from '@/utils/api/files';

export default function FileDetailPage() {
  const router = useRouter();
  const { id } = router.query as { id?: string };
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    if (!id) return;
    (async () => {
      try {
        setLoading(true);
        const res = await getFile(id);
        if (!active) return;
        setData(res);
      } catch (e: any) {
        if (!active) return;
        setError(e?.response?.data?.detail || e?.message || 'Failed to load file');
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [id]);

  function handleExport() {
    if (!data && !id) return;
    try {
      setExporting(true);
      const payload = {
        exported_at: new Date().toISOString(),
        file_id: id,
        data,
      };
      const json = JSON.stringify(payload, null, 2);
      const blob = new Blob([json], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const base = data?.original_filename || data?.filename || `file-${id}`;
      const safe = String(base).replace(/\s+/g, '_').replace(/[^\w\.-]/g, '');
      a.href = url;
      a.download = `${safe}-export.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  return (
    <SidebarLayout>
      <div className="space-y-6">
        <div className="text-sm text-muted-foreground">
          <Link href="/files" className="hover:underline">Files</Link>
          <span className="mx-2">/</span>
          <span>File Detail</span>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle>File id: {id || '...'}</CardTitle>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleExport}
                  disabled={exporting || loading || !!error}
                  className="text-sm px-3 py-1.5 rounded border hover:bg-muted disabled:opacity-50"
                >
                  {exporting ? 'Exporting…' : 'Export JSON'}
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="text-sm text-muted-foreground">Loading file details...</div>
            )}
            {error && (
              <div className="text-sm text-red-600">{error}</div>
            )}
            {!loading && !error && (
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h3 className="font-medium mb-2">Overview</h3>
                  <div className="rounded-md border p-3 text-sm">
                    <div><span className="text-muted-foreground">Original name:</span> {data?.original_filename ?? data?.filename ?? '-'}</div>
                    <div><span className="text-muted-foreground">Stored name:</span> {data?.filename ?? data?.name ?? '-'}</div>
                    <div><span className="text-muted-foreground">Size:</span> {data?.size_bytes ?? data?.size ?? '-'}{data?.size_bytes ? ' bytes' : ''}</div>
                    <div><span className="text-muted-foreground">Uploaded at:</span> {data?.uploaded_at ?? data?.created_at ?? '-'}</div>
                  </div>
                </div>
                <div>
                  <h3 className="font-medium mb-2">Status</h3>
                  <div className="rounded-md border p-3 text-sm">
                    <div><span className="text-muted-foreground">Processing:</span> {String(data?.processing ?? data?.in_progress ?? false)}</div>
                    <div><span className="text-muted-foreground">Status:</span> {data?.status ?? '-'}</div>
                    <div><span className="text-muted-foreground">Last updated:</span> {data?.updated_at ?? '-'}</div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detailed Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="text-sm text-muted-foreground">Loading analysis...</div>
            )}
            {!loading && !error && (
              <div className="rounded-md border p-3 text-sm">
                {data?.analysis_summary ? (
                  <pre className="whitespace-pre-wrap break-words">{data.analysis_summary}</pre>
                ) : (
                  <div className="text-muted-foreground">No analysis summary available.</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </SidebarLayout>
  );
}

