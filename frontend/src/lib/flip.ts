import { useEffect, type RefObject } from "react";

let captured: { x: number; y: number; width: number } | null = null;

export function captureRect(el: HTMLElement | null): void {
  if (!el) return;
  const r = el.getBoundingClientRect();
  captured = { x: r.x, y: r.y, width: r.width };
}

export function useFlipIn(ref: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const el = ref.current;
    const from = captured;
    captured = null;
    if (!el || !from) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    try {
      const to = el.getBoundingClientRect();
      if (!to.width || !to.height || !from.width || !isFinite(from.width / to.width)) {
        return;
      }
      if (typeof el.animate !== "function") return;
      el.animate(
        [
          { transform: `translate(${from.x - to.x}px, ${from.y - to.y}px) scale(${from.width / to.width})`, transformOrigin: "left top" },
          { transform: "none", transformOrigin: "left top" },
        ],
        { duration: 420, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
      );
    } catch (e) {
      // Fail gracefully without crashing the component tree
      console.warn("Flip animation skipped:", e);
    }
  }, [ref]);
}
