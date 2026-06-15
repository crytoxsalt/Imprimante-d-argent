"use client";
import { useEffect, useRef, useState } from "react";
import { api, type Job } from "@/lib/api";
import { clsx } from "clsx";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STATUS_COLORS: Record<string, string> = {
  pending: "text-yellow-400",
  running: "text-blue-400",
  done: "text-green-400",
  failed: "text-red-400",
};

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const logsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getJob(params.id).then(setJob);
  }, [params.id]);

  useEffect(() => {
    const token = localStorage.getItem("cashroll_token");
    const es = new EventSource(`${API}/jobs/${params.id}/logs?token=${token}`);
    es.onmessage = (e) => {
      setLogs((l) => [...l, e.data]);
      setTimeout(() => logsRef.current?.scrollTo(0, logsRef.current.scrollHeight), 50);
    };
    return () => es.close();
  }, [params.id]);

  // Poll job status while running
  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const id = setInterval(async () => {
      const updated = await api.getJob(params.id);
      setJob(updated);
    }, 3000);
    return () => clearInterval(id);
  }, [job, params.id]);

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <Link href="/dashboard" className="flex items-center gap-2 text-gray-400 hover:text-gray-100 text-sm mb-6 transition">
        <ArrowLeft size={14} /> Back to jobs
      </Link>
      {job && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-lg font-bold capitalize">{job.pipeline.replace("_", " ")}</h1>
            <span className={clsx("text-sm font-medium", STATUS_COLORS[job.status])}>{job.status}</span>
          </div>
          <p className="text-xs text-gray-500">ID: {job.id}</p>
          <p className="text-xs text-gray-500">Created: {new Date(job.created_at).toLocaleString()}</p>
          {job.completed_at && (
            <p className="text-xs text-gray-500">Completed: {new Date(job.completed_at).toLocaleString()}</p>
          )}
          {job.output_path && (
            <div className="mt-3">
              <p className="text-xs text-gray-400 mb-1">Output:</p>
              <p className="text-xs text-brand font-mono break-all">{job.output_path}</p>
            </div>
          )}
          {job.error && (
            <div className="mt-3">
              <p className="text-xs text-red-400 mb-1">Error:</p>
              <pre className="text-xs text-red-300 bg-red-950/20 rounded p-2 overflow-auto max-h-32">{job.error}</pre>
            </div>
          )}
        </div>
      )}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-2">Live logs</h2>
        <div
          ref={logsRef}
          className="bg-gray-950 border border-gray-800 rounded-xl p-4 h-96 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5"
        >
          {logs.length === 0 && <span className="text-gray-600">Waiting for logs...</span>}
          {logs.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
