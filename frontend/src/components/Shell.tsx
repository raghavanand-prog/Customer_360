import { Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { lockScroll, reveal, scrollToTop, slideTo } from "../lib/motion";
import { RouteProgress } from "./Motion";
import { SidebarStatus } from "./OverviewPanels";
import { Icon } from "./Icons";
import { SkeletonTiles, SkeletonTable, Skeleton } from "./Common";

const NAV = [
  { to: "/", label: "Overview", end: true, icon: Icon.Overview },
  { to: "/customers", label: "Customers", icon: Icon.Customers },
  { to: "/segments", label: "Segments", icon: Icon.Segments },
  { to: "/analytics", label: "Analytics", icon: Icon.Analytics },
  { to: "/quality", label: "Data Quality", icon: Icon.Quality },
  { to: "/pipeline", label: "Pipeline Runs", icon: Icon.Pipeline },
  { to: "/system", label: "System Health", icon: Icon.Health },
];

function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const box = size === "sm" ? "h-6 w-6" : "h-7 w-7";
  return (
    <div className={`${box} rounded-md bg-accent/15 border border-accent/30 flex items-center justify-center shrink-0`}>
      <div className="h-2 w-2 rounded-full bg-accent" />
    </div>
  );
}

/** Nav list with a single accent marker that glides to the active item. */
function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();
  const listRef = useRef<HTMLUListElement>(null);
  const markerRef = useRef<HTMLSpanElement>(null);
  const placed = useRef(false);

  useLayoutEffect(() => {
    const list = listRef.current;
    const marker = markerRef.current;
    if (!list || !marker) return;
    const active = list.querySelector<HTMLElement>('a[aria-current="page"]');
    if (!active) {
      marker.style.opacity = "0";
      return;
    }
    slideTo(marker, active.offsetTop + 6, active.offsetHeight - 12, !placed.current);
    placed.current = true;
  }, [location.pathname]);

  return (
    <ul ref={listRef} className="relative px-2 space-y-0.5">
      <span
        ref={markerRef}
        className="absolute left-2 top-0 w-[2px] rounded-full bg-accent opacity-0 pointer-events-none"
        aria-hidden="true"
      />
      {NAV.map(({ to, label, end, icon: ItemIcon }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-md pl-4 pr-3 py-2 text-sm transition-colors duration-150 ${
                isActive ? "text-ink bg-white/[0.045]" : "text-ink-muted hover:text-ink hover:bg-white/[0.025]"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <ItemIcon
                  className={`shrink-0 transition-colors duration-150 ${
                    isActive ? "text-accent" : "text-ink-faint group-hover:text-ink-muted"
                  }`}
                />
                <span className="truncate">{label}</span>
              </>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function UserFooter() {
  const { user, logout } = useAuth();
  const initials = (user?.email ?? "?").slice(0, 2).toUpperCase();
  return (
    <div className="px-3 py-3 border-t border-surface-border">
      <div className="flex items-center gap-2.5 px-1">
        <div
          className="h-7 w-7 rounded-full bg-white/[0.06] border border-surface-border flex items-center justify-center text-2xs font-semibold text-ink-muted shrink-0"
          aria-hidden="true"
        >
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs text-ink truncate" title={user?.email}>
            {user?.email}
          </div>
          <div className="text-2xs text-ink-faint uppercase tracking-[0.08em] mt-0.5 truncate">{user?.roles.join(", ")}</div>
        </div>
        <button
          onClick={logout}
          className="h-7 w-7 inline-flex items-center justify-center rounded-md text-ink-faint hover:text-danger hover:bg-danger/10 transition-colors"
          aria-label="Sign out"
          title="Sign out"
        >
          <Icon.Logout size={14} />
        </button>
      </div>
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <div className="px-4 h-14 flex items-center gap-2.5 border-b border-surface-border shrink-0">
        <BrandMark />
        <div className="min-w-0">
          <div className="text-sm font-semibold tracking-tight text-ink leading-none">Customer360</div>
          <div className="text-2xs text-ink-faint mt-1 leading-none">Data Platform Console</div>
        </div>
      </div>
      <nav aria-label="Primary" className="flex-1 py-3 overflow-y-auto">
        <div className="px-4 pb-2 stat-label">Workspace</div>
        <NavList onNavigate={onNavigate} />
      </nav>
      <SidebarStatus />
      <UserFooter />
    </>
  );
}

function PageFallback() {
  return (
    <div role="status" aria-live="polite" className="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <span className="sr-only">Loading page…</span>
      <Skeleton className="h-5 w-48" />
      <SkeletonTiles />
      <SkeletonTable rows={5} />
    </div>
  );
}

export default function Shell() {
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pageRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  // Route change: reset scroll, and a short fade/rise so navigation reads as
  // a deliberate change of context rather than a flash of new content.
  useLayoutEffect(() => {
    scrollToTop();
    if (!pageRef.current) return;
    return reveal([pageRef.current], { distance: 16, duration: 700 });
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false);
    };
    const menuButton = menuButtonRef.current;
    document.addEventListener("keydown", onKey);
    lockScroll(true);
    drawerRef.current?.querySelector<HTMLElement>("a")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      lockScroll(false);
      menuButton?.focus();
    };
  }, [drawerOpen]);

  return (
    <div className="min-h-screen lg:flex">
      <RouteProgress routeKey={location.pathname} />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-3 focus:py-2 focus:rounded-md focus:bg-surface-raised focus:text-ink focus:border focus:border-accent/50 text-sm"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r border-surface-border bg-surface-raised sticky top-0 h-screen">
        <SidebarContent />
      </aside>

      {/* Mobile / tablet top bar */}
      <div className="lg:hidden sticky top-0 z-30 h-14 flex items-center justify-between px-4 border-b border-surface-border bg-surface-raised/95 backdrop-blur supports-[backdrop-filter]:bg-surface-raised/80">
        <div className="flex items-center gap-2.5">
          <BrandMark size="sm" />
          <span className="text-sm font-semibold tracking-tight text-ink">Customer360</span>
        </div>
        <button
          ref={menuButtonRef}
          onClick={() => setDrawerOpen(true)}
          className="h-9 w-9 inline-flex items-center justify-center rounded-md text-ink-muted hover:text-ink hover:bg-white/[0.05] transition-colors"
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          aria-controls="mobile-nav"
        >
          <Icon.Menu size={18} />
        </button>
      </div>

      {/* Mobile drawer: always mounted so it can transition; inert while closed. */}
      <div className={`lg:hidden fixed inset-0 z-40 ${drawerOpen ? "" : "pointer-events-none"}`} inert={!drawerOpen}>
        <div
          className={`absolute inset-0 bg-black/60 transition-opacity duration-300 ${drawerOpen ? "opacity-100" : "opacity-0"}`}
          onClick={() => setDrawerOpen(false)}
          aria-hidden="true"
        />
        <div
          id="mobile-nav"
          ref={drawerRef}
          data-lenis-prevent
          role="dialog"
          aria-modal="true"
          aria-label="Navigation"
          className={`absolute inset-y-0 left-0 w-72 max-w-[85vw] flex flex-col bg-surface-raised border-r border-surface-border shadow-raised transition-transform duration-300 ease-out-quart ${
            drawerOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <button
            onClick={() => setDrawerOpen(false)}
            className="absolute right-3 top-3.5 h-7 w-7 inline-flex items-center justify-center rounded-md text-ink-faint hover:text-ink hover:bg-white/[0.05] transition-colors"
            aria-label="Close navigation"
          >
            <Icon.Close size={14} />
          </button>
          {drawerOpen && <SidebarContent onNavigate={() => setDrawerOpen(false)} />}
        </div>
      </div>

      <main id="main" tabIndex={-1} className="flex-1 min-w-0 focus:outline-none">
        <div key={location.pathname} ref={pageRef}>
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
