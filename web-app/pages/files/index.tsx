import React, { useEffect, useState } from 'react';
import SidebarLayout from '@/components/layout/SidebarLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { listFiles, downloadFileById, deleteFileById } from '@/utils/api/files';

export default function FilesListPage() {
  const [files, setFiles] = useState<Array<any>>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [busyIds, setBusyIds] = useState<Record<string, boolean>>({});
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const data = await listFiles();
        if (!mounted) return;
        setFiles(Array.isArray(data) ? data : data?.files || []);
      } catch (e: any) {
        if (!mounted) return;
        setError(e?.response?.data?.detail || e?.message || 'Failed to load files');
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const toId = (f: any) => f.file_id ?? f.id ?? f.filename ?? f.name;
  const toLabel = (f: any) => f.original_filename ?? f.filename ?? f.name ?? String(toId(f));
  const toPublic = (f: any) => (f.is_public ?? f.public ?? false) as boolean;
  const toStatus = (f: any) => f.status ?? '-';
  const toType = (f: any) => f.content_type ?? f.mime_type ?? '-';
  const toCreated = (f: any) => f.created_at ?? f.uploaded_at ?? f.updated_at ?? null;
  const fmtDate = (v: any) => {
    if (!v) return '-';
    try {
      const d = new Date(v);
      if (isNaN(d.getTime())) return String(v);
      return d.toLocaleString();
    } catch {
      return String(v);
    }
  };

  async function handleDownload(file: any) {
    const id = toId(file);
    if (id == null) return;
    try {
      setBusyIds((b) => ({ ...b, [id]: true }));
      const { blob, filename } = await downloadFileById(id);
      const a = document.createElement('a');
      const url = URL.createObjectURL(blob);
      a.href = url;
      a.download = filename || toLabel(file) || `file-${id}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || 'Failed to download file');
    } finally {
      setBusyIds((b) => ({ ...b, [id]: false }));
    }
  }

  async function handleDelete(file: any) {
    const id = toId(file);
    if (id == null) return;
    const label = toLabel(file);
    if (!confirm(`Delete "${label}"? This cannot be undone.`)) return;
    try {
      setBusyIds((b) => ({ ...b, [id]: true }));
      await deleteFileById(id);
      setFiles((prev) => prev.filter((x) => toId(x) !== id));
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || 'Failed to delete file');
    } finally {
      setBusyIds((b) => ({ ...b, [id]: false }));
    }
  }

  return (
    <SidebarLayout>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Your Files</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="text-sm text-muted-foreground">Loading files...</div>
            )}
            {error && (
              <div className="text-sm text-red-600">{error}</div>
            )}
            {!loading && !error && (
              <div>
                {files.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No files found.</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Public</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Content Type</TableHead>
                        <TableHead>Created At</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {files.map((f: any) => {
                        const id = toId(f);
                        const label = toLabel(f);
                        const isBusy = !!busyIds[id];
                        return (
                          <TableRow
                            key={String(id)}
                            className="cursor-pointer"
                            onClick={() => router.push(`/files/${encodeURIComponent(String(id))}`)}
                          >
                            <TableCell title={label} className="max-w-[280px] truncate">
                              <Link
                                href={`/files/${encodeURIComponent(String(id))}`}
                                className="hover:underline"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {label}
                              </Link>
                            </TableCell>
                            <TableCell>{toPublic(f) ? 'Yes' : 'No'}</TableCell>
                            <TableCell>{toStatus(f)}</TableCell>
                            <TableCell className="truncate">{toType(f)}</TableCell>
                            <TableCell>{fmtDate(toCreated(f))}</TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDownload(f);
                                  }}
                                  disabled={isBusy}
                                  className="text-xs px-2 py-1 rounded border hover:bg-muted disabled:opacity-50"
                                >
                                  {isBusy ? 'Working…' : 'Download'}
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDelete(f);
                                  }}
                                  disabled={isBusy}
                                  className="text-xs px-2 py-1 rounded border border-red-300 text-red-700 hover:bg-red-50 disabled:opacity-50"
                                >
                                  Delete
                                </button>
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </SidebarLayout>
  );
}

