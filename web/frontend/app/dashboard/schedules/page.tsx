"use client";
import { useEffect, useState } from "react";
import { api, type Schedule } from "@/lib/api";
import { Trash2, ToggleLeft, ToggleRight, Plus } from "lucide-react";

const PIPELINES = ["reddit","brat","montage","stocks_dca","stocks_compare","familyguy","movies"];

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ label: "", pipeline: "reddit", cron_expr: "0 9 * * *", params: "{}" });
  const [error, setError] = useState("");

  async function load() {
    setSchedules(await api.listSchedules());
  }

  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const params = JSON.parse(form.params);
      await api.createSchedule({ label: form.label, pipeline: form.pipeline, cron_expr: form.cron_expr, params, is_active: true });
      setShowForm(false);
      setForm({ label: "", pipeline: "reddit", cron_expr: "0 9 * * *", params: "{}" });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function toggle(s: Schedule) {
    await api.updateSchedule(s.id, { is_active: !s.is_active });
    load();
  }

  async function del(id: string) {
    await api.deleteSchedule(id);
    setSchedules((s) => s.filter((x) => x.id !== id));
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Schedules</h1>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-brand hover:bg-brand-dark text-white text-sm font-medium px-4 py-2 rounded-lg transition">
          <Plus size={14} /> New schedule
        </button>
      </div>
      {showForm && (
        <form onSubmit={create} className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 space-y-3">
          <h2 className="font-semibold">New Schedule</h2>
          <input placeholder="Label" value={form.label} onChange={(e) => setForm({...form, label: e.target.value})} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand" />
          <select value={form.pipeline} onChange={(e) => setForm({...form, pipeline: e.target.value})} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand">
            {PIPELINES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input placeholder="Cron (e.g. 0 9 * * *)" value={form.cron_expr} onChange={(e) => setForm({...form, cron_expr: e.target.value})} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-brand" required />
          <textarea placeholder='Params JSON e.g. {"subreddit":"AmItheAsshole"}' value={form.params} onChange={(e) => setForm({...form, params: e.target.value})} rows={3} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-brand" />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" className="bg-brand hover:bg-brand-dark text-white text-sm font-medium px-4 py-2 rounded-lg transition">Create</button>
            <button type="button" onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-100 text-sm px-4 py-2 rounded-lg transition">Cancel</button>
          </div>
        </form>
      )}
      <div className="space-y-3">
        {schedules.length === 0 && <p className="text-gray-500 text-sm">No schedules yet.</p>}
        {schedules.map((s) => (
          <div key={s.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-100">{s.label || s.pipeline}</p>
              <p className="text-xs text-gray-500 font-mono">{s.cron_expr} · {s.pipeline}</p>
              {s.last_run_at && <p className="text-xs text-gray-600">Last run: {new Date(s.last_run_at).toLocaleString()}</p>}
            </div>
            <button onClick={() => toggle(s)} className="text-gray-400 hover:text-brand transition">
              {s.is_active ? <ToggleRight size={24} className="text-brand" /> : <ToggleLeft size={24} />}
            </button>
            <button onClick={() => del(s.id)} className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-red-400 transition">
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
