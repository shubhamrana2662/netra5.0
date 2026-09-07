import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * ScrollToTop: Enforces instantaneous reset of window and document scroll
 * on any route transition, preventing the "blank space" viewport bug when
 * navigating from tall pages (like Landing) into standard dashboards.
 */
export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    try {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    } catch {
      // ignore
    }
  }, [pathname]);

  return null;
}
