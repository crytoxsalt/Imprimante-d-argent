"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Video, Calendar, Users, BarChart2, CreditCard, LogOut } from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Jobs", icon: Video },
  { href: "/dashboard/schedules", label: "Schedules", icon: Calendar },
  { href: "/dashboard/accounts", label: "TikTok Accounts", icon: Users },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    localStorage.removeItem("cashroll_token");
    router.push("/login");
  }

  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col min-h-screen">
      <div className="px-6 py-5 border-b border-gray-800">
        <span className="text-xl font-bold text-brand">Cashroll</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition",
              pathname === href
                ? "bg-brand/10 text-brand"
                : "text-gray-400 hover:text-gray-100 hover:bg-gray-800"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="px-3 py-4 border-t border-gray-800">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 w-full text-left text-sm text-gray-400 hover:text-gray-100 hover:bg-gray-800 rounded-lg transition"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
