/**
 * Canvas-generated textures for the login 3D world.
 * Everything is drawn locally (system monospace), so the scene has zero asset
 * downloads and stays crisp on any DPI.
 */
import { CanvasTexture, SRGBColorSpace, LinearFilter, type Texture } from "three";

const cache = new Map<string, Texture>();

function make(key: string, w: number, h: number, draw: (c: CanvasRenderingContext2D) => void): Texture {
  const hit = cache.get(key);
  if (hit) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (ctx) draw(ctx);
  const tex = new CanvasTexture(canvas);
  tex.colorSpace = SRGBColorSpace;
  tex.minFilter = LinearFilter;
  tex.magFilter = LinearFilter;
  tex.generateMipmaps = false;
  cache.set(key, tex);
  return tex;
}

/** Soft radial glow — the workhorse sprite for light in the scene. */
export function glowTexture(): Texture {
  return make("glow", 128, 128, (c) => {
    const g = c.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, "rgba(255,255,255,1)");
    g.addColorStop(0.22, "rgba(255,255,255,0.55)");
    g.addColorStop(0.55, "rgba(255,255,255,0.14)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    c.fillStyle = g;
    c.fillRect(0, 0, 128, 128);
  });
}

/** Thin expanding ring for investigator scan waves. */
export function ringTexture(): Texture {
  return make("ring", 256, 256, (c) => {
    c.strokeStyle = "rgba(255,255,255,0.95)";
    c.lineWidth = 5;
    c.shadowColor = "rgba(255,255,255,0.9)";
    c.shadowBlur = 14;
    c.beginPath();
    c.arc(128, 128, 108, 0, Math.PI * 2);
    c.stroke();
  });
}

function mono(ctx: CanvasRenderingContext2D, size: number) {
  ctx.font = `500 ${size}px "Geist Mono", ui-monospace, SFMono-Regular, Menlo, monospace`;
}

function ticks(ctx: CanvasRenderingContext2D, w: number, h: number, len: number, color: string) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  const L = len;
  ctx.beginPath();
  ctx.moveTo(6, 6 + L); ctx.lineTo(6, 6); ctx.lineTo(6 + L, 6);
  ctx.moveTo(w - 6 - L, 6); ctx.lineTo(w - 6, 6); ctx.lineTo(w - 6, 6 + L);
  ctx.moveTo(6, h - 6 - L); ctx.lineTo(6, h - 6); ctx.lineTo(6 + L, h - 6);
  ctx.moveTo(w - 6 - L, h - 6); ctx.lineTo(w - 6, h - 6); ctx.lineTo(w - 6, h - 6 - L);
  ctx.stroke();
}

/** Holographic evidence data card. */
export function cardTexture(nodeLabel: string, lines: string[]): Texture {
  const key = `card:${nodeLabel}`;
  return make(key, 512, 320, (c) => {
    c.clearRect(0, 0, 512, 320);
    // glass body
    const bg = c.createLinearGradient(0, 0, 512, 320);
    bg.addColorStop(0, "rgba(13, 22, 38, 0.88)");
    bg.addColorStop(1, "rgba(7, 12, 22, 0.82)");
    c.fillStyle = bg;
    c.beginPath();
    c.roundRect(4, 4, 504, 312, 10);
    c.fill();
    // holo stripes
    c.save();
    c.beginPath(); c.roundRect(4, 4, 504, 312, 10); c.clip();
    c.strokeStyle = "rgba(126, 190, 255, 0.05)";
    c.lineWidth = 22;
    for (let x = -320; x < 560; x += 90) {
      c.beginPath(); c.moveTo(x, 340); c.lineTo(x + 240, -20); c.stroke();
    }
    c.restore();
    // frame
    c.strokeStyle = "rgba(126, 180, 255, 0.32)";
    c.lineWidth = 2;
    c.beginPath(); c.roundRect(4, 4, 504, 312, 10); c.stroke();
    ticks(c, 512, 320, 22, "rgba(160, 214, 255, 0.85)");
    // header
    c.fillStyle = "rgba(127, 212, 255, 0.9)";
    c.beginPath(); c.arc(36, 44, 6, 0, Math.PI * 2); c.fill();
    mono(c, 27);
    c.fillStyle = "rgba(214, 233, 255, 0.96)";
    c.textBaseline = "middle";
    c.fillText(nodeLabel, 56, 45, 400);
    // divider
    c.strokeStyle = "rgba(126, 180, 255, 0.22)";
    c.lineWidth = 1.5;
    c.beginPath(); c.moveTo(30, 78); c.lineTo(482, 78); c.stroke();
    // data lines
    mono(c, 24);
    c.fillStyle = "rgba(148, 178, 220, 0.92)";
    lines.forEach((ln, i) => c.fillText(ln, 34, 122 + i * 52, 448));
    // footer strip
    mono(c, 18);
    c.fillStyle = "rgba(108, 138, 180, 0.75)";
    c.fillText("EVIDENCE FRAGMENT", 34, 282);
    c.fillStyle = "rgba(108, 138, 180, 0.5)";
    c.fillText("SHA · 8f2c…41aa", 320, 282);
  });
}

/** Small world-space label used for evidence node names. */
export function labelTexture(text: string): Texture {
  const key = `label:${text}`;
  return make(key, 512, 96, (c) => {
    c.clearRect(0, 0, 512, 96);
    mono(c, 40);
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.shadowColor = "rgba(120, 200, 255, 0.55)";
    c.shadowBlur = 12;
    c.fillStyle = "rgba(226, 240, 255, 0.95)";
    c.fillText(text, 256, 50);
  });
}

/** Contextual system message card (mono line inside bracket ticks). */
export function messageTexture(text: string, color: string): Texture {
  const key = `msg:${text}:${color}`;
  return make(key, 768, 120, (c) => {
    c.clearRect(0, 0, 768, 120);
    mono(c, 38);
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.shadowColor = color;
    c.shadowBlur = 18;
    c.fillStyle = color;
    c.fillText(text, 384, 62);
    // bracket ticks
    c.shadowBlur = 0;
    c.strokeStyle = color;
    c.globalAlpha = 0.85;
    c.lineWidth = 3;
    const w = Math.min(720, c.measureText(text).width + 60);
    const x0 = 384 - w / 2, x1 = 384 + w / 2, L = 18;
    c.beginPath();
    c.moveTo(x0, 22 + L); c.lineTo(x0, 22); c.lineTo(x0 + L, 22);
    c.moveTo(x1 - L, 22); c.lineTo(x1, 22); c.lineTo(x1, 22 + L);
    c.moveTo(x0, 98 - L); c.lineTo(x0, 98); c.lineTo(x0 + L, 98);
    c.moveTo(x1 - L, 98); c.lineTo(x1, 98); c.lineTo(x1, 98 - L);
    c.stroke();
  });
}
