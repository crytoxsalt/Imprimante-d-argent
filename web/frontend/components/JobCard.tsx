"use client";
import { clsx } from "clsx";
import { Trash2, Upload, Eye } from "lucide-react";
import Link from "next/link";
import type { Job } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500/20 text-yellow-400",
  running: "bg-blue-500/20 text-blue-400",
  done: "bg-green-500/20 text-green-400",
  failed: "bg-red-500/20 text-red-400",
};

interface Props {
  job: Job;
  onDelete?: (id: string) => void;
  onUpload?: (id: string) => void;
}

export default function JobCard({ job, onDelete, onUpload }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold capitalize text-gray-100">{job.pipeline.replace("_", " ")}</span>
          <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", STATUS_COLORS[job.status])}>
            {job.status}
          </span>
        </div>
        <p className="text-xs text-gray-500 truncate">
          {new Date(job.created_at).toLocaleString()}
          {job.completed_at && ` · completed ${new Date(job.completed_at).toLocaleString()}`}
        </p>
        {job.error && <p className="text-xs text-red-400 mt-1 truncate">{job.error}</p>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Link
          href={`/dashboard/jobs/${job.id}`}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-100 transition"
          title="View logs"
        >
          <Eye size={16} />
        </Link>
        {job.status === "done" && onUpload && (
          <button
            onClick={() => onUpload(job.id)}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-brand transition"
            title="Upload to TikTok"
          >
            <Upload size={16} />
          </button>
        )}
        {onDelete && (
          <button
            onClick={() => onDelete(job.id)}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-red-400 transition"
            title="Delete"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
