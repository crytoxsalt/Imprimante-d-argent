"use client";
import { useEffect, useState } from "react";
import { api, type AnalyticsSummary } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);

  useEffect(() => { api.analytics().then(setData).catch(() => {}); }, []);

  if (!data) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Analytics</h1>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Total videos generated" value={data.total_jobs} />
        <Stat label="Success rate" value={`${(data.success_rate * 100).toFixed(1)}%`} />
      </div>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-4">Videos by pipeline</h2>
        <div className="space-y-2">
          {Object.entries(data.jobs_by_pipeline).map(([pipeline, count]) => (
            <div key={pipeline} className="flex items-center gap-3">
              <span className="text-xs text-gray-400 w-32 capitalize">{pipeline.replace("_", " ")}</span>
              <div className="flex-1 bg-gray-800 rounded-full h-2">
                <div
                  className="bg-brand h-2 rounded-full"
                  style={{ width: `${Math.min(100, (count / data.total_jobs) * 100)}%` }}
                />
              </div>
              <span className="text-xs text-gray-400 w-8 text-right">{count}</span>
            </div>
          ))}
        </div>
      </div>
      {data.jobs_last_30_days.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-400 mb-4">Videos last 30 days</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.jobs_last_30_days}>
              <XAxis dataKey="day" tick={{ fill: "#6b7280", fontSize: 10 }} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
              <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-3xl font-bold text-brand">{value}</p>
      <p className="text-sm text-gray-400 mt-1">{label}</p>
    </div>
  );
}
