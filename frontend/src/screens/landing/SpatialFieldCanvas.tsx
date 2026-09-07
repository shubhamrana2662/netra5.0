import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../../lib/motion";
import { createDustPool, project3D, clamp, type ProjectedPoint } from "./spatialEngine";
import { getSceneState } from "./getSceneState";
import type { SceneState, EntityVisualState } from "./storyTypes";

interface Props {
  storyProgress: number; // Normalized [0, 1] single source of truth
  blurAmount?: number;
}

export function SpatialFieldCanvas({ storyProgress, blurAmount = 0 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Damped scroll & mouse state for fluid motion
  const targetProgressRef = useRef(storyProgress);
  const currentProgressRef = useRef(storyProgress);
  const mouseRef = useRef({ targetX: 0, targetY: 0, currentX: 0, currentY: 0 });

  useEffect(() => {
    targetProgressRef.current = storyProgress;
  }, [storyProgress]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      mouseRef.current.targetX = clamp(nx, -1, 1);
      mouseRef.current.targetY = clamp(ny, -1, 1);
    };
    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;

    const reduced = prefersReducedMotion();
    const dustPool = createDustPool(reduced ? 25 : 65);

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

    const render = (time: number) => {
      // 1. Smooth damping of progress and mouse parallax
      const pTarget = targetProgressRef.current;
      currentProgressRef.current += (pTarget - currentProgressRef.current) * (reduced ? 0.35 : 0.08);
      const p = currentProgressRef.current;

      const m = mouseRef.current;
      m.currentX += (m.targetX - m.currentX) * 0.05;
      m.currentY += (m.targetY - m.currentY) * 0.05;

      // 2. DETERMINISTIC SCENE EVALUATION FROM PROGRESS
      const scene: SceneState = getSceneState(p);

      // 3. Clear canvas with deep obsidian void
      ctx.fillStyle = "#0A0B0E";
      ctx.fillRect(0, 0, width, height);

      // Incorporate mouse parallax into camera state
      const cam = {
        ...scene.camera,
        x: scene.camera.x + m.currentX * 25,
        y: scene.camera.y + m.currentY * 18,
        yaw: scene.camera.yaw + m.currentX * 0.02,
        pitch: scene.camera.pitch + m.currentY * 0.015,
      };

      // 4. Render ambient 3D dust particles
      ctx.fillStyle = "rgba(241, 241, 238, 0.35)";
      for (let i = 0; i < dustPool.length; i++) {
        const d = dustPool[i];
        const dx = d.x + Math.sin(time * 0.0003 * d.speed + d.phase) * 12;
        const dy = d.y + Math.cos(time * 0.00025 * d.speed + d.phase * 1.3) * 10;
        const dz = d.z;

        const proj = project3D({ x: dx, y: dy, z: dz }, cam, width, height);
        if (!proj.inView) continue;

        const alpha = d.alpha * proj.depthAlpha * scene.backgroundDensity;
        if (alpha <= 0.015) continue;

        ctx.beginPath();
        ctx.arc(proj.x2d, proj.y2d, d.size * proj.scale, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(241, 241, 238, ${alpha.toFixed(3)})`;
        ctx.fill();
      }

      // 5. Project all entities to screen space
      const projectedEntities = new Map<string, { proj: ProjectedPoint; ent: EntityVisualState }>();

      for (let i = 0; i < scene.entities.length; i++) {
        const ent = scene.entities[i];
        if (ent.opacity <= 0.01) continue;

        const proj = project3D({ x: ent.x, y: ent.y, z: ent.z }, cam, width, height);
        projectedEntities.set(ent.id, { proj, ent });
      }

      // 6. Chapter 01 Isolated Radar Pings
      if (p <= 0.16) {
        for (const [, item] of projectedEntities.entries()) {
          if (!item.proj.inView || !item.ent.pingRadius || !item.ent.pingAlpha) continue;
          ctx.beginPath();
          ctx.arc(item.proj.x2d, item.proj.y2d, item.ent.pingRadius * item.proj.scale, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(241, 241, 238, ${(item.ent.pingAlpha * item.proj.depthAlpha).toFixed(3)})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // ── 7. RENDER FILAMENT CONNECTIONS & IGNITIONS ──
      for (let i = 0; i < scene.edges.length; i++) {
        const edge = scene.edges[i];
        const pA = projectedEntities.get(edge.sourceId);
        const pB = projectedEntities.get(edge.targetId);
        if (!pA || !pB || !pA.proj.inView || !pB.proj.inView) continue;

        const endX = pA.proj.x2d + (pB.proj.x2d - pA.proj.x2d) * edge.drawProgress;
        const endY = pA.proj.y2d + (pB.proj.y2d - pA.proj.y2d) * edge.drawProgress;
        const avgDepthAlpha = (pA.proj.depthAlpha + pB.proj.depthAlpha) * 0.5;

        // Flash ignition ring when edge first sparks
        if (edge.flashAlpha && edge.flashRadius && !reduced) {
          ctx.beginPath();
          ctx.arc(endX, endY, edge.flashRadius * pB.proj.scale, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(255, 255, 255, ${(edge.flashAlpha * avgDepthAlpha).toFixed(3)})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        ctx.save();

        if (edge.isDashed) {
          // Chapter 05 Inferred Hidden Link
          ctx.setLineDash([8, 6]);
          ctx.beginPath();
          ctx.moveTo(pA.proj.x2d, pA.proj.y2d);
          ctx.lineTo(endX, endY);
          ctx.strokeStyle = `${edge.strokeStyle}${(edge.opacity * avgDepthAlpha).toFixed(3)})`;
          ctx.lineWidth = edge.lineWidth;
          ctx.stroke();

          // Amber traveling pulse
          if (edge.pulsePosition !== undefined && !reduced) {
            const px = pA.proj.x2d + (pB.proj.x2d - pA.proj.x2d) * edge.pulsePosition;
            const py = pA.proj.y2d + (pB.proj.y2d - pA.proj.y2d) * edge.pulsePosition;
            ctx.beginPath();
            ctx.arc(px, py, 3.5, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(251, 191, 36, ${(edge.opacity * 1.2).toFixed(3)})`;
            ctx.fill();
          }

          // Analytical midpoint callout
          if (edge.drawProgress >= 0.9 && p >= 0.83 && p <= 0.88) {
            const midX = (pA.proj.x2d + pB.proj.x2d) * 0.5;
            const midY = (pA.proj.y2d + pB.proj.y2d) * 0.5 - 16;
            ctx.font = `9px "Geist Mono", monospace`;
            ctx.textAlign = "center";
            ctx.fillStyle = "rgba(10, 11, 14, 0.88)";
            ctx.fillRect(midX - 95, midY - 10, 190, 20);
            ctx.strokeStyle = "rgba(245, 158, 11, 0.6)";
            ctx.lineWidth = 1;
            ctx.strokeRect(midX - 95, midY - 10, 190, 20);
            ctx.fillStyle = "#F59E0B";
            ctx.fillText("INFERRED LINK · 88.4% CONFIDENCE", midX, midY + 3);
          }
        } else {
          // Normal or suspect filament
          ctx.beginPath();
          ctx.moveTo(pA.proj.x2d, pA.proj.y2d);
          ctx.lineTo(endX, endY);
          ctx.strokeStyle = `${edge.strokeStyle}${(edge.opacity * avgDepthAlpha).toFixed(3)})`;
          ctx.lineWidth = edge.lineWidth;
          ctx.stroke();

          // Traveling pulse along suspect chain
          if (edge.isSuspectChain && edge.pulsePosition !== undefined && !reduced && p >= 0.20) {
            const px = pA.proj.x2d + (pB.proj.x2d - pA.proj.x2d) * edge.pulsePosition;
            const py = pA.proj.y2d + (pB.proj.y2d - pA.proj.y2d) * edge.pulsePosition;
            ctx.beginPath();
            ctx.arc(px, py, edge.isSuspectChain ? 2.4 : 1.5, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(241, 241, 238, ${(edge.opacity * avgDepthAlpha).toFixed(3)})`;
            ctx.fill();
          }
        }

        ctx.restore();
      }

      // ── 8. CHAPTER 04: SEQUENTIAL INVESTIGATION PROBE BEAM ──
      if (scene.investigationPulse.active && !reduced) {
        const pulse = scene.investigationPulse;
        const headProj = project3D(
          { x: pulse.headX, y: pulse.headY, z: pulse.headZ },
          cam,
          width,
          height
        );

        if (headProj.inView) {
          ctx.save();
          // Luminous cyan probe comet head
          ctx.beginPath();
          ctx.arc(headProj.x2d, headProj.y2d, 6.0, 0, Math.PI * 2);
          ctx.fillStyle = "#38BDF8";
          ctx.shadowColor = "#38BDF8";
          ctx.shadowBlur = 14;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(headProj.x2d, headProj.y2d, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = "#FFFFFF";
          ctx.fill();

          // Shockwave ripple at receiving node
          const targetNode = projectedEntities.get(pulse.activeNodeId);
          if (targetNode && pulse.shockwaveRadius && pulse.shockwaveAlpha) {
            ctx.beginPath();
            ctx.arc(targetNode.proj.x2d, targetNode.proj.y2d, pulse.shockwaveRadius * targetNode.proj.scale, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(56, 189, 248, ${pulse.shockwaveAlpha.toFixed(3)})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Step Indicator Badge
            ctx.font = `10px "Geist Mono", monospace`;
            ctx.textAlign = "center";
            ctx.fillStyle = "rgba(10, 11, 14, 0.88)";
            ctx.fillRect(targetNode.proj.x2d - 90, targetNode.proj.y2d - 28, 180, 20);
            ctx.strokeStyle = "rgba(56, 189, 248, 0.6)";
            ctx.lineWidth = 1;
            ctx.strokeRect(targetNode.proj.x2d - 90, targetNode.proj.y2d - 28, 180, 20);
            ctx.fillStyle = "#38BDF8";
            ctx.fillText(pulse.stepLabel, targetNode.proj.x2d, targetNode.proj.y2d - 14);
          }

          ctx.restore();
        }
      }

      // ── 9. RENDER ENTITY NODES (Sorted by depth — Painter's Algorithm) ──
      const sortedEntities = Array.from(projectedEntities.values()).sort(
        (a, b) => b.proj.depth - a.proj.depth
      );

      for (let i = 0; i < sortedEntities.length; i++) {
        const { proj, ent } = sortedEntities[i];
        if (!proj.inView || proj.depthAlpha <= 0.01) continue;

        const isBridge = !!ent.isBridge;
        const isSuspect = !!ent.isSuspectChain;
        const baseRadius = (ent.isBridge ? 4.8 : isSuspect ? 4.2 : 3.2) * proj.scale * ent.scale;
        const radius = clamp(baseRadius, 2.0, 20);

        ctx.save();

        // Bridge Node Rose Beacon Halo (Chapter 05)
        if (isBridge && scene.bridgeEmphasis > 0) {
          const bridgePulse = 0.5 + 0.5 * Math.sin(time * 0.005);
          const auraRadius = radius + 8 + bridgePulse * 8 * scene.bridgeEmphasis;

          ctx.beginPath();
          ctx.arc(proj.x2d, proj.y2d, auraRadius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(251, 113, 133, ${(0.22 + bridgePulse * 0.18).toFixed(3)})`;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(proj.x2d, proj.y2d, auraRadius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(251, 113, 133, ${(0.65 * scene.bridgeEmphasis).toFixed(3)})`;
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Distinct Geometric Shapes by kind
        ctx.beginPath();
        if (ent.kind === 'UPI') {
          // Diamond
          ctx.moveTo(proj.x2d, proj.y2d - radius * 1.25);
          ctx.lineTo(proj.x2d + radius * 1.25, proj.y2d);
          ctx.lineTo(proj.x2d, proj.y2d + radius * 1.25);
          ctx.lineTo(proj.x2d - radius * 1.25, proj.y2d);
          ctx.closePath();
        } else if (ent.kind === 'DEVICE') {
          // Square
          ctx.rect(proj.x2d - radius, proj.y2d - radius, radius * 2, radius * 2);
        } else if (ent.kind === 'ACCOUNT' || ent.kind === 'BANK') {
          // Rounded Rect
          ctx.rect(proj.x2d - radius * 1.2, proj.y2d - radius * 0.8, radius * 2.4, radius * 1.6);
        } else if (ent.kind === 'IP') {
          // Triangle
          ctx.moveTo(proj.x2d, proj.y2d - radius * 1.2);
          ctx.lineTo(proj.x2d + radius * 1.1, proj.y2d + radius * 0.9);
          ctx.lineTo(proj.x2d - radius * 1.1, proj.y2d + radius * 0.9);
          ctx.closePath();
        } else {
          // Circle
          ctx.arc(proj.x2d, proj.y2d, radius, 0, Math.PI * 2);
        }

        // Fill Color
        if (isBridge && scene.bridgeEmphasis > 0) {
          ctx.fillStyle = `rgba(251, 113, 133, ${ent.opacity.toFixed(3)})`;
        } else if (isSuspect && p >= 0.54 && p <= 0.72) {
          ctx.fillStyle = `rgba(255, 255, 255, ${ent.opacity.toFixed(3)})`;
        } else if (isSuspect && p > 0.72 && p <= 0.88) {
          ctx.fillStyle = `rgba(255, 110, 110, ${ent.opacity.toFixed(3)})`;
        } else if (p <= 0.35) {
          ctx.fillStyle = `rgba(241, 241, 238, ${ent.opacity.toFixed(3)})`;
        } else {
          ctx.fillStyle = `rgba(180, 184, 195, ${(ent.opacity * 0.85).toFixed(3)})`;
        }
        ctx.fill();

        ctx.strokeStyle = "rgba(10, 11, 14, 0.9)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Node Labels & Metadata Pills
        if (ent.opacity > 0.15 && proj.scale > 0.38) {
          const textAlpha = ent.opacity * proj.depthAlpha;
          ctx.font = `${Math.round(clamp(10 * proj.scale, 9, 12))}px "Geist Mono", monospace`;
          ctx.textAlign = "left";

          const tx = proj.x2d + radius + 8;
          const ty = proj.y2d + 3;

          const labelText = ent.label;
          const textMetrics = ctx.measureText(labelText);
          const pillW = textMetrics.width + 10;
          const pillH = 17;

          ctx.fillStyle = `rgba(10, 11, 14, ${(textAlpha * 0.88).toFixed(3)})`;
          ctx.fillRect(tx - 4, ty - 12, pillW, pillH);

          if (isBridge && scene.bridgeEmphasis > 0) {
            ctx.fillStyle = `rgba(251, 113, 133, ${textAlpha.toFixed(3)})`;
          } else if (isSuspect && p >= 0.54) {
            ctx.fillStyle = `rgba(255, 230, 230, ${textAlpha.toFixed(3)})`;
          } else {
            ctx.fillStyle = `rgba(241, 241, 238, ${textAlpha.toFixed(3)})`;
          }
          ctx.fillText(labelText, tx, ty);

          // Subtext Tag
          if (p <= 0.16) {
            ctx.font = `8px "Geist Mono", monospace`;
            ctx.fillStyle = `rgba(160, 166, 178, ${(textAlpha * 0.65).toFixed(3)})`;
            ctx.fillText("ISOLATED SIGNAL", tx, ty + 12);
          } else if (isBridge && scene.bridgeEmphasis > 0) {
            ctx.font = `9px "Geist Mono", monospace`;
            ctx.fillStyle = "#FB7185";
            ctx.fillText("BRIDGE BROKER · 67%", tx, ty + 12);
          } else if (ent.subtext && (p >= 0.72 || isSuspect)) {
            ctx.font = `8px "Geist Mono", monospace`;
            ctx.fillStyle = `rgba(160, 166, 178, ${(textAlpha * 0.60).toFixed(3)})`;
            ctx.fillText(ent.subtext, tx, ty + 12);
          }
        }

        ctx.restore();
      }

      // ── 10. CHAPTER 06: INTERFACE FRAMING ACCENTS ──
      if (scene.interfaceFramingAlpha > 0) {
        const frameAlpha = scene.interfaceFramingAlpha;
        const margin = 36;
        const bLen = 28;
        ctx.save();
        ctx.strokeStyle = `rgba(241, 241, 238, ${(frameAlpha * 0.40).toFixed(3)})`;
        ctx.lineWidth = 1;

        // Top-left
        ctx.beginPath(); ctx.moveTo(margin, margin + bLen); ctx.lineTo(margin, margin); ctx.lineTo(margin + bLen, margin); ctx.stroke();
        // Top-right
        ctx.beginPath(); ctx.moveTo(width - margin - bLen, margin); ctx.lineTo(width - margin, margin); ctx.lineTo(width - margin, margin + bLen); ctx.stroke();
        // Bottom-left
        ctx.beginPath(); ctx.moveTo(margin, height - margin - bLen); ctx.lineTo(margin, height - margin); ctx.lineTo(margin + bLen, height - margin); ctx.stroke();
        // Bottom-right
        ctx.beginPath(); ctx.moveTo(width - margin - bLen, height - margin); ctx.lineTo(width - margin, height - margin); ctx.lineTo(width - margin, height - margin - bLen); ctx.stroke();

        ctx.font = `9px "Geist Mono", monospace`;
        ctx.fillStyle = `rgba(241, 241, 238, ${(frameAlpha * 0.35).toFixed(3)})`;
        ctx.fillText("SYS.INTELLIGENCE.TOPOLOGY", margin + 8, margin + 14);
        ctx.textAlign = "right";
        ctx.fillText("STATUS: RESOLVED", width - margin - 8, margin + 14);

        ctx.restore();
      }
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
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
        background: "#0A0B0E",
        overflow: "hidden",
        filter: blurAmount > 0 ? `blur(${blurAmount}px)` : "none",
        transition: "filter 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
        willChange: "filter"
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          display: "block",
          width: "100%",
          height: "100%"
        }}
      />
    </div>
  );
}
