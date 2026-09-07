import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { ModelNode, ModelEdge, IntelAnalysis, InferredHiddenLink } from '../graphEngine';
import { CameraState, SpatialNode, SpatialFilament, DustParticle3D, Point3D } from './spatial3DTypes';
import { buildSpatialScene } from './spatialSceneBuilder';
import { updateFilamentOrchestration } from './connectionOrchestrator';
import { project3D, createDustPool, clamp, computeGraphBounds, GraphBoundsInfo } from './spatialCameraEngine';
import { useGraphInteraction } from '../graphCore/GraphInteractionStore';
import { GraphAlgorithmService } from '../graphCore/GraphAlgorithmService';
import styles from './immersive.module.css';

interface ImmersiveSpatialGraphProps {
  nodes: ModelNode[];
  edges: ModelEdge[];
  analysis: IntelAnalysis | null;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  inferredLinks?: InferredHiddenLink[];
  activeInvestigationPath?: string[];
  onLocateOperational?: () => void;
}

const ENTITY_COLORS: Record<string, { stroke: string; fill: string; badge: string }> = {
  PERSON: { stroke: '#38BDF8', fill: 'rgba(2, 132, 199, 0.45)', badge: 'P' },
  DEVICE: { stroke: '#A78BFA', fill: 'rgba(124, 58, 237, 0.45)', badge: 'D' },
  ACCOUNT: { stroke: '#34D399', fill: 'rgba(5, 150, 105, 0.45)', badge: 'A' },
  BANK: { stroke: '#10B981', fill: 'rgba(4, 120, 87, 0.45)', badge: 'B' },
  PHONE: { stroke: '#F472B6', fill: 'rgba(219, 39, 119, 0.45)', badge: 'M' },
  UPI: { stroke: '#F59E0B', fill: 'rgba(217, 119, 6, 0.45)', badge: 'U' },
  IP: { stroke: '#67E8F9', fill: 'rgba(8, 145, 178, 0.45)', badge: 'I' },
  ORG: { stroke: '#818CF8', fill: 'rgba(79, 70, 229, 0.45)', badge: 'O' },
  ORGANIZATION: { stroke: '#818CF8', fill: 'rgba(79, 70, 229, 0.45)', badge: 'O' },
};

const DEFAULT_COLOR = { stroke: '#EDEDE9', fill: 'rgba(100, 116, 139, 0.45)', badge: '•' };

export const ImmersiveSpatialGraph: React.FC<ImmersiveSpatialGraphProps> = ({
  nodes,
  edges,
  analysis,
  selectedNodeId: propSelectedNodeId,
  onSelectNode: propOnSelectNode,
  inferredLinks = [],
  activeInvestigationPath: propActivePath = [],
  onLocateOperational
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Shared Graph Core Controller
  const {
    state: storeState,
    selectNode: storeSelectNode,
    hoverNode: storeHoverNode,
    selectEdge: storeSelectEdge,
    hoverEdge: storeHoverEdge,
    expandNeighborhood,
    setPath: storeSetPath,
    focusCluster: storeFocusCluster,
    clearSelection: storeClearSelection
  } = useGraphInteraction();

  // Mode and controls
  const [navMode, setNavMode] = useState<'CINEMATIC' | 'FREE'>('CINEMATIC');
  const [showAiLinks, setShowAiLinks] = useState(storeState.activeFilters.showHidden);
  const [hoveredNode, setHoveredNode] = useState<SpatialNode | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<SpatialFilament | null>(null);
  const [activeClusterIndex, setActiveClusterIndex] = useState(0);
  const [pathStep, setPathStep] = useState(0);

  // Diagnostics & Debug Panel (Phases 2, 3, 9)
  const [showDebug, setShowDebug] = useState(false);
  const [debugNodes, setDebugNodes] = useState(true);
  const [debugEdges, setDebugEdges] = useState(true);
  const [debugLabels, setDebugLabels] = useState(true);
  const [debugAxes, setDebugAxes] = useState(false);
  const [debugCalibration, setDebugCalibration] = useState(false);

  // Synchronized selection from store or prop
  const activeSelectedNodeId = storeState.focusedNodeId || propSelectedNodeId;
  const activePath = storeState.activePath || propActivePath;

  // Time & Animation anchor
  const t0Ref = useRef(performance.now());

  // Mouse parallax
  const mouseRef = useRef({ targetX: 0, targetY: 0, currentX: 0, currentY: 0 });

  // Camera State (Initialized via auto-framing on first build)
  const cameraRef = useRef<CameraState>({ x: 0, y: 0, z: 580, yaw: 0, pitch: 0 });
  const targetCamRef = useRef<CameraState>({ x: 0, y: 0, z: 580, yaw: 0, pitch: 0 });
  const hasAutoFramedRef = useRef(false);

  // Free Explore Dragging
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0, camX: 0, camY: 0, yaw: 0, pitch: 0 });
  const hasDraggedRef = useRef(false);

  // Double click detection
  const lastClickTimeRef = useRef(0);
  const lastClickedNodeRef = useRef<string | null>(null);

  // Ambient dust
  const dustPoolRef = useRef<DustParticle3D[]>(createDustPool(55));

  // Stable Dataset Fingerprint: Prevents rebuilding scene when other UI states change
  const datasetFingerprint = useMemo(() => {
    return `${nodes.length}:${nodes.map(n => n.id).sort().join(',')}|${edges.length}`;
  }, [nodes, edges]);

  // Build Scene from Real Case Graph
  const { sceneNodes, sceneFilaments, clusterCentroids, graphBounds } = useMemo(() => {
    console.log('[3D GRAPH PIPELINE] Building scene with:', { nodeCount: nodes.length, edgeCount: edges.length });
    const scene = buildSpatialScene(nodes, edges, analysis);
    const bounds = computeGraphBounds(scene.nodes.values());

    console.log('[3D GRAPH PIPELINE] Scene built successfully:', {
      nodeCount: scene.nodes.size,
      filamentCount: scene.filaments.length,
      boundsCenter: bounds.center,
      optimalCamZ: bounds.optimalCamZ
    });

    return {
      sceneNodes: scene.nodes,
      sceneFilaments: scene.filaments,
      clusterCentroids: scene.clusterCentroids,
      graphBounds: bounds
    };
  }, [datasetFingerprint, analysis]);

  // Merge Inferred Links into filaments when enabled
  const allFilaments = useMemo(() => {
    if (!showAiLinks || !inferredLinks.length) return sceneFilaments;
    const aiFilaments: SpatialFilament[] = inferredLinks.map(l => ({
      id: l.id,
      sourceId: l.sourceId,
      targetId: l.targetId,
      type: 'inferred_link',
      conf: l.confidence,
      is_hidden: true,
      directed: 0,
      waveIndex: 4,
      state: 'stable',
      drawProgress: 1.0,
      opacity: 0.90,
      lineWidth: 2.0,
      isSuspectPath: false
    }));
    return [...sceneFilaments, ...aiFilaments];
  }, [sceneFilaments, showAiLinks, inferredLinks]);

  // Phase 6: Auto-Framing Function (Centers entire graph inside viewing volume)
  const fitCameraToGraph = useCallback(() => {
    const b = graphBounds;
    targetCamRef.current = {
      x: b.center.x,
      y: b.center.y,
      z: b.optimalCamZ,
      yaw: 0,
      pitch: 0
    };
  }, [graphBounds]);

  // Auto-frame on first mount or dataset change
  useEffect(() => {
    if (!hasAutoFramedRef.current || Math.abs(cameraRef.current.z - 580) < 5) {
      fitCameraToGraph();
      cameraRef.current = { ...targetCamRef.current };
      hasAutoFramedRef.current = true;
    }
  }, [fitCameraToGraph]);

  // Camera preset actions
  const resetToOverview = useCallback(() => {
    fitCameraToGraph();
    storeFocusCluster(null);
  }, [fitCameraToGraph, storeFocusCluster]);

  const focusCluster = useCallback((clusterIdx: number) => {
    const centroid = clusterCentroids.get(clusterIdx);
    if (!centroid) return;
    targetCamRef.current = {
      x: centroid.x * 0.85,
      y: centroid.y * 0.85 - 10,
      z: 360,
      yaw: -0.02 + (clusterIdx * 0.05),
      pitch: 0.03
    };
    storeFocusCluster(clusterIdx);
  }, [clusterCentroids, storeFocusCluster]);

  const focusEntity = useCallback((id: string) => {
    const node = sceneNodes.get(id);
    if (!node) return;
    targetCamRef.current = {
      x: node.basePos.x * 0.9,
      y: node.basePos.y * 0.9 - 10,
      z: 320,
      yaw: cameraRef.current.yaw * 0.5,
      pitch: 0.02
    };
  }, [sceneNodes]);

  // Focus when selected node changes
  useEffect(() => {
    if (activeSelectedNodeId) {
      focusEntity(activeSelectedNodeId);
    }
  }, [activeSelectedNodeId, focusEntity]);

  // Mouse Parallax listener
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      mouseRef.current.targetX = clamp(nx, -1, 1);
      mouseRef.current.targetY = clamp(ny, -1, 1);
    };
    window.addEventListener('mousemove', onMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMouseMove);
  }, []);

  // Keyboard Shortcuts (Esc, F, 1, 2, H, P, D)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'Escape') {
        storeClearSelection();
        propOnSelectNode(null);
        resetToOverview();
      } else if (e.key.toLowerCase() === 'f' && activeSelectedNodeId) {
        focusEntity(activeSelectedNodeId);
      } else if (e.key === '1' && activeSelectedNodeId) {
        expandNeighborhood(activeSelectedNodeId, 1);
      } else if (e.key === '2' && activeSelectedNodeId) {
        expandNeighborhood(activeSelectedNodeId, 2);
      } else if (e.key.toLowerCase() === 'h') {
        setShowAiLinks(prev => !prev);
      } else if (e.key.toLowerCase() === 'd') {
        setShowDebug(prev => !prev);
      } else if (e.key.toLowerCase() === 'p' && storeState.selectedNodeIds.size >= 2) {
        const selectedArr = Array.from(storeState.selectedNodeIds);
        const pathRes = GraphAlgorithmService.findConnectionPath(selectedArr[0], selectedArr[1], edges);
        if (pathRes) {
          storeSetPath(pathRes.nodes);
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeSelectedNodeId, storeState.selectedNodeIds, edges, expandNeighborhood, focusEntity, propOnSelectNode, resetToOverview, storeClearSelection, storeSetPath]);

  // Distance from point (px, py) to line segment (x1, y1) -> (x2, y2)
  const distToSegment = (px: number, py: number, x1: number, y1: number, x2: number, y2: number) => {
    const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
    if (l2 === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
  };

  // Accurate 3D Picking & Interaction Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    hasDraggedRef.current = false;
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      camX: targetCamRef.current.x,
      camY: targetCamRef.current.y,
      yaw: targetCamRef.current.yaw,
      pitch: targetCamRef.current.pitch
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (isDraggingRef.current) {
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      if (Math.hypot(dx, dy) > 4) {
        hasDraggedRef.current = true;
      }

      if (e.shiftKey || e.buttons === 2) {
        // Pan
        targetCamRef.current.x = dragStartRef.current.camX - dx * 0.7;
        targetCamRef.current.y = dragStartRef.current.camY - dy * 0.7;
      } else {
        // Orbit (bounded)
        targetCamRef.current.yaw = dragStartRef.current.yaw + dx * 0.005;
        targetCamRef.current.pitch = clamp(dragStartRef.current.pitch - dy * 0.004, -0.65, 0.65);
      }
      return;
    }

    // Accurate 3D Picking
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const cam = cameraRef.current;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    // 1. Test Nodes
    let hitNode: SpatialNode | null = null;
    for (const node of sceneNodes.values()) {
      const proj = project3D(node.currentPos, cam, width, height);
      if (!proj.inView) continue;
      const radius = clamp(11 * proj.scale, 8, 26);
      const dist = Math.hypot(mx - proj.x2d, my - proj.y2d);
      if (dist <= radius + 6) {
        hitNode = node;
        break;
      }
    }

    setHoveredNode(hitNode);
    storeHoverNode(hitNode ? hitNode.id : null);

    // 2. Test Edges if no node hovered
    if (!hitNode) {
      let hitEdge: SpatialFilament | null = null;
      for (const fil of allFilaments) {
        if (fil.state === 'hidden' || fil.drawProgress <= 0.05) continue;
        const nA = sceneNodes.get(fil.sourceId);
        const nB = sceneNodes.get(fil.targetId);
        if (!nA || !nB) continue;
        const pA = project3D(nA.currentPos, cam, width, height);
        const pB = project3D(nB.currentPos, cam, width, height);
        if (!pA.inView || !pB.inView) continue;

        const d = distToSegment(mx, my, pA.x2d, pA.y2d, pB.x2d, pB.y2d);
        if (d <= 8.0) {
          hitEdge = fil;
          break;
        }
      }
      setHoveredEdge(hitEdge);
      storeHoverEdge(hitEdge ? hitEdge.id : null);
    } else {
      setHoveredEdge(null);
      storeHoverEdge(null);
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomDelta = e.deltaY * 0.75;
    targetCamRef.current.z = clamp(targetCamRef.current.z + zoomDelta, 220, 1200);
  };

  const handleClick = (e: React.MouseEvent) => {
    if (hasDraggedRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const cam = cameraRef.current;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    const isMultiKey = e.shiftKey || e.metaKey || e.ctrlKey;
    const now = performance.now();

    // 1. Check Node Click
    for (const node of sceneNodes.values()) {
      const proj = project3D(node.currentPos, cam, width, height);
      if (!proj.inView) continue;
      const radius = clamp(11 * proj.scale, 8, 26);
      const dist = Math.hypot(mx - proj.x2d, my - proj.y2d);
      if (dist <= radius + 6) {
        // Double Click Detection: 1-hop / 2-hop expansion
        if (now - lastClickTimeRef.current < 320 && lastClickedNodeRef.current === node.id) {
          const nextHops = storeState.activeHopDepth === 1 ? 2 : 1;
          expandNeighborhood(node.id, nextHops);
          lastClickTimeRef.current = 0;
          return;
        }

        lastClickTimeRef.current = now;
        lastClickedNodeRef.current = node.id;

        // Multi-select or single select
        if (isMultiKey) {
          storeSelectNode(node.id, true);
          // If two nodes now selected, auto-discover path
          const currentSelected = Array.from(storeState.selectedNodeIds);
          if (currentSelected.length === 1 && currentSelected[0] !== node.id) {
            const pathRes = GraphAlgorithmService.findConnectionPath(currentSelected[0], node.id, edges);
            if (pathRes) storeSetPath(pathRes.nodes);
          }
        } else {
          storeSelectNode(node.id, false);
          propOnSelectNode(node.id);
        }
        return;
      }
    }

    // 2. Check Edge Click
    for (const fil of allFilaments) {
      if (fil.state === 'hidden' || fil.drawProgress <= 0.05) continue;
      const nA = sceneNodes.get(fil.sourceId);
      const nB = sceneNodes.get(fil.targetId);
      if (!nA || !nB) continue;
      const pA = project3D(nA.currentPos, cam, width, height);
      const pB = project3D(nB.currentPos, cam, width, height);
      if (!pA.inView || !pB.inView) continue;

      const d = distToSegment(mx, my, pA.x2d, pA.y2d, pB.x2d, pB.y2d);
      if (d <= 8.0) {
        storeSelectEdge(fil.id);
        return;
      }
    }

    // Background Tap: clear selection and frame overview
    storeClearSelection();
    propOnSelectNode(null);
    resetToOverview();
  };

  // Main 60fps Living Spatial Network Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

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

    const render = (now: number) => {
      const elapsed = now - t0Ref.current;

      // 1. Mouse Parallax Smoothing
      const m = mouseRef.current;
      m.currentX += (m.targetX - m.currentX) * 0.05;
      m.currentY += (m.targetY - m.currentY) * 0.05;

      // 2. Camera Interpolation & Autonomous Breathing Drift
      const camEase = navMode === 'CINEMATIC' ? 0.05 : 0.14;
      const tCam = targetCamRef.current;
      const cCam = cameraRef.current;

      cCam.x += (tCam.x - cCam.x) * camEase;
      cCam.y += (tCam.y - cCam.y) * camEase;
      cCam.z += (tCam.z - cCam.z) * camEase;
      cCam.yaw += (tCam.yaw - cCam.yaw) * camEase;
      cCam.pitch += (tCam.pitch - cCam.pitch) * camEase;

      // Subtle breathing drift in Cinematic mode (pauses during dragging)
      const isDragging = isDraggingRef.current;
      const driftX = (navMode === 'CINEMATIC' && !isDragging) ? Math.sin(now * 0.0003) * 12 : 0;
      const driftY = (navMode === 'CINEMATIC' && !isDragging) ? Math.cos(now * 0.00025) * 8 : 0;
      const driftYaw = (navMode === 'CINEMATIC' && !isDragging) ? Math.sin(now * 0.0002) * 0.012 : 0;

      const activeCam: CameraState = {
        x: cCam.x + driftX + m.currentX * 18,
        y: cCam.y + driftY + m.currentY * 12,
        z: cCam.z,
        yaw: cCam.yaw + driftYaw + m.currentX * 0.015,
        pitch: cCam.pitch + m.currentY * 0.01
      };

      // 3. Update Progressive Connection Waves & Orchestration
      updateFilamentOrchestration(allFilaments, sceneNodes, {
        time: elapsed,
        selectedNodeId: activeSelectedNodeId,
        showAiLinks,
        activePath,
        pathStep
      });

      // 4. Update Node Positions with Differential Harmonic Breathing
      for (const node of sceneNodes.values()) {
        const amp = node.depthLayer === 'foreground' ? 4.5 : node.depthLayer === 'midground' ? 2.8 : 1.2;
        const nx = Math.sin(now * 0.0006 + node.harmonicPhase) * amp;
        const ny = Math.cos(now * 0.0005 + node.harmonicPhase * 1.3) * (amp * 0.85);

        node.currentPos = {
          x: node.basePos.x + nx,
          y: node.basePos.y + ny,
          z: node.basePos.z
        };
      }

      // 5. Clear with deep obsidian void
      ctx.fillStyle = '#090B10';
      ctx.fillRect(0, 0, width, height);

      // Subtle coordinate grid crosshairs
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.025)';
      ctx.lineWidth = 1;
      const step = 64;
      for (let x = step; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = step; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Phase 3: Spatial Orientation Helpers (3D Axes & Origin Marker)
      if (debugAxes) {
        ctx.save();
        const pO = project3D({ x: 0, y: 0, z: 0 }, activeCam, width, height);
        const pX = project3D({ x: 140, y: 0, z: 0 }, activeCam, width, height);
        const pY = project3D({ x: 0, y: 140, z: 0 }, activeCam, width, height);
        const pZ = project3D({ x: 0, y: 0, z: 140 }, activeCam, width, height);

        if (pO.inView) {
          // Origin beacon
          ctx.beginPath();
          ctx.arc(pO.x2d, pO.y2d, 5, 0, Math.PI * 2);
          ctx.fillStyle = '#FFFFFF';
          ctx.fill();
          ctx.font = '700 10px monospace';
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText('ORIGIN (0,0,0)', pO.x2d + 8, pO.y2d - 6);

          // X Axis (Red)
          if (pX.inView) {
            ctx.beginPath();
            ctx.moveTo(pO.x2d, pO.y2d);
            ctx.lineTo(pX.x2d, pX.y2d);
            ctx.strokeStyle = '#EF4444';
            ctx.lineWidth = 2.2;
            ctx.stroke();
            ctx.fillStyle = '#EF4444';
            ctx.fillText('+X (140)', pX.x2d + 6, pX.y2d + 4);
          }

          // Y Axis (Green)
          if (pY.inView) {
            ctx.beginPath();
            ctx.moveTo(pO.x2d, pO.y2d);
            ctx.lineTo(pY.x2d, pY.y2d);
            ctx.strokeStyle = '#10B981';
            ctx.lineWidth = 2.2;
            ctx.stroke();
            ctx.fillStyle = '#10B981';
            ctx.fillText('+Y (140)', pY.x2d + 6, pY.y2d + 4);
          }

          // Z Axis (Blue)
          if (pZ.inView) {
            ctx.beginPath();
            ctx.moveTo(pO.x2d, pO.y2d);
            ctx.lineTo(pZ.x2d, pZ.y2d);
            ctx.strokeStyle = '#38BDF8';
            ctx.lineWidth = 2.2;
            ctx.stroke();
            ctx.fillStyle = '#38BDF8';
            ctx.fillText('+Z (140)', pZ.x2d + 6, pZ.y2d + 4);
          }
        }
        ctx.restore();
      }

      // Phase 2: Diagnostic Calibration Spheres
      if (debugCalibration) {
        ctx.save();
        const testPoints = [
          { name: 'RED (0,0,0)', pt: { x: 0, y: 0, z: 0 }, color: '#EF4444' },
          { name: 'GREEN (+60,0,0)', pt: { x: 60, y: 0, z: 0 }, color: '#10B981' },
          { name: 'BLUE (-60,0,0)', pt: { x: -60, y: 0, z: 0 }, color: '#3B82F6' },
        ];

        // Draw line between them
        const pR = project3D(testPoints[0].pt, activeCam, width, height);
        const pG = project3D(testPoints[1].pt, activeCam, width, height);
        const pB = project3D(testPoints[2].pt, activeCam, width, height);

        if (pR.inView && pG.inView && pB.inView) {
          ctx.beginPath();
          ctx.moveTo(pB.x2d, pB.y2d);
          ctx.lineTo(pR.x2d, pR.y2d);
          ctx.lineTo(pG.x2d, pG.y2d);
          ctx.strokeStyle = '#FDE047';
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        testPoints.forEach(t => {
          const pr = project3D(t.pt, activeCam, width, height);
          if (!pr.inView) return;
          ctx.beginPath();
          ctx.arc(pr.x2d, pr.y2d, 12 * pr.scale, 0, Math.PI * 2);
          ctx.fillStyle = t.color;
          ctx.fill();
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.font = '700 11px monospace';
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(t.name, pr.x2d, pr.y2d + 22 * pr.scale);
        });
        ctx.restore();
      }

      // 6. Render 3D Ambient Dust Particles
      const dust = dustPoolRef.current;
      for (let i = 0; i < dust.length; i++) {
        const d = dust[i];
        const dx = d.x + Math.sin(now * 0.00025 * d.speed + d.phase) * 10;
        const dy = d.y + Math.cos(now * 0.0002 * d.speed + d.phase * 1.4) * 8;
        const proj = project3D({ x: dx, y: dy, z: d.z }, activeCam, width, height);
        if (!proj.inView) continue;
        const alpha = d.alpha * proj.depthAlpha;
        if (alpha <= 0.02) continue;

        ctx.beginPath();
        ctx.arc(proj.x2d, proj.y2d, d.size * proj.scale, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(241, 241, 238, ${alpha.toFixed(3)})`;
        ctx.fill();
      }

      // 7. Project Entities to 2D
      const projectedNodes = new Map<string, { proj: ReturnType<typeof project3D>; node: SpatialNode }>();
      for (const node of sceneNodes.values()) {
        const proj = project3D(node.currentPos, activeCam, width, height);
        projectedNodes.set(node.id, { proj, node });
      }

      // 8. RENDER FILAMENT CONNECTIONS (Guaranteed high-visibility lines)
      if (debugEdges) {
        for (let i = 0; i < allFilaments.length; i++) {
          const filament = allFilaments[i];
          if (filament.state === 'hidden' || filament.drawProgress <= 0.02) continue;

          const pA = projectedNodes.get(filament.sourceId);
          const pB = projectedNodes.get(filament.targetId);
          if (!pA || !pB || !pA.proj.inView || !pB.proj.inView) continue;

          const endX = pA.proj.x2d + (pB.proj.x2d - pA.proj.x2d) * filament.drawProgress;
          const endY = pA.proj.y2d + (pB.proj.y2d - pA.proj.y2d) * filament.drawProgress;
          const avgDepthAlpha = (pA.proj.depthAlpha + pB.proj.depthAlpha) * 0.5;

          ctx.save();
          const isHoveredFil = hoveredEdge?.id === filament.id;
          const isSelectedFil = storeState.selectedEdgeId === filament.id;

          if (filament.is_hidden) {
            // AI Inferred Link: Dashed Amber Filament
            ctx.setLineDash([8, 5]);
            ctx.beginPath();
            ctx.moveTo(pA.proj.x2d, pA.proj.y2d);
            ctx.lineTo(endX, endY);
            const strokeAlpha = (isHoveredFil || isSelectedFil) ? 1.0 : clamp(filament.opacity * avgDepthAlpha, 0.45, 1.0);
            ctx.strokeStyle = `rgba(245, 158, 11, ${strokeAlpha.toFixed(3)})`;
            ctx.lineWidth = 2.2 * ((pA.proj.scale + pB.proj.scale) * 0.5);
            ctx.stroke();

            // Amber Traveling Pulse
            if (filament.pulsePosition !== undefined) {
              const px = pA.proj.x2d + (pB.proj.x2d - pA.proj.x2d) * filament.pulsePosition;
              const py = pA.proj.y2d + (pB.proj.y2d - pA.proj.y2d) * filament.pulsePosition;
              ctx.beginPath();
              ctx.arc(px, py, 3.5, 0, Math.PI * 2);
              ctx.fillStyle = '#FBBF24';
              ctx.fill();
            }
          } else {
            // Evidence Relationship: Luminous Filament
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(pA.proj.x2d, pA.proj.y2d);
            ctx.lineTo(endX, endY);

            const isFocused = filament.state === 'focused' || isHoveredFil || isSelectedFil;
            const strokeColor = isFocused ? '56, 189, 248' : '148, 163, 184';
            const strokeAlpha = isFocused ? 0.95 : clamp(filament.opacity * avgDepthAlpha, 0.45, 0.90);
            ctx.strokeStyle = `rgba(${strokeColor}, ${strokeAlpha.toFixed(3)})`;
            ctx.lineWidth = (isFocused ? 2.4 : 1.6) * ((pA.proj.scale + pB.proj.scale) * 0.5);
            ctx.stroke();

            // Traveling Pulse along active connections
            if (filament.pulsePosition !== undefined) {
              const px = pA.proj.x2d + (pB.proj.x2d - pA.proj.x2d) * filament.pulsePosition;
              const py = pA.proj.y2d + (pB.proj.y2d - pA.proj.y2d) * filament.pulsePosition;
              ctx.beginPath();
              ctx.arc(px, py, isFocused ? 3.5 : 2.2, 0, Math.PI * 2);
              ctx.fillStyle = isFocused ? '#38BDF8' : '#EDEDE9';
              ctx.fill();
            }
          }

          ctx.restore();
        }
      }

      // 9. RENDER ENTITY NODES (Sorted by depth — Painter's Algorithm)
      if (debugNodes) {
        const sortedEntities = Array.from(projectedNodes.values()).sort(
          (a, b) => b.proj.depth - a.proj.depth
        );

        const isNodeSelected = !!activeSelectedNodeId;
        const selectedNeighbors = new Set<string>();
        if (activeSelectedNodeId) {
          selectedNeighbors.add(activeSelectedNodeId);
          allFilaments.forEach(f => {
            if (f.sourceId === activeSelectedNodeId) selectedNeighbors.add(f.targetId);
            if (f.targetId === activeSelectedNodeId) selectedNeighbors.add(f.sourceId);
          });
        }

        for (let i = 0; i < sortedEntities.length; i++) {
          const { proj, node } = sortedEntities[i];
          if (!proj.inView || proj.depthAlpha <= 0.02) continue;

          const isSelected = storeState.selectedNodeIds.has(node.id) || node.id === activeSelectedNodeId;
          const isNeighbor = selectedNeighbors.has(node.id);
          const isHovered = hoveredNode?.id === node.id;
          const isDimmed = isNodeSelected && !isNeighbor;

          // Guaranteed visible, readable size (between 8.5px and 24px)
          const baseRadius = (node.isBridge ? 12 : node.risk === 'HIGH' ? 11 : 9.5) * proj.scale * node.scale;
          const radius = clamp(baseRadius, 8.5, 24);
          const nodeOpacity = isDimmed ? 0.22 : (isSelected || isHovered ? 1.0 : clamp(proj.depthAlpha, 0.45, 1.0));

          const colorScheme = ENTITY_COLORS[node.kind] || DEFAULT_COLOR;

          ctx.save();
          ctx.globalAlpha = nodeOpacity;

          // Bridge Node Rose Beacon Halo
          if (node.isBridge && !isDimmed) {
            const haloPulse = 0.5 + 0.5 * Math.sin(now * 0.004);
            const auraRadius = radius + 6 + haloPulse * 8;
            ctx.beginPath();
            ctx.arc(proj.x2d, proj.y2d, auraRadius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(251, 113, 133, ${(0.22 + haloPulse * 0.18).toFixed(3)})`;
            ctx.fill();
            ctx.beginPath();
            ctx.arc(proj.x2d, proj.y2d, auraRadius, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(251, 113, 133, 0.65)';
            ctx.lineWidth = 1.4;
            ctx.stroke();
          }

          // Luminous Outer Ring
          ctx.beginPath();
          ctx.arc(proj.x2d, proj.y2d, radius + 3, 0, Math.PI * 2);
          ctx.fillStyle = isSelected
            ? 'rgba(56, 189, 248, 0.25)'
            : (node.risk === 'HIGH' ? 'rgba(244, 63, 94, 0.25)' : 'rgba(255, 255, 255, 0.06)');
          ctx.fill();

          // Main Vibrant Node Body
          ctx.beginPath();
          ctx.arc(proj.x2d, proj.y2d, radius, 0, Math.PI * 2);
          ctx.fillStyle = isSelected ? '#0284C7' : (node.risk === 'HIGH' ? '#BE123C' : colorScheme.fill);
          ctx.fill();

          // High-contrast Border
          ctx.lineWidth = isSelected ? 3.2 : (node.risk === 'HIGH' ? 2.5 : 2.0);
          ctx.strokeStyle = isSelected ? '#38BDF8' : (node.risk === 'HIGH' ? '#FB7185' : colorScheme.stroke);
          ctx.stroke();

          // Single-letter Badge Icon inside node
          if (radius >= 9) {
            ctx.font = `700 ${Math.round(radius * 1.05)}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#FFFFFF';
            ctx.fillText(colorScheme.badge, proj.x2d, proj.y2d + 0.5);
          }

          // Context-Aware Anti-Aliased Label with Background Pill
          if (debugLabels && (!isDimmed || isSelected || isHovered)) {
            const fontSize = clamp(Math.round(11 * proj.scale), 9.5, 13);
            ctx.font = `600 ${fontSize}px monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'alphabetic';

            const labelText = node.name;
            const textWidth = ctx.measureText(labelText).width;
            const pillY = proj.y2d + radius + 7;

            // Label backdrop pill
            ctx.fillStyle = isSelected ? 'rgba(14, 165, 233, 0.25)' : 'rgba(10, 13, 20, 0.88)';
            ctx.strokeStyle = isSelected ? '#38BDF8' : 'rgba(255, 255, 255, 0.15)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(proj.x2d - textWidth / 2 - 6, pillY, textWidth + 12, fontSize + 6, 4);
            ctx.fill();
            ctx.stroke();

            // Label text
            ctx.fillStyle = isSelected ? '#38BDF8' : (node.risk === 'HIGH' ? '#FDA4AF' : '#F8FAFC');
            ctx.fillText(labelText, proj.x2d, pillY + fontSize);
          }

          ctx.restore();
        }
      }

      raf = requestAnimationFrame(render);
    };

    raf = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [
    allFilaments,
    sceneNodes,
    activeSelectedNodeId,
    hoveredNode,
    hoveredEdge,
    navMode,
    activePath,
    pathStep,
    showAiLinks,
    storeState.selectedNodeIds,
    storeState.selectedEdgeId,
    debugNodes,
    debugEdges,
    debugLabels,
    debugAxes,
    debugCalibration
  ]);

  return (
    <div className={styles.stage} ref={containerRef}>
      {/* 3D Living Canvas */}
      <canvas
        ref={canvasRef}
        className={`${styles.canvas} ${isDraggingRef.current ? styles.canvasGrabbing : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onClick={handleClick}
        onContextMenu={e => e.preventDefault()}
      />

      {/* Top Tactical HUD */}
      <div className={styles.topHud}>
        <div className={styles.hudBadge}>
          <span className={styles.hudDot} />
          <span>IMMERSIVE SPATIAL · {navMode}</span>
        </div>

        <div className={styles.topActions}>
          <button
            className={`${styles.btn} ${showAiLinks ? styles.btnAiActive : ''}`}
            onClick={() => setShowAiLinks(!showAiLinks)}
            title="Toggle AI inferred relationships"
          >
            <span>◈</span> AI LINKS {showAiLinks ? 'ON' : 'OFF'}
          </button>

          <button
            className={`${styles.btn} ${navMode === 'FREE' ? styles.btnActive : ''}`}
            onClick={() => setNavMode(navMode === 'CINEMATIC' ? 'FREE' : 'CINEMATIC')}
            title="Toggle Free 3D Camera Exploration"
          >
            <span>⎈</span> {navMode === 'FREE' ? 'FREE EXPLORE' : 'CINEMATIC'}
          </button>

          <button
            className={styles.btn}
            onClick={fitCameraToGraph}
            title="Fit camera to entire graph bounding box"
          >
            <span>⌖</span> FIT VIEW
          </button>

          <button
            className={`${styles.btn} ${showDebug ? styles.btnActive : ''}`}
            onClick={() => setShowDebug(!showDebug)}
            title="Toggle 3D Graph Diagnostics & Calibration Panel (Hotkey: D)"
          >
            <span>⚙</span> DIAGNOSTICS
          </button>

          {onLocateOperational && (
            <button className={styles.btn} onClick={onLocateOperational} title="Return to Operational 2D View">
              <span>⌖</span> OPERATIONAL GRAPH
            </button>
          )}
        </div>
      </div>

      {/* Diagnostics & Debug Panel (Phase 9) */}
      {showDebug && (
        <div className={styles.debugPanel}>
          <div className={styles.debugTitle}>
            <span>3D GRAPH DIAGNOSTICS</span>
            <button
              onClick={() => setShowDebug(false)}
              style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: '13px' }}
            >
              ✕
            </button>
          </div>

          <div className={styles.debugMetric}>
            <span>Total Nodes:</span>
            <b>{sceneNodes.size}</b>
          </div>
          <div className={styles.debugMetric}>
            <span>Total Edges:</span>
            <b>{allFilaments.length}</b>
          </div>
          <div className={styles.debugMetric}>
            <span>Graph Bounds:</span>
            <b>{graphBounds.size.width} × {graphBounds.size.height} × {graphBounds.size.depth}</b>
          </div>
          <div className={styles.debugMetric}>
            <span>Camera Pos:</span>
            <b>({Math.round(cameraRef.current.x)}, {Math.round(cameraRef.current.y)}, {Math.round(cameraRef.current.z)})</b>
          </div>

          <label className={styles.debugRow}>
            <input
              type="checkbox"
              checked={debugNodes}
              onChange={e => setDebugNodes(e.target.checked)}
            />
            <span>Show Graph Nodes ({sceneNodes.size})</span>
          </label>

          <label className={styles.debugRow}>
            <input
              type="checkbox"
              checked={debugEdges}
              onChange={e => setDebugEdges(e.target.checked)}
            />
            <span>Show Graph Edges ({allFilaments.length})</span>
          </label>

          <label className={styles.debugRow}>
            <input
              type="checkbox"
              checked={debugLabels}
              onChange={e => setDebugLabels(e.target.checked)}
            />
            <span>Show Entity Labels</span>
          </label>

          <label className={styles.debugRow}>
            <input
              type="checkbox"
              checked={debugAxes}
              onChange={e => setDebugAxes(e.target.checked)}
            />
            <span>Show 3D Axes & Origin (XYZ)</span>
          </label>

          <label className={styles.debugRow}>
            <input
              type="checkbox"
              checked={debugCalibration}
              onChange={e => setDebugCalibration(e.target.checked)}
            />
            <span>Show Calibration Spheres (RGB)</span>
          </label>
        </div>
      )}

      {/* Sequential Investigation Trail Bar */}
      {activePath.length > 1 && (
        <div className={styles.pathBar}>
          <span className={styles.pathStep}>
            TRAVERSING HOP {pathStep + 1} OF {activePath.length - 1}
          </span>
          <div className={styles.pathControls}>
            <button
              className={styles.pathBtn}
              onClick={() => setPathStep(Math.max(0, pathStep - 1))}
              disabled={pathStep === 0}
            >
              ◀ PREV
            </button>
            <button
              className={styles.pathBtn}
              onClick={() => setPathStep(Math.min(activePath.length - 2, pathStep + 1))}
              disabled={pathStep >= activePath.length - 2}
            >
              NEXT ▶
            </button>
          </div>
        </div>
      )}

      {/* Node Hover Tooltip */}
      {hoveredNode && (
        <div
          className={styles.hoverCard}
          style={{
            left: `${project3D(hoveredNode.currentPos, cameraRef.current, canvasRef.current?.clientWidth || 900, canvasRef.current?.clientHeight || 600).x2d}px`,
            top: `${project3D(hoveredNode.currentPos, cameraRef.current, canvasRef.current?.clientWidth || 900, canvasRef.current?.clientHeight || 600).y2d}px`
          }}
        >
          <div className={styles.hoverKind}>{hoveredNode.kind}</div>
          <div className={styles.hoverName}>{hoveredNode.name}</div>
          <div className={styles.hoverMeta}>
            {hoveredNode.degree} connections · Community #{hoveredNode.cluster + 1}
            {hoveredNode.isBridge ? ' · Bridge Broker' : ''}
          </div>
        </div>
      )}

      {/* Edge Hover Tooltip */}
      {hoveredEdge && !hoveredNode && (
        <div
          className={styles.hoverCardEdge}
          style={{
            left: `${((project3D(sceneNodes.get(hoveredEdge.sourceId)?.currentPos || { x: 0, y: 0, z: 0 }, cameraRef.current, canvasRef.current?.clientWidth || 900, canvasRef.current?.clientHeight || 600).x2d +
                     project3D(sceneNodes.get(hoveredEdge.targetId)?.currentPos || { x: 0, y: 0, z: 0 }, cameraRef.current, canvasRef.current?.clientWidth || 900, canvasRef.current?.clientHeight || 600).x2d) * 0.5)}px`,
            top: `${((project3D(sceneNodes.get(hoveredEdge.sourceId)?.currentPos || { x: 0, y: 0, z: 0 }, cameraRef.current, canvasRef.current?.clientWidth || 900, canvasRef.current?.clientHeight || 600).y2d +
                    project3D(sceneNodes.get(hoveredEdge.targetId)?.currentPos || { x: 0, y: 0, z: 0 }, cameraRef.current, canvasRef.current?.clientWidth || 900, canvasRef.current?.clientHeight || 600).y2d) * 0.5)}px`
          }}
        >
          <div className={styles.hoverKind} style={{ color: hoveredEdge.is_hidden ? '#F59E0B' : '#38BDF8' }}>
            {hoveredEdge.is_hidden ? 'AI INFERRED HYPOTHESIS' : 'VERIFIED RELATIONSHIP'}
          </div>
          <div className={styles.hoverName} style={{ fontSize: '11px' }}>
            {hoveredEdge.type.toUpperCase()} · {hoveredEdge.conf}% CONFIDENCE
          </div>
        </div>
      )}

      {/* Bottom Camera & Exploration Controls */}
      <div className={styles.bottomHud}>
        <div className={styles.navGroup}>
          <button className={styles.btn} onClick={resetToOverview} title="Reset camera to overview">
            OVERVIEW
          </button>
          <button
            className={styles.btn}
            onClick={() => {
              const numComms = clusterCentroids.size || 1;
              const nextIdx = (activeClusterIndex + 1) % numComms;
              setActiveClusterIndex(nextIdx);
              focusCluster(nextIdx);
            }}
            title="Focus camera on community cluster"
          >
            CLUSTER #{activeClusterIndex + 1}
          </button>
          {activeSelectedNodeId && (
            <>
              <button
                className={styles.btn}
                onClick={() => focusEntity(activeSelectedNodeId)}
                title="Center camera on selected entity"
              >
                FOCUS
              </button>
              <button
                className={styles.btn}
                onClick={() => expandNeighborhood(activeSelectedNodeId, 1)}
                title="Isolate 1-hop neighborhood"
              >
                1-HOP
              </button>
              <button
                className={styles.btn}
                onClick={() => expandNeighborhood(activeSelectedNodeId, 2)}
                title="Expand 2-hop neighborhood"
              >
                2-HOP
              </button>
            </>
          )}
        </div>

        {/* Tactical Keybinding Hints */}
        <div className={styles.kbdHint}>
          <span><span className={styles.kbdKey}>ESC</span> clear</span>
          <span><span className={styles.kbdKey}>F</span> focus</span>
          <span><span className={styles.kbdKey}>1</span> / <span className={styles.kbdKey}>2</span> hops</span>
          <span><span className={styles.kbdKey}>D</span> diagnostics</span>
          <span><span className={styles.kbdKey}>H</span> ai links</span>
        </div>
      </div>
    </div>
  );
};
