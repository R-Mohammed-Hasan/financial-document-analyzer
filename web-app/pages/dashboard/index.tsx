import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import SidebarLayout from '@/components/layout/SidebarLayout';
import dynamic from 'next/dynamic';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title as ChartTitle,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

// Register chart.js parts once
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ChartTitle, Tooltip, Legend, Filler);

// Dynamically load Line component to avoid any SSR hiccups
const Line = dynamic(() => import('react-chartjs-2').then((m) => m.Line), { ssr: false });

export default function DashboardPage() {
  // Dummy data shaped like AnalysisMetricsResponse from backend
  const metrics = {
    total_analyses: 120,
    successful_analyses: 95,
    failed_analyses: 25,
    average_processing_time: 42,
    most_analyzed_file_type: 'PDF',
    analysis_trends: {
      '2025-09-21': 5,
      '2025-09-22': 12,
      '2025-09-23': 7,
      '2025-09-24': 15,
      '2025-09-25': 9,
      '2025-09-26': 20,
      '2025-09-27': 11,
    } as Record<string, number>,
  };

  const successRate = metrics.successful_analyses;
  const failRate = metrics.failed_analyses;
  const totalSF = Math.max(successRate + failRate, 1);
  const successPct = (successRate / totalSF) * 100;
  const failPct = (failRate / totalSF) * 100;

  // Prepare bar chart data
  const trendEntries = Object.entries(metrics.analysis_trends);
  const trendValues = trendEntries.map(([, v]) => v);
  const maxTrend = Math.max(...trendValues, 1);

  return (
    <SidebarLayout>
      <div className="space-y-6">
        {/* KPIs */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Total Analyses</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.total_analyses}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Successful</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold text-green-600">{metrics.successful_analyses}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Failed</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold text-red-600">{metrics.failed_analyses}</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Avg Proc. Time</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.average_processing_time}s</CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Top File Type</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">{metrics.most_analyzed_file_type}</CardContent>
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {/* Success vs Failure Pie */}
          <Card>
            <CardHeader>
              <CardTitle>Success vs Failure</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-6">
                <svg viewBox="0 0 36 36" width="140" height="140" className="shrink-0">
                  <circle cx="18" cy="18" r="15.915" fill="#eef2ff" />
                  {/* Success arc */}
                  <circle
                    cx="18"
                    cy="18"
                    r="15.915"
                    fill="transparent"
                    stroke="#16a34a"
                    strokeWidth="3.8"
                    strokeDasharray={`${successPct} ${100 - successPct}`}
                    strokeDashoffset="25"
                  />
                  {/* Failure arc overlays after success portion */}
                  <circle
                    cx="18"
                    cy="18"
                    r="15.915"
                    fill="transparent"
                    stroke="#dc2626"
                    strokeWidth="3.8"
                    strokeDasharray={`${failPct} ${100 - failPct}`}
                    strokeDashoffset={25 - (successPct / 100) * 100}
                  />
                </svg>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-sm bg-green-600" /> Successful: {successRate}</div>
                  <div className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-sm bg-red-600" /> Failed: {failRate}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Trends Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full overflow-x-auto">
                <svg width="100%" height="220" viewBox={`0 0 ${Math.max(trendEntries.length * 50, 300)} 220`}>
                  {/* Axis */}
                  <line x1="40" y1="10" x2="40" y2="190" stroke="#cbd5e1" strokeWidth="1" />
                  <line x1="40" y1="190" x2={trendEntries.length * 50 + 20} y2="190" stroke="#cbd5e1" strokeWidth="1" />
                  {trendEntries.map(([label, value], idx) => {
                    const barHeight = (value / maxTrend) * 150;
                    const x = 50 + idx * 50;
                    const y = 190 - barHeight;
                    return (
                      <g key={label}>
                        <rect x={x} y={y} width={30} height={barHeight} fill="#3b82f6" rx={4} />
                        <text x={x + 15} y="205" textAnchor="middle" fontSize="10" fill="#64748b">{label.slice(5)}</text>
                        <text x={x + 15} y={y - 5} textAnchor="middle" fontSize="10" fill="#475569">{value}</text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Line Chart with react-chartjs-2 */}
        <Card>
          <CardHeader>
            <CardTitle>Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <Line
                data={{
                  labels: trendEntries.map(([label]) => label),
                  datasets: [
                    {
                      label: 'Analyses',
                      data: trendEntries.map(([, v]) => v),
                      fill: true,
                      borderColor: '#3b82f6',
                      pointBackgroundColor: '#1d4ed8',
                      tension: 0.35,
                      backgroundColor: (ctx) => {
                        const { chart } = ctx;
                        const { ctx: c, chartArea } = chart as any;
                        if (!chartArea) return 'rgba(59,130,246,0.15)';
                        const gradient = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        gradient.addColorStop(0, 'rgba(59,130,246,0.25)');
                        gradient.addColorStop(1, 'rgba(59,130,246,0.02)');
                        return gradient;
                      },
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  interaction: { mode: 'index', intersect: false },
                  plugins: {
                    legend: { display: false },
                    tooltip: {
                      enabled: true,
                      callbacks: {
                        title: (items) => (items[0] ? `Date: ${items[0].label}` : ''),
                        label: (item) => `Analyses: ${item.parsed.y}`,
                      },
                    },
                  },
                  scales: {
                    x: {
                      grid: { display: false },
                      ticks: { color: '#64748b' },
                    },
                    y: {
                      beginAtZero: true,
                      grid: { color: '#e2e8f0' },
                      ticks: { color: '#64748b', precision: 0 },
                    },
                  },
                }}
              />
            </div>
          </CardContent>
        </Card>

      </div>
    </SidebarLayout>
  );
}
