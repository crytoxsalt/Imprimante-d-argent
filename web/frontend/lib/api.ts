const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cashroll_token");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<{ id: string; email: string; subscription_tier: string }>("/auth/me"),

  createJob: (pipeline: string, params: Record<string, unknown>) =>
    request<Job>("/jobs/", { method: "POST", body: JSON.stringify({ pipeline, params }) }),

  listJobs: () => request<Job[]>("/jobs/"),

  getJob: (id: string) => request<Job>(`/jobs/${id}`),

  deleteJob: (id: string) => request(`/jobs/${id}`, { method: "DELETE" }),

  uploadToTikTok: (jobId: string, accountId: string) =>
    request(`/jobs/${jobId}/upload?account_id=${accountId}`, { method: "POST" }),

  listSchedules: () => request<Schedule[]>("/schedules/"),

  createSchedule: (data: Omit<Schedule, "id" | "created_at" | "last_run_at" | "next_run_at">) =>
    request<Schedule>("/schedules/", { method: "POST", body: JSON.stringify(data) }),

  updateSchedule: (id: string, data: Partial<Schedule>) =>
    request<Schedule>(`/schedules/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  deleteSchedule: (id: string) => request(`/schedules/${id}`, { method: "DELETE" }),

  listAccounts: () => request<TikTokAccount[]>("/accounts/"),

  addAccount: (label: string, cookies_json: string) =>
    request<TikTokAccount>("/accounts/", { method: "POST", body: JSON.stringify({ label, cookies_json }) }),

  deleteAccount: (id: string) => request(`/accounts/${id}`, { method: "DELETE" }),

  analytics: () => request<AnalyticsSummary>("/analytics/summary"),

  checkoutUrl: (tier: string) =>
    request<{ url: string }>(`/billing/checkout?tier=${tier}`, { method: "POST" }),

  portalUrl: () => request<{ url: string }>("/billing/portal"),
};

export interface Job {
  id: string;
  pipeline: string;
  params: Record<string, unknown>;
  status: "pending" | "running" | "done" | "failed";
  output_path?: string;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface Schedule {
  id: string;
  label: string;
  pipeline: string;
  params: Record<string, unknown>;
  cron_expr: string;
  is_active: boolean;
  last_run_at?: string;
  next_run_at?: string;
  created_at: string;
}

export interface TikTokAccount {
  id: string;
  label: string;
  is_active: boolean;
  created_at: string;
}

export interface AnalyticsSummary {
  total_jobs: number;
  jobs_by_pipeline: Record<string, number>;
  jobs_last_30_days: Array<{ day: string; count: number }>;
  success_rate: number;
}
