"use client";
import { useEffect, useState, useCallback } from "react";
import { api, type Job } from "@/lib/api";
import JobCard from "@/components/JobCard";
import PipelineForm from "@/components/PipelineForm";
import { RefreshCw } from "lucide-react";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listJobs();
      setJobs(data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  async function deleteJob(id: string) {
    await api.deleteJob(id);
    setJobs((j) => j.filter((x) => x.id !== id));
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Jobs</h1>
        <button onClick={refresh} className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 transition">
          <RefreshCw size={16} />
        </button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <PipelineForm onCreated={refresh} />
        </div>
        <div className="lg:col-span-2 space-y-3">
          {loading && <p className="text-gray-500 text-sm">Loading...</p>}
          {!loading && jobs.length === 0 && (
            <p className="text-gray-500 text-sm">No jobs yet. Generate your first video.</p>
          )}
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} onDelete={deleteJob} />
          ))}
        </div>
      </div>
    </div>
  );
}
