import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../api/client";

/**
 * Route guard for the authenticated app shell. When there is no valid token we
 * redirect to /login, preserving the attempted destination in `next` so the
 * user lands where they intended after signing in. The public landing page and
 * /login itself are not wrapped by this guard.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (!isAuthenticated()) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <>{children}</>;
}
