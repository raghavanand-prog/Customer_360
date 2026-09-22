import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/customers", label: "Customers" },
  { to: "/segments", label: "Segments" },
  { to: "/analytics", label: "Analytics" },
  { to: "/quality", label: "Data Quality" },
  { to: "/pipeline", label: "Pipeline Runs" },
  { to: "/system", label: "System Health" },
];

export default function Shell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 border-r border-surface-border bg-surface-raised flex flex-col">
        <div className="px-4 py-4 border-b border-surface-border">
          <div className="text-sm font-semibold tracking-tight text-ink">Customer360</div>
          <div className="text-[11px] text-ink-faint mt-0.5">Data Platform Console</div>
        </div>
        <nav className="flex-1 py-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm border-l-2 ${
                  isActive
                    ? "border-accent text-ink bg-white/[0.03]"
                    : "border-transparent text-ink-muted hover:text-ink hover:bg-white/[0.02]"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-surface-border text-xs">
          <div className="text-ink truncate">{user?.email}</div>
          <div className="text-ink-faint uppercase tracking-wide text-[10px] mt-0.5">
            {user?.roles.join(", ")}
          </div>
          <button onClick={logout} className="mt-2 text-ink-muted hover:text-danger transition-colors">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
