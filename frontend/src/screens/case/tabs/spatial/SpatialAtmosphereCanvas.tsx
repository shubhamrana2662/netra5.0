import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../../../../lib/motion";
import { mulberry32 } from "../graphEngine";

interface Props {
  pan: { x: number; y: number };
  zoom: number;
}

interface Particle {
  x: number;
  y: number;
  z: number;
  size: number;
  alpha: number;
  speed: number;
  phase: number;
}

export function SpatialAtmosphereCanvas({ pan, zoom }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Smooth pan/zoom damping
  const panRef = useRef(pan);
  const zoomRef = useRef(zoom);
  useEffect(() => {
    panRef.current = pan;
    zoomRef.current = zoom;
  }, [pan, zoom]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    const reduced = prefersReducedMotion();
    const count = reduced ? 30 : 75;
    const rnd = mulberry32(0x0a0b0e);

    const particles: Particle[] = [];
    for (let i = 0; i < count; i++) {
      particles.push({
        x: (rnd() - 0.5) * 2400,
        y: (rnd() - 0.5) * 1800,
        z: 50 + rnd() * 600,
        size: 0.8 + rnd() * 1.8,
        alpha: 0.08 + rnd() * 0.22,
        speed: 0.4 + rnd() * 0.8,
        phase: rnd() * Math.PI * 2,
      });
    }

    let width = 0;
    let height = 0;

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);

    let raf = 0;
    const t0 = performance.now();

    let curPanX = pan.x;
    let curPanY = pan.y;
    let curZoom = zoom;

    const render = (time: number) => {
      // Damped smooth camera sync
      curPanX += (panRef.current.x - curPanX) * 0.12;
      curPanY += (panRef.current.y - curPanY) * 0.12;
      curZoom += (zoomRef.current - curZoom) * 0.12;

      // 1. Clear deep obsidian background
      ctx.fillStyle = "#0A0B0E";
      ctx.fillRect(0, 0, width, height);

      // Subtle radial dark gradient
      const grad = ctx.createRadialGradient(
        width * 0.5,
        height * 0.5,
        width * 0.15,
        width * 0.5,
        height * 0.5,
        width * 0.75
      );
      grad.addColorStop(0, "#0F1218");
      grad.addColorStop(1, "#0A0B0E");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);

      // 2. Subtle Coordinate Grid & Crosshairs (Deep Atmosphere)
      ctx.save();
      const gridSpacing = 160 * curZoom;
      const ox = ((curPanX % gridSpacing) + gridSpacing) % gridSpacing;
      const oy = ((curPanY % gridSpacing) + gridSpacing) % gridSpacing;

      ctx.strokeStyle = "rgba(255, 255, 255, 0.02)";
      ctx.lineWidth = 1;

      // Vertical lines
      for (let x = ox; x < width; x += gridSpacing) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      // Horizontal lines
      for (let y = oy; y < height; y += gridSpacing) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Faint subtle coordinate crosses at intersections
      ctx.strokeStyle = "rgba(241, 241, 238, 0.06)";
      for (let x = ox; x < width; x += gridSpacing) {
        for (let y = oy; y < height; y += gridSpacing) {
          ctx.beginPath();
          ctx.moveTo(x - 3, y);
          ctx.lineTo(x + 3, y);
          ctx.moveTo(x, y - 3);
          ctx.lineTo(x, y + 3);
          ctx.stroke();
        }
      }
      ctx.restore();

      // 3. Ambient 3D Particle Starfield with Parallax
      ctx.save();
      const cx = width * 0.5;
      const cy = height * 0.5;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        // Subtle organic sine drift
        const dx = p.x + Math.sin(time * 0.00025 * p.speed + p.phase) * 15;
        const dy = p.y + Math.cos(time * 0.00020 * p.speed + p.phase * 1.2) * 12;

        // Depth projection with parallax response
        const pScale = 400 / (400 + p.z);
        const parallaxX = (curPanX - cx) * (pScale * 0.45);
        const parallaxY = (curPanY - cy) * (pScale * 0.45);

        const screenX = cx + (dx * curZoom * pScale) + parallaxX;
        const screenY = cy + (dy * curZoom * pScale) + parallaxY;

        if (screenX < -20 || screenX > width + 20 || screenY < -20 || screenY > height + 20) {
          continue;
        }

        const alpha = p.alpha * Math.min(1.0, curZoom * 1.2);
        ctx.beginPath();
        ctx.arc(screenX, screenY, p.size * pScale * Math.max(0.6, curZoom), 0, Math.PI * 2);
        ctx.fillStyle = `rgba(241, 241, 238, ${alpha.toFixed(3)})`;
        ctx.fill();
      }
      ctx.restore();
    };

    const loop = (now: number) => {
      render(now - t0);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 1,
        pointerEvents: "none",
        overflow: "hidden",
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          display: "block",
          width: "100%",
          height: "100%",
        }}
      />
    </div>
  );
}
