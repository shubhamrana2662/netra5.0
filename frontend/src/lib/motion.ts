// CyberDrishti Unified Motion System Tokens & Physics Primitives

export const EASE_OUT: [number, number, number, number] = [0.16, 1, 0.3, 1];
export const EASE_IN_OUT: [number, number, number, number] = [0.45, 0, 0.25, 1];
export const EASE_SOFT: [number, number, number, number] = [0.65, 0, 0.35, 1];

export const SPRING_TACTILE = {
  type: "spring",
  stiffness: 420,
  damping: 30,
  mass: 0.8
} as const;

export const SPRING_GENTLE = {
  type: "spring",
  stiffness: 280,
  damping: 26,
  mass: 1.0
} as const;

export const DUR = {
  instant: 0.08,   // Active press, toggle, checkbox
  micro: 0.16,     // Button hover, tooltip, badge update
  interface: 0.24, // Tab switch, dropdown pop, filter badge
  panel: 0.32,     // Side drawer, modal, detail inspector
  page: 0.32,      // Major route transition
  structural: 0.44,// App entry compression, layout re-run
  spatial: 0.52    // Deep 3D camera travel
} as const;

/** Stagger cadence for orchestrated composition reveals (≤ 35ms per item) */
export const STAGGER = 0.035;

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
