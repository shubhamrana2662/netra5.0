import { useEffect, useRef } from "react";
import type { Core } from "cytoscape";
import { prefersReducedMotion } from "../../../../lib/motion";

interface Props {
  cy: Core | null;
  mode: "EXPLORE" | "ENTITY_FOCUS" | "PATH_FOCUS" | "PATTERN_FOCUS";
  activePathNodes: string[];
  bridgeNodeIds: string[];
  hiddenEdgePairs?: Array<{ source: string; target: string; confidence?: number }>;
  pan: { x: number; y: number };
  zoom: number;
}

export function InvestigationEffectsOverlay({
  cy,
  mode,
  activePathNodes,
  bridgeNodeIds,
  hiddenEdgePairs = [],
  pan,
  zoom,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = prefersReducedMotion();

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

    const render = (now: number) => {
      ctx.clearRect(0, 0, width, height);

      if (!cy || cy.destroyed()) return;

      const time = now * 0.001;

      // ── 1. BRIDGE ENTITY EXPANDING BEACON HALO (Rose ◉) ──
      if (bridgeNodeIds.length > 0) {
        ctx.save();
        for (const id of bridgeNodeIds) {
          const cyNode = cy.getElementById(id);
          if (!cyNode || cyNode.length === 0 || !cyNode.visible()) continue;

          const renderedPos = cyNode.renderedPosition();
          const renderedSize = cyNode.renderedWidth() * 0.5;

          const pulsePhase = (time * 1.4) % 1;
          const haloRadius = renderedSize + 4 + pulsePhase * 22;
          const haloAlpha = (1 - pulsePhase) * 0.65;

          ctx.beginPath();
          ctx.arc(renderedPos.x, renderedPos.y, haloRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(251, 113, 133, ${haloAlpha.toFixed(3)})`;
          ctx.lineWidth = 1.6;
          ctx.stroke();

          // Inner halo
          ctx.beginPath();
          ctx.arc(renderedPos.x, renderedPos.y, renderedSize + 3, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(251, 113, 133, 0.4)";
          ctx.lineWidth = 1;
          ctx.stroke();

          // Monospace Bridge Badge if in Pattern or Explore mode
          if (mode === "PATTERN_FOCUS" || mode === "EXPLORE") {
            ctx.font = '9px "Geist Mono", monospace';
            ctx.textAlign = "center";
            ctx.fillStyle = "rgba(10, 11, 14, 0.88)";
            ctx.fillRect(renderedPos.x - 50, renderedPos.y - renderedSize - 22, 100, 16);
            ctx.strokeStyle = "rgba(251, 113, 133, 0.6)";
            ctx.lineWidth = 1;
            ctx.strokeRect(renderedPos.x - 50, renderedPos.y - renderedSize - 22, 100, 16);
            ctx.fillStyle = "#FB7185";
            ctx.fillText("BRIDGE BROKER", renderedPos.x, renderedPos.y - renderedSize - 11);
          }
        }
        ctx.restore();
      }

      // ── 2. TRAVELING INVESTIGATION PROBE COMET & SHOCKWAVES ──
      if (activePathNodes.length >= 2 && !reduced) {
        ctx.save();
        const pathCoords: Array<{ x: number; y: number; id: string }> = [];
        for (const id of activePathNodes) {
          const cyNode = cy.getElementById(id);
          if (cyNode && cyNode.length > 0 && cyNode.visible()) {
            pathCoords.push({ ...cyNode.renderedPosition(), id });
          }
        }

        if (pathCoords.length >= 2) {
          const totalSegments = pathCoords.length - 1;
          const speed = 0.55; // segments per second
          const progress = (time * speed) % totalSegments;
          const activeSegment = Math.min(Math.floor(progress), totalSegments - 1);
          const segT = progress - activeSegment;

          const pA = pathCoords[activeSegment];
          const pB = pathCoords[activeSegment + 1];

          // Luminous probe head coordinate
          const headX = pA.x + (pB.x - pA.x) * segT;
          const headY = pA.y + (pB.y - pA.y) * segT;

          // Trail line
          ctx.beginPath();
          ctx.moveTo(pA.x, pA.y);
          ctx.lineTo(headX, headY);
          ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
          ctx.lineWidth = 2.4;
          ctx.stroke();

          // Glowing Comet Head
          ctx.beginPath();
          ctx.arc(headX, headY, 6.0, 0, Math.PI * 2);
          ctx.fillStyle = "#38BDF8";
          ctx.shadowColor = "#38BDF8";
          ctx.shadowBlur = 14;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(headX, headY, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = "#FFFFFF";
          ctx.shadowBlur = 0;
          ctx.fill();

          // Shockwave ripple at receiving node
          const ripplePhase = (segT * 3) % 1;
          const shockRadius = 14 + ripplePhase * 28;
          const shockAlpha = (1 - ripplePhase) * 0.75;
          ctx.beginPath();
          ctx.arc(pB.x, pB.y, shockRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(56, 189, 248, ${shockAlpha.toFixed(3)})`;
          ctx.lineWidth = 1.4;
          ctx.stroke();

          // Active Step Telemetry Tag
          ctx.font = '10px "Geist Mono", monospace';
          ctx.textAlign = "center";
          const stepLabel = `HOP ${activeSegment + 1} OF ${totalSegments} · CORRELATING`;
          const textW = ctx.measureText(stepLabel).width + 16;
          ctx.fillStyle = "rgba(10, 11, 14, 0.90)";
          ctx.fillRect(headX - textW * 0.5, headY - 26, textW, 18);
          ctx.strokeStyle = "rgba(56, 189, 248, 0.5)";
          ctx.lineWidth = 1;
          ctx.strokeRect(headX - textW * 0.5, headY - 26, textW, 18);
          ctx.fillStyle = "#38BDF8";
          ctx.fillText(stepLabel, headX, headY - 14);
        }
        ctx.restore();
      }

      // ── 3. INFERRED LINK FLOATING ANALYTICAL BADGES ──
      if (mode === "PATTERN_FOCUS" || mode === "EXPLORE") {
        ctx.save();
        for (const pair of hiddenEdgePairs) {
          const nA = cy.getElementById(pair.source);
          const nB = cy.getElementById(pair.target);
          if (!nA || !nB || nA.length === 0 || nB.length === 0 || !nA.visible() || !nB.visible()) continue;

          const pA = nA.renderedPosition();
          const pB = nB.renderedPosition();
          const midX = (pA.x + pB.x) * 0.5;
          const midY = (pA.y + pB.y) * 0.5 - 12;

          const confText = `INFERRED · ${(pair.confidence || 88.4).toFixed(1)}% CONF`;
          ctx.font = '9px "Geist Mono", monospace';
          ctx.textAlign = "center";
          const tw = ctx.measureText(confText).width + 14;

          ctx.fillStyle = "rgba(18, 14, 6, 0.92)";
          ctx.fillRect(midX - tw * 0.5, midY - 9, tw, 18);
          ctx.strokeStyle = "rgba(245, 158, 11, 0.65)";
          ctx.lineWidth = 1;
          ctx.strokeRect(midX - tw * 0.5, midY - 9, tw, 18);
          ctx.fillStyle = "#F59E0B";
          ctx.fillText(confText, midX, midY + 3);
        }
        ctx.restore();
      }

      // ── 4. INTERFACE FRAMING ACCENTS (Tactical HUD Corner Brackets) ──
      ctx.save();
      const margin = 18;
      const bLen = 22;
      ctx.strokeStyle = "rgba(241, 241, 238, 0.30)";
      ctx.lineWidth = 1;

      // Top-left
      ctx.beginPath(); ctx.moveTo(margin, margin + bLen); ctx.lineTo(margin, margin); ctx.lineTo(margin + bLen, margin); ctx.stroke();
      // Top-right
      ctx.beginPath(); ctx.moveTo(width - margin - bLen, margin); ctx.lineTo(width - margin, margin); ctx.lineTo(width - margin, margin + bLen); ctx.stroke();
      // Bottom-left
      ctx.beginPath(); ctx.moveTo(margin, height - margin - bLen); ctx.lineTo(margin, height - margin); ctx.lineTo(margin + bLen, height - margin); ctx.stroke();
      // Bottom-right
      ctx.beginPath(); ctx.moveTo(width - margin - bLen, height - margin); ctx.lineTo(width - margin, height - margin); ctx.lineTo(width - margin, height - margin - bLen); ctx.stroke();

      // Monospace live telemetry
      ctx.font = '9px "Geist Mono", monospace';
      ctx.fillStyle = "rgba(241, 241, 238, 0.35)";
      ctx.textAlign = "left";
      ctx.fillText(`SYS.GRAPH.TOPOLOGY · MODE: ${mode}`, margin + 8, margin + 12);
      ctx.textAlign = "right";
      ctx.fillText(`2.5D DEPTH ACTIVE · ZOOM: ${(zoom * 100).toFixed(0)}%`, width - margin - 8, margin + 12);

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
  }, [cy, mode, activePathNodes, bridgeNodeIds, hiddenEdgePairs, pan, zoom]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 4,
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
