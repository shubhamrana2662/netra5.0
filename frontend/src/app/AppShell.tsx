import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { NavRail } from "../components/nav/NavRail";
import { BottomBar } from "../components/nav/BottomBar";
import { Header } from "../components/nav/Header";
import { CommandPalette } from "./CommandPalette";
import { AmbientField } from "../components/ambient/AmbientField";
import { page } from "./transitions";
import { useMediaQuery } from "../lib/useMediaQuery";
import { ErrorBoundary } from "../components/common/ErrorBoundary";
import s from "./shell.module.css";

const CMD_NAV: Record<string, string> = {
  "1": "/command",
  "2": "/investigations",
  "3": "/intelligence",
  "0": "/settings",
};

export function AppShell() {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const location = useLocation();
  const navigate = useNavigate();
  const viewRef = useRef<HTMLElement>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

  // Lock document and window scroll while inside the application shell
  useEffect(() => {
    if (typeof history !== "undefined" && "scrollRestoration" in history) {
      history.scrollRestoration = "manual";
    }

    const prevHtmlOverflow = document.documentElement.style.overflow;
    const prevBodyOverflow = document.body.style.overflow;
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    return () => {
      document.documentElement.style.overflow = prevHtmlOverflow;
      document.body.style.overflow = prevBodyOverflow;
    };
  }, []);

  // Reset scroll on view container and window on every route change
  useEffect(() => {
    try {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      if (viewRef.current) {
        viewRef.current.scrollTop = 0;
      }
      requestAnimationFrame(() => {
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
        if (viewRef.current) {
          viewRef.current.scrollTop = 0;
        }
      });
    } catch {
      // ignore
    }
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(o => !o);
      } else if (mod && e.key in CMD_NAV) {
        e.preventDefault();
        navigate(CMD_NAV[e.key]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  const baseKey = location.pathname.split("/").slice(0, 3).join("/");

  return (
    <div className={s.app}>
      <AmbientField />
      {isMobile ? <BottomBar /> : <NavRail />}
      <div className={s.frame}>
        <Header />
        <motion.main
          key={baseKey}
          ref={viewRef}
          className={s.view}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        >
          <ErrorBoundary locationKey={location.pathname}>
            <Outlet context={{ openPalette }} />
          </ErrorBoundary>
        </motion.main>
      </div>
      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </div>
  );
}
