import React from 'react';
import { useRouter } from 'next/router';
import SidebarLayout from '@/components/layout/SidebarLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';

export default function FileDetailPage() {
  const router = useRouter();
  const { id } = router.query as { id?: string };

  return (
    <SidebarLayout>
      <div className="space-y-6">
        <div className="text-sm text-muted-foreground">
          <Link href="/dashboard" className="hover:underline">Dashboard</Link>
          <span className="mx-2">/</span>
          <span>File Detail</span>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>File: {id || '...'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h3 className="font-medium mb-2">Overview</h3>
                <div className="h-24 rounded-md border border-dashed flex items-center justify-center text-sm text-muted-foreground">
                  High-level metrics will render here
                </div>
              </div>
              <div>
                <h3 className="font-medium mb-2">Status</h3>
                <div className="h-24 rounded-md border border-dashed flex items-center justify-center text-sm text-muted-foreground">
                  Analysis status from backend will render here
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detailed Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 rounded-md border border-dashed flex items-center justify-center text-sm text-muted-foreground">
              Detailed insights for {id || '...'} will render here
            </div>
          </CardContent>
        </Card>
      </div>
    </SidebarLayout>
  );
}
