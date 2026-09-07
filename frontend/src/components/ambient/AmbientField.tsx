import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../../lib/motion";
import { mulberry32 } from "../../lib/random";

interface AmbientPoint {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  baseAlpha: number;
  phase: number;
}

/**
 * AmbientField: Persistent subtle intelligence background layer.
 * Extremely low-contrast and performance-optimized (≤ 0.5% CPU).
 */
export function AmbientField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    if (prefersReducedMotion()) return;

    const rnd = mulberry32(0xcd042);
    const count = 35;
    const points: AmbientPoint[] = [];

    let w = 0, h = 0;
    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize, { passive: true });

    for (let i = 0; i < count; i++) {
      points.push({
        x: rnd() * w,
        y: rnd() * h,
        vx: (rnd() - 0.5) * 0.12,
        vy: (rnd() - 0.5) * 0.10,
        radius: 0.8 + rnd() * 1.2,
        baseAlpha: 0.025 + rnd() * 0.035, // Barely perceptible (2.5% - 6% alpha)
        phase: rnd() * Math.PI * 2
      });
    }

    let raf = 0;
    let visible = !document.hidden;
    let lastT = performance.now();

    const draw = (now: number) => {
      const dt = Math.min(64, now - lastT);
      lastT = now;

      ctx.clearRect(0, 0, w, h);

      // Subtle atmospheric radial vignette
      const cx = w * 0.5;
      const cy = h * 0.45;
      const grad = ctx.createRadialGradient(cx, cy, 50, cx, cy, Math.max(w, h) * 0.7);
      grad.addColorStop(0, "rgba(22, 26, 36, 0.03)");
      grad.addColorStop(0.6, "rgba(14, 16, 22, 0.015)");
      grad.addColorStop(1, "rgba(10, 11, 14, 0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Draw faint drifting micro-signals
      for (let i = 0; i < points.length; i++) {
        const p = points[i];
        p.x += p.vx * (dt / 16);
        p.y += p.vy * (dt / 16);

        if (p.x < -10) p.x = w + 10;
        else if (p.x > w + 10) p.x = -10;
        if (p.y < -10) p.y = h + 10;
        else if (p.y > h + 10) p.y = -10;

        const pulse = 0.85 + 0.15 * Math.sin(now * 0.0008 + p.phase);
        const alpha = p.baseAlpha * pulse;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(241, 241, 238, ${alpha.toFixed(4)})`;
        ctx.fill();
      }
    };

    const loop = (now: number) => {
      draw(now);
      raf = requestAnimationFrame(loop);
    };

    const start = () => { if (!raf && visible) raf = requestAnimationFrame(loop); };
    const stop = () => { if (raf) { cancelAnimationFrame(raf); raf = 0; } };

    const onVis = () => {
      visible = !document.hidden;
      if (visible) start();
      else stop();
    };
    document.addEventListener("visibilitychange", onVis);

    start();

    return () => {
      stop();
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
        opacity: 0.85
      }}
      aria-hidden="true"
    />
  );
}
