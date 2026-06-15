"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Check } from "lucide-react";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "forever",
    features: ["5 videos/month", "All pipelines", "Manual upload"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$29",
    period: "/month",
    features: ["100 videos/month", "All pipelines", "Auto-upload to TikTok", "Scheduling"],
  },
  {
    id: "agency",
    name: "Agency",
    price: "$99",
    period: "/month",
    features: ["Unlimited videos", "All pipelines", "Multi-account TikTok", "Scheduling", "Priority support"],
  },
];

export default function BillingPage() {
  const [tier, setTier] = useState("free");
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    api.me().then((u) => setTier(u.subscription_tier)).catch(() => {});
  }, []);

  async function checkout(planId: string) {
    if (planId === "free") return;
    setLoading(planId);
    try {
      const res = await api.checkoutUrl(planId);
      window.location.href = res.url;
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(null);
    }
  }

  async function portal() {
    try {
      const res = await api.portalUrl();
      window.location.href = res.url;
    } catch (err: any) {
      alert(err.message);
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Billing</h1>
      <p className="text-gray-400 text-sm mb-8">
        Current plan: <span className="text-brand font-semibold capitalize">{tier}</span>
        {tier !== "free" && (
          <button onClick={portal} className="ml-4 text-gray-400 hover:text-gray-100 text-xs underline transition">
            Manage subscription
          </button>
        )}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = tier === plan.id;
          return (
            <div
              key={plan.id}
              className={`bg-gray-900 border rounded-xl p-5 flex flex-col ${isCurrent ? "border-brand" : "border-gray-800"}`}
            >
              <p className="font-bold text-lg">{plan.name}</p>
              <p className="text-2xl font-bold text-brand mt-1">
                {plan.price}<span className="text-sm text-gray-400 font-normal">{plan.period}</span>
              </p>
              <ul className="mt-4 space-y-2 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
                    <Check size={14} className="text-brand shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <button
                disabled={isCurrent || loading === plan.id}
                onClick={() => checkout(plan.id)}
                className={`mt-5 py-2 rounded-lg text-sm font-medium transition ${
                  isCurrent
                    ? "bg-brand/20 text-brand cursor-default"
                    : "bg-brand hover:bg-brand-dark text-white disabled:opacity-50"
                }`}
              >
                {isCurrent ? "Current plan" : loading === plan.id ? "Loading..." : `Upgrade to ${plan.name}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
