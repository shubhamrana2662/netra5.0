import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { prefersReducedMotion } from "../lib/motion";
import { mulberry32 } from "../lib/random";
import s from "./enter.module.css";

const FIELD_COUNT = 28;
function fieldLayout(count = FIELD_COUNT) {
  const rnd = mulberry32(0x094213);
  const nodes = [{ x: 0.5, y: 0.42 }];
  for (let i = 1; i < count; i++) {
    nodes.push({ x: 0.06 + rnd() * 0.88, y: 0.06 + rnd() * 0.88 });
  }
  return nodes;
}

type NavFn = (path: string) => void;
let trigger: ((nav: NavFn) => void) | null = null;

export function startEnterTransition(nav: NavFn): void {
  try {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  } catch {
    // ignore
  }
  if (prefersReducedMotion()) { nav("/command"); return; }
  if (trigger) trigger(nav);
  else nav("/command");
}

const ORGANIZE_MS = 500; // §5 structural — the only choreographed transition
const SWAP_AT = 300;     // route swaps at 60% progress

function runOrganize(canvas: HTMLCanvasElement, nav: NavFn, done: () => void): () => void {
  const ctx = canvas.getContext("2d");
  if (!ctx) { nav("/command"); done(); return () => {}; }

  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = window.innerWidth;
  const h = window.innerHeight;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // The chaos organizes onto the app's actual structural lines.
  const cs = getComputedStyle(document.documentElement);
  const railX = parseFloat(cs.getPropertyValue("--rail-w")) || 64;
  const headY = parseFloat(cs.getPropertyValue("--header-h")) || 60;

  const layout = fieldLayout(FIELD_COUNT);
  const targets = layout.map((_, i) =>
    i < 13
      ? { x: railX, y: headY + (i / 12) * (h - headY) }            // rail vertical
      : { x: railX + ((i - 13) / (FIELD_COUNT - 14)) * (w - railX), y: headY }, // header horizontal
  );

  const easeOut = (p: number) => 1 - Math.pow(1 - p, 3);
  const t0 = performance.now();
  let swapped = false;
  let raf = 0;

  const frame = (now: number) => {
    const t = now - t0;
    const p = Math.min(1, t / ORGANIZE_MS);
    ctx.clearRect(0, 0, w, h);

    const lineA = Math.max(0, Math.min(1, (p - 0.45) / 0.55)) * 0.16;
    if (lineA > 0) {
      ctx.strokeStyle = `rgba(241, 241, 238, ${lineA.toFixed(3)})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(railX + 0.5, headY);
      ctx.lineTo(railX + 0.5, h);
      ctx.moveTo(railX, headY + 0.5);
      ctx.lineTo(w, headY + 0.5);
      ctx.stroke();
    }

    layout.forEach((n, i) => {
      const span = ORGANIZE_MS - (i % 7) * 18;
      const e = easeOut(Math.min(1, Math.max(0, (t - (i % 7) * 18) / span)));
      const x = n.x * w + (targets[i].x - n.x * w) * e;
      const y = n.y * h + (targets[i].y - n.y * h) * e;
      ctx.beginPath();
      ctx.arc(x, y, 2.5 - e, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(241, 241, 238, ${(0.8 - 0.35 * e).toFixed(3)})`;
      ctx.fill();
    });

    // crossfade into the shell during the final 40%
    canvas.style.opacity = String(p < 0.6 ? 1 : 1 - (p - 0.6) / 0.4);

    if (!swapped && t >= SWAP_AT) {
      swapped = true;
      try {
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
      } catch {}
      nav("/command");
    }
    if (t < ORGANIZE_MS) raf = requestAnimationFrame(frame);
    else done();
  };
  raf = requestAnimationFrame(frame);
  return () => cancelAnimationFrame(raf);
}

export function EnterOverlay() {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const busy = useRef(false);
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    trigger = (nav) => {
      if (busy.current) return;
      busy.current = true;
      setActive(true);
      requestAnimationFrame(() => {
        cancelRef.current = runOrganize(canvasRef.current!, nav, () => {
          setActive(false);
          busy.current = false;
          cancelRef.current = null;
        });
      });
    };
    return () => { trigger = null; cancelRef.current?.(); };
  }, [navigate]);

  if (!active) return null;
  return (
    <div className={s.overlay} aria-hidden="true">
      <canvas ref={canvasRef} className={s.canvas} />
    </div>
  );
}
