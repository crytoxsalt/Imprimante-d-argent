"use client";
import { useEffect, useState } from "react";
import { api, type TikTokAccount } from "@/lib/api";
import { Trash2, Plus } from "lucide-react";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<TikTokAccount[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [cookies, setCookies] = useState("");
  const [error, setError] = useState("");

  async function load() { setAccounts(await api.listAccounts()); }
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.addAccount(label, cookies);
      setShowForm(false);
      setLabel(""); setCookies("");
      load();
    } catch (err: any) { setError(err.message); }
  }

  async function del(id: string) {
    await api.deleteAccount(id);
    setAccounts((a) => a.filter((x) => x.id !== id));
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">TikTok Accounts</h1>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 bg-brand hover:bg-brand-dark text-white text-sm font-medium px-4 py-2 rounded-lg transition">
          <Plus size={14} /> Add account
        </button>
      </div>
      {showForm && (
        <form onSubmit={add} className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 space-y-3">
          <h2 className="font-semibold">Add TikTok Account</h2>
          <input placeholder="Label (e.g. @cashroll)" value={label} onChange={(e) => setLabel(e.target.value)} required className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand" />
          <textarea placeholder='Cookie JSON from tiktok-uploader' value={cookies} onChange={(e) => setCookies(e.target.value)} rows={5} required className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-brand" />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" className="bg-brand hover:bg-brand-dark text-white text-sm font-medium px-4 py-2 rounded-lg transition">Save</button>
            <button type="button" onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-100 text-sm px-4 py-2 rounded-lg transition">Cancel</button>
          </div>
        </form>
      )}
      <div className="space-y-3">
        {accounts.length === 0 && <p className="text-gray-500 text-sm">No accounts yet. Add your TikTok cookie to enable auto-upload.</p>}
        {accounts.map((a) => (
          <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
            <div className="flex-1">
              <p className="font-medium text-gray-100">{a.label}</p>
              <p className="text-xs text-gray-500">Added {new Date(a.created_at).toLocaleDateString()}</p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full ${a.is_active ? "bg-green-500/20 text-green-400" : "bg-gray-700 text-gray-400"}`}>
              {a.is_active ? "active" : "inactive"}
            </span>
            <button onClick={() => del(a.id)} className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-red-400 transition">
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
