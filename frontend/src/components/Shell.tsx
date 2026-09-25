import { Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { reveal, slideTo } from "../lib/motion";
import { Icon } from "./Icons";
import { SkeletonTiles, SkeletonTable, Skeleton } from "./Common";

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
  icon: (typeof Icon)[keyof typeof Icon];
}

// Grouped by what the operator is looking at: the customer data itself, or
// the platform that produces it.
const NAV_GROUPS: { label?: string; items: NavItem[] }[] = [
  { items: [{ to: "/", label: "Overview", end: true, icon: Icon.Overview }] },
  {
    label: "Customer data",
    items: [
      { to: "/customers", label: "Customers", icon: Icon.Customers },
      { to: "/segments", label: "Segments", icon: Icon.Segments },
      { to: "/analytics", label: "Analytics", icon: Icon.Analytics },
    ],
  },
  {
    label: "Platform",
    items: [
      { to: "/quality", label: "Data Quality", icon: Icon.Quality },
      { to: "/pipeline", label: "Pipeline Runs", icon: Icon.Pipeline },
      { to: "/system", label: "System Health", icon: Icon.Health },
    ],
  },
];

function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const box = size === "sm" ? "h-6 w-6" : "h-7 w-7";
  return (
    <div className={`${box} rounded-md bg-accent/15 border border-accent/30 flex items-center justify-center shrink-0`}>
      <div className="h-2 w-2 rounded-full bg-accent" />
    </div>
  );
}

function NavEntry({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const ItemIcon = item.icon;
  return (
    <li>
      <NavLink
        to={item.to}
        end={item.end}
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
              className={`shrink-0 transition-[color,transform] duration-200 ease-out-quart motion-safe:group-hover:translate-x-px ${
                isActive ? "text-accent" : "text-ink-faint group-hover:text-ink-muted"
              }`}
            />
            <span className="truncate">{item.label}</span>
          </>
        )}
      </NavLink>
    </li>
  );
}

/** Grouped nav with a single accent marker that glides to the active item, across groups. */
function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();
  const listRef = useRef<HTMLDivElement>(null);
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
    // Rect delta rather than offsetTop: group labels put items on fractional
    // positions, and offsetTop rounds to whole pixels.
    const y = active.getBoundingClientRect().top - list.getBoundingClientRect().top;
    slideTo(marker, y + 6, active.offsetHeight - 12, !placed.current);
    placed.current = true;
  }, [location.pathname]);

  // The marker is positioned relative to this wrapper (the nearest positioned
  // ancestor of every link), so offsetTop stays correct across groups.
  return (
    <div ref={listRef} className="relative px-2">
      <span
        ref={markerRef}
        data-nav-marker
        className="absolute left-2 top-0 w-[2px] rounded-full bg-accent opacity-0 pointer-events-none"
        aria-hidden="true"
      />
      {NAV_GROUPS.map((group, gi) => (
        <div key={group.label ?? gi} className={gi > 0 ? "mt-5" : ""}>
          {group.label && (
            <div className="px-2 pb-1.5 stat-label" id={`nav-group-${gi}`}>
              {group.label}
            </div>
          )}
          <ul className="space-y-0.5" aria-labelledby={group.label ? `nav-group-${gi}` : undefined}>
            {group.items.map((item) => (
              <NavEntry key={item.to} item={item} onNavigate={onNavigate} />
            ))}
          </ul>
        </div>
      ))}
    </div>
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
        <NavList onNavigate={onNavigate} />
      </nav>
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
    window.scrollTo(0, 0);
    if (!pageRef.current) return;
    return reveal([pageRef.current], { distance: 6, duration: 320 });
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false);
    };
    const menuButton = menuButtonRef.current;
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    drawerRef.current?.querySelector<HTMLElement>("a")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      menuButton?.focus();
    };
  }, [drawerOpen]);

  return (
    <div className="min-h-screen lg:flex">
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
