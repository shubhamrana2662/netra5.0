/**
 * Adaptive quality for the login 3D scene.
 *
 * Tier is detected once from device signals, then governed at runtime: if the
 * rolling FPS drops below budget the tier degrades (particle draw counts, city
 * density, DPR, AA). All counts are read per-frame from `quality.level`, so a
 * degrade takes effect immediately without remounting the scene.
 */

export type TierName = "low" | "medium" | "high";

const LEVELS: Record<TierName, number> = { low: 0, medium: 1, high: 2 };

function detectTier(): TierName {
  if (typeof navigator === "undefined") return "medium";
  const nav = navigator as Navigator & { deviceMemory?: number; hardwareConcurrency?: number };
  const cores = nav.hardwareConcurrency ?? 4;
  const mem = nav.deviceMemory ?? 4;
  const coarsePointer = window.matchMedia?.("(pointer: coarse)").matches ?? false;
  const mobileUA = /android|iphone|ipad|mobile/i.test(navigator.userAgent);
  let tier: TierName = cores >= 8 && mem >= 8 ? "high" : cores >= 4 && mem >= 4 ? "medium" : "low";
  if (coarsePointer || mobileUA) tier = tier === "high" ? "medium" : "low";
  // Weak GPU strings — only checked when the browser exposes them.
  try {
    const gl = document.createElement("canvas").getContext("webgl2") ?? document.createElement("canvas").getContext("webgl");
    if (gl) {
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      const renderer = ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : "";
      if (/intel.*(hd|uhd)\s*(5|6)[0-9]{2}|mali|powervr|adreno\s*[1-5]|swiftshader|software/i.test(renderer)) {
        tier = tier === "high" ? "medium" : "low";
      }
    }
  } catch {
    /* probing is best-effort */
  }
  return tier;
}

const COUNTS = {
  // [low, medium, high]
  particles: [700, 1500, 2600] as const,
  city: [90, 190, 340] as const,
  trail: [90, 160, 240] as const,
  dust: [14, 22, 30] as const,
};

export const quality = {
  level: LEVELS[detectTier()],
  maxDegrades: 2,

  get tier(): TierName {
    return (["low", "medium", "high"] as TierName[])[this.level];
  },
  isMobileLike(): boolean {
    return this.level <= 0;
  },
  count(kind: keyof typeof COUNTS): number {
    return COUNTS[kind][this.level];
  },
  dprMax(): number {
    return [1, 1.5, 1.75][this.level];
  },
  antialias(): boolean {
    return this.level > 0;
  },
  canDegrade(): boolean {
    return this.level > 0;
  },
  degrade(): void {
    if (this.canDegrade()) this.level -= 1;
  },
};

/** True when the user asked the OS for reduced motion. */
export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}
