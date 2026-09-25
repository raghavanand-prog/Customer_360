import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div role="status" aria-live="polite" className="min-h-screen flex flex-col items-center justify-center gap-3">
        <div className="h-7 w-7 rounded-md bg-accent/15 border border-accent/30 flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-accent motion-safe:animate-soft-pulse" />
        </div>
        <span className="text-xs text-ink-faint">Restoring session…</span>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
