"use client";
import { useState } from "react";
import { api } from "@/lib/api";

const PIPELINES = [
  { id: "reddit", label: "Reddit Story" },
  { id: "brat", label: "BRAT Lyric Video" },
  { id: "montage", label: "Luxury Montage" },
  { id: "stocks_dca", label: "Stock DCA Chart" },
  { id: "stocks_compare", label: "Stock Comparison" },
  { id: "familyguy", label: "Family Guy Split-Screen" },
  { id: "movies", label: "Movie Clip" },
];

interface Props {
  onCreated: () => void;
}

export default function PipelineForm({ onCreated }: Props) {
  const [pipeline, setPipeline] = useState("reddit");
  const [params, setParams] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function setParam(key: string, value: string) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const parsed: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(params)) {
        if (v === "") continue;
        const num = Number(v);
        parsed[k] = isNaN(num) ? v : num;
      }
      if (pipeline === "stocks_compare" && params.tickers) {
        parsed.tickers = params.tickers.split(",").map((t) => t.trim());
        if (params.names) parsed.names = params.names.split(",").map((n) => n.trim());
      }
      await api.createJob(pipeline, parsed);
      setParams({});
      onCreated();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
      <h2 className="font-semibold text-gray-100">Generate Video</h2>
      <div>
        <label className="text-xs text-gray-400 mb-1 block">Pipeline</label>
        <select
          value={pipeline}
          onChange={(e) => { setPipeline(e.target.value); setParams({}); }}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand"
        >
          {PIPELINES.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </div>

      {pipeline === "reddit" && (
        <Field label="Subreddit (optional)" placeholder="AmItheAsshole" onChange={(v) => setParam("subreddit", v)} value={params.subreddit ?? ""} />
      )}
      {pipeline === "brat" && (
        <>
          <Field label="Music file path" placeholder="/app/assets/music/song.mp3" required onChange={(v) => setParam("music_path", v)} value={params.music_path ?? ""} />
          <Field label="Artist (optional)" placeholder="Charli XCX" onChange={(v) => setParam("artist", v)} value={params.artist ?? ""} />
        </>
      )}
      {pipeline === "montage" && (
        <>
          <Field label="Music file path (optional)" placeholder="/app/assets/music/sigma/track.mp3" onChange={(v) => setParam("music_path", v)} value={params.music_path ?? ""} />
          <Field label="Cut every N beats" placeholder="2" onChange={(v) => setParam("every_n_beats", v)} value={params.every_n_beats ?? ""} />
        </>
      )}
      {pipeline === "stocks_dca" && (
        <>
          <Field label="Ticker" placeholder="BTC-USD" required onChange={(v) => setParam("ticker", v)} value={params.ticker ?? ""} />
          <Field label="Name" placeholder="Bitcoin" required onChange={(v) => setParam("name", v)} value={params.name ?? ""} />
          <Field label="Start year" placeholder="2020" required onChange={(v) => setParam("year", v)} value={params.year ?? ""} />
          <Field label="Monthly investment ($)" placeholder="100" onChange={(v) => setParam("monthly", v)} value={params.monthly ?? ""} />
        </>
      )}
      {pipeline === "stocks_compare" && (
        <>
          <Field label="Tickers (comma-separated)" placeholder="BTC-USD,ETH-USD,SOL-USD" required onChange={(v) => setParam("tickers", v)} value={params.tickers ?? ""} />
          <Field label="Names (comma-separated)" placeholder="Bitcoin,Ethereum,Solana" onChange={(v) => setParam("names", v)} value={params.names ?? ""} />
          <Field label="Start year" placeholder="2020" required onChange={(v) => setParam("year", v)} value={params.year ?? ""} />
          <Field label="Initial investment ($)" placeholder="1000" onChange={(v) => setParam("investment", v)} value={params.investment ?? ""} />
        </>
      )}
      {(pipeline === "familyguy" || pipeline === "movies") && (
        <>
          <Field label="Parts" placeholder="3" onChange={(v) => setParam("parts", v)} value={params.parts ?? ""} />
          <Field label="Duration per part (seconds)" placeholder="120" onChange={(v) => setParam("duration", v)} value={params.duration ?? ""} />
        </>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-brand hover:bg-brand-dark disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition"
      >
        {loading ? "Queuing..." : "Generate"}
      </button>
    </form>
  );
}

function Field({
  label, placeholder, value, onChange, required
}: {
  label: string; placeholder: string; value: string;
  onChange: (v: string) => void; required?: boolean;
}) {
  return (
    <div>
      <label className="text-xs text-gray-400 mb-1 block">{label}</label>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand"
      />
    </div>
  );
}
