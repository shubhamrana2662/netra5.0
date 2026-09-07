"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Phone,
  Wallet,
  Building2,
  IndianRupee,
  Network,
  Search,
  RefreshCw,
  X,
  Sparkles,
  Layers,
  GitBranch,
  CircleDot,
  Orbit,
  TreePine,
  Focus,
  SlidersHorizontal,
  Eye,
  EyeOff,
  Maximize2,
  ZoomIn,
  ZoomOut,
  Box,
  Cuboid,
  Layers3,
  PhoneCall,
  DollarSign,
  Globe,
} from "lucide-react";
import dynamic from "next/dynamic";
import { useUiStore } from "@/stores";
import {
  NeoCard,
  NeoButton,
  NeoInput,
  NeoBadge,
  NeoPageHeader,
  NeoSkeleton,
  NeoEmptyState,
} from "@/components/ui/neomorphic";
import { CaseContextBar } from "@/components/layout/CaseContextBar";
import { graphApi } from "@/lib/api";
import { useInvestigationStore } from "@/stores";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { cn } from "@/lib/utils";

const Graph3DCanvas = dynamic(() => import("@/components/graph/Graph3DCanvas"), { ssr: false, loading: () => <div className="flex h-full w-full items-center justify-center bg-[#020617] text-cyan-400 font-mono text-xs">Initializing 3D Topology...</div> });

/* ────────────────────────────────────────────────────────────────
   ENTITY TYPE VISUAL CONFIG
   ──────────────────────────────────────────────────────────────── */
const ENTITY_CONFIG: Record<string, { icon: any; color: string; bg: string; border: string; label: string; hex: string }> = {
  PER:      { icon: User,        color: "text-blue-600",    bg: "bg-blue-50 dark:bg-blue-950/40",    border: "border-blue-400/60 dark:border-blue-500/40",    label: "Person",       hex: "#3B82F6" },
  PHONE:    { icon: Phone,       color: "text-purple-600",  bg: "bg-purple-50 dark:bg-purple-950/40",  border: "border-purple-400/60 dark:border-purple-500/40",  label: "Phone",        hex: "#8B5CF6" },
  UPI:      { icon: Wallet,      color: "text-amber-600",   bg: "bg-amber-50 dark:bg-amber-950/40",   border: "border-amber-400/60 dark:border-amber-500/40",   label: "UPI VPA",      hex: "#D97706" },
  ACCOUNT:  { icon: Building2,   color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-950/40", border: "border-emerald-400/60 dark:border-emerald-500/40", label: "Bank Account", hex: "#059669" },
  BANK:     { icon: Building2,   color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-950/40", border: "border-emerald-400/60 dark:border-emerald-500/40", label: "Bank Branch",  hex: "#059669" },
  ORG:      { icon: Building2,   color: "text-slate-500",   bg: "bg-slate-100/80 dark:bg-slate-800/40",   border: "border-slate-400/60 dark:border-slate-500/40",   label: "Organization", hex: "#64748B" },
  AMOUNT:   { icon: IndianRupee, color: "text-rose-600",    bg: "bg-rose-50 dark:bg-rose-950/40",    border: "border-rose-400/60 dark:border-rose-500/40",    label: "Amount",       hex: "#E11D48" },
};

const ALL_ENTITY_TYPES = Object.keys(ENTITY_CONFIG);

/* ────────────────────────────────────────────────────────────────
   LAYOUT ALGORITHMS
   ──────────────────────────────────────────────────────────────── */
type LayoutMode = "force" | "radial" | "hierarchical" | "clustered";

const LAYOUT_OPTIONS: { value: LayoutMode; label: string; icon: any; desc: string }[] = [
  { value: "force",         label: "Force-Directed",  icon: Orbit,      desc: "Physics simulation — connected nodes attract" },
  { value: "radial",        label: "Radial",          icon: CircleDot,  desc: "Hub-centric — high-degree nodes at center" },
  { value: "hierarchical",  label: "Hierarchical",    icon: TreePine,   desc: "Tree layout — flows top-down from roots" },
  { value: "clustered",     label: "Type Clusters",   icon: Layers,     desc: "Grouped by entity type — reveals structure" },
];

/* Simple force-directed simulation (Fruchterman-Reingold) */
function forceDirectedLayout(rawNodes: any[], rawEdges: any[], width: number, height: number): { x: number; y: number }[] {
  const N = rawNodes.length;
  if (N === 0) return [];

  const area = width * height;
  const k = Math.sqrt(area / Math.max(1, N)) * 0.85;
  const iterations = 80;
  const cooling = 0.97;
  let temp = width / 4;

  // Initialize random positions
  const pos = rawNodes.map((_, i) => ({
    x: width / 2 + (Math.random() - 0.5) * width * 0.6,
    y: height / 2 + (Math.random() - 0.5) * height * 0.6,
  }));

  const nodeIdxMap = new Map<string, number>();
  rawNodes.forEach((n, i) => nodeIdxMap.set(n.id, i));

  for (let iter = 0; iter < iterations; iter++) {
    const disp = pos.map(() => ({ x: 0, y: 0 }));

    // Repulsive forces between all pairs
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        let dx = pos[i].x - pos[j].x;
        let dy = pos[i].y - pos[j].y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        let force = (k * k) / dist;
        let fx = (dx / dist) * force;
        let fy = (dy / dist) * force;
        disp[i].x += fx;
        disp[i].y += fy;
        disp[j].x -= fx;
        disp[j].y -= fy;
      }
    }

    // Attractive forces along edges
    for (const e of rawEdges) {
      const si = nodeIdxMap.get(e.source);
      const ti = nodeIdxMap.get(e.target);
      if (si === undefined || ti === undefined) continue;
      let dx = pos[si].x - pos[ti].x;
      let dy = pos[si].y - pos[ti].y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      let force = (dist * dist) / k;
      let fx = (dx / dist) * force;
      let fy = (dy / dist) * force;
      disp[si].x -= fx;
      disp[si].y -= fy;
      disp[ti].x += fx;
      disp[ti].y += fy;
    }

    // Apply displacements with temperature limit
    for (let i = 0; i < N; i++) {
      let dist = Math.sqrt(disp[i].x * disp[i].x + disp[i].y * disp[i].y) || 0.01;
      let scale = Math.min(dist, temp) / dist;
      pos[i].x += disp[i].x * scale;
      pos[i].y += disp[i].y * scale;
      // Keep within bounds
      pos[i].x = Math.max(60, Math.min(width - 60, pos[i].x));
      pos[i].y = Math.max(60, Math.min(height - 60, pos[i].y));
    }
    temp *= cooling;
  }

  return pos;
}

/* Radial layout — high-degree nodes at center */
function radialLayout(rawNodes: any[], rawEdges: any[], width: number, height: number): { x: number; y: number }[] {
  const cx = width / 2, cy = height / 2;
  const degreeMap = new Map<string, number>();
  rawNodes.forEach(n => degreeMap.set(n.id, 0));
  rawEdges.forEach(e => {
    degreeMap.set(e.source, (degreeMap.get(e.source) || 0) + 1);
    degreeMap.set(e.target, (degreeMap.get(e.target) || 0) + 1);
  });

  const sorted = [...rawNodes].sort((a, b) => (degreeMap.get(b.id) || 0) - (degreeMap.get(a.id) || 0));
  const idToIdx = new Map<string, number>();
  rawNodes.forEach((n, i) => idToIdx.set(n.id, i));

  const pos: { x: number; y: number }[] = new Array(rawNodes.length);

  // Place highest degree node at center, rest in concentric rings
  const ringCapacities = [1, 6, 12, 20, 30, 50, 80];
  let nodeIdx = 0;
  let ringIdx = 0;
  while (nodeIdx < sorted.length) {
    const cap = ringCapacities[Math.min(ringIdx, ringCapacities.length - 1)];
    const radius = ringIdx === 0 ? 0 : 100 + ringIdx * 90;
    const countInRing = Math.min(cap, sorted.length - nodeIdx);
    for (let i = 0; i < countInRing; i++) {
      const angle = (i / countInRing) * 2 * Math.PI - Math.PI / 2;
      const origIdx = idToIdx.get(sorted[nodeIdx].id)!;
      pos[origIdx] = {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      };
      nodeIdx++;
    }
    ringIdx++;
  }
  return pos;
}

/* Hierarchical layout — BFS from root nodes */
function hierarchicalLayout(rawNodes: any[], rawEdges: any[], width: number, height: number): { x: number; y: number }[] {
  const adj = new Map<string, string[]>();
  const inDeg = new Map<string, number>();
  rawNodes.forEach(n => { adj.set(n.id, []); inDeg.set(n.id, 0); });
  rawEdges.forEach(e => {
    adj.get(e.source)?.push(e.target);
    inDeg.set(e.target, (inDeg.get(e.target) || 0) + 1);
  });

  // Find roots (0 in-degree), fallback to highest-degree
  let roots = rawNodes.filter(n => (inDeg.get(n.id) || 0) === 0).map(n => n.id);
  if (roots.length === 0) roots = [rawNodes[0]?.id].filter(Boolean);

  const idToIdx = new Map<string, number>();
  rawNodes.forEach((n, i) => idToIdx.set(n.id, i));

  const levels: string[][] = [];
  const visited = new Set<string>();
  let queue = [...roots];
  queue.forEach(r => visited.add(r));

  while (queue.length > 0) {
    levels.push(queue);
    const nextQueue: string[] = [];
    for (const nid of queue) {
      for (const child of (adj.get(nid) || [])) {
        if (!visited.has(child)) {
          visited.add(child);
          nextQueue.push(child);
        }
      }
    }
    queue = nextQueue;
  }

  // Place orphans in last level
  rawNodes.forEach(n => {
    if (!visited.has(n.id)) levels.push([n.id]);
  });

  const pos: { x: number; y: number }[] = new Array(rawNodes.length);
  const levelHeight = height / Math.max(1, levels.length + 1);

  levels.forEach((level, li) => {
    const levelWidth = width / (level.length + 1);
    level.forEach((nid, ni) => {
      const origIdx = idToIdx.get(nid);
      if (origIdx !== undefined) {
        pos[origIdx] = { x: levelWidth * (ni + 1), y: levelHeight * (li + 0.5) };
      }
    });
  });

  return pos;
}

/* Clustered layout — group by entity_type */
function clusteredLayout(rawNodes: any[], _rawEdges: any[], width: number, height: number): { x: number; y: number }[] {
  const groups = new Map<string, number[]>();
  rawNodes.forEach((n, i) => {
    const t = n.entity_type || "OTHER";
    if (!groups.has(t)) groups.set(t, []);
    groups.get(t)!.push(i);
  });

  const typeList = [...groups.keys()];
  const clusterCount = typeList.length;
  const cols = Math.ceil(Math.sqrt(clusterCount));
  const rows = Math.ceil(clusterCount / cols);
  const cellW = width / cols;
  const cellH = height / rows;

  const pos: { x: number; y: number }[] = new Array(rawNodes.length);

  typeList.forEach((type, gi) => {
    const col = gi % cols;
    const row = Math.floor(gi / cols);
    const cx = cellW * col + cellW / 2;
    const cy = cellH * row + cellH / 2;
    const indices = groups.get(type)!;
    const clusterRadius = Math.min(cellW, cellH) * 0.35;

    indices.forEach((nodeIdx, ni) => {
      if (indices.length === 1) {
        pos[nodeIdx] = { x: cx, y: cy };
      } else {
        const angle = (ni / indices.length) * 2 * Math.PI - Math.PI / 2;
        const r = clusterRadius * Math.sqrt((ni + 1) / indices.length);
        pos[nodeIdx] = {
          x: cx + Math.cos(angle) * r,
          y: cy + Math.sin(angle) * r,
        };
      }
    });
  });

  return pos;
}

function applyLayout(mode: LayoutMode, rawNodes: any[], rawEdges: any[], w: number, h: number) {
  switch (mode) {
    case "force":         return forceDirectedLayout(rawNodes, rawEdges, w, h);
    case "radial":        return radialLayout(rawNodes, rawEdges, w, h);
    case "hierarchical":  return hierarchicalLayout(rawNodes, rawEdges, w, h);
    case "clustered":     return clusteredLayout(rawNodes, rawEdges, w, h);
    default:              return forceDirectedLayout(rawNodes, rawEdges, w, h);
  }
}

/* ────────────────────────────────────────────────────────────────
   CUSTOM NODE COMPONENT
   ──────────────────────────────────────────────────────────────── */
function CustomEntityNode({ data }: { data: any }) {
  const cfg = ENTITY_CONFIG[data.entity_type] || ENTITY_CONFIG.PER;
  const Icon = cfg.icon;
  const isHighlighted = data._highlighted;
  const isDimmed = data._dimmed;

  return (
    <div
      className={cn(
        "neo-card min-w-[150px] px-3 py-2 transition-all select-none border",
        cfg.border,
        isHighlighted && "ring-2 ring-accent ring-offset-1 ring-offset-neo-bg scale-110 z-10",
        isDimmed && "opacity-30 scale-95",
        !isDimmed && !isHighlighted && "hover:scale-105",
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-accent !w-2 !h-2" />
      <div className="flex items-center gap-2">
        <div className={cn("grid h-6 w-6 place-items-center rounded-md border shrink-0", cfg.border, cfg.bg)}>
          <Icon size={12} className={cfg.color} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-sans text-xs font-bold text-primary">{data.label}</p>
          <p className="font-mono text-[9px] uppercase tracking-wider text-muted">{cfg.label}</p>
        </div>
      </div>
      {data.bridge_score > 0.6 && (
        <div className="mt-1.5 flex items-center justify-between border-t border-neo-border/60 pt-1 text-[9px]">
          <span className="text-muted">Bridge Link:</span>
          <span className="font-bold text-accent font-mono">{(data.bridge_score * 100).toFixed(0)}%</span>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-accent !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { custom: CustomEntityNode };

/* ────────────────────────────────────────────────────────────────
   MAIN GRAPH PAGE — INNER (needs ReactFlowProvider)
   ──────────────────────────────────────────────────────────────── */
function EntityGraphInner() {
  const { activeCaseId } = useInvestigationStore();
  const reactFlowInstance = useReactFlow();

  // Data
  const [rawNodes, setRawNodes] = useState<any[]>([]);
  const [rawEdges, setRawEdges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Layout & Filtering
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("force");
  const [twoHop, setTwoHop] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(new Set(ALL_ENTITY_TYPES));
  const [edgeMinWeight, setEdgeMinWeight] = useState(0);
  const [showHiddenLinks, setShowHiddenLinks] = useState(true);
  const threeDEnabled = useUiStore((s) => s.threeDEnabled);
  const [is3D, setIs3D] = useState(true);

  // Inspectors
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const router = useRouter();
  const [selectedEdge, setSelectedEdge] = useState<any>(null);

  // UI
  const [showLayoutPanel, setShowLayoutPanel] = useState(false);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const CANVAS_W = 1200;
  const CANVAS_H = 800;

  /* ── Fetch raw graph data ── */
  const fetchGraph = useCallback(async () => {
    if (!activeCaseId) return;
    setLoading(true);
    try {
      const res = await graphApi.get(activeCaseId, twoHop);
      const data = res.data;
      setRawNodes(data.nodes || []);
      setRawEdges(data.edges || []);
    } catch (err) {
      console.error("Failed to load graph data", err);
    } finally {
      setLoading(false);
    }
  }, [activeCaseId, twoHop]);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  // Sync global 3D preference → local toggle (respect reducedMotion via scene store)
  useEffect(() => {
    if (!threeDEnabled) setIs3D(false);
  }, [threeDEnabled]);

  // Shared filtered data for both 2D and 3D
  const { visibleNodesFiltered, visibleEdgesFiltered } = useMemo(() => {
    if (rawNodes.length === 0) return { visibleNodesFiltered: [] as any[], visibleEdgesFiltered: [] as any[] };
    const visibleNodes = rawNodes.filter((n: any) => visibleTypes.has(n.entity_type || "PER"));
    const visibleNodeIds = new Set(visibleNodes.map((n: any) => n.id));
    const visibleEdges = rawEdges.filter((e: any) => {
      if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
      if (!showHiddenLinks && e.edge_type === "hidden_link") return false;
      if (edgeMinWeight > 0 && (e.weight || 0) < edgeMinWeight) return false;
      return true;
    });
    return { visibleNodesFiltered: visibleNodes, visibleEdgesFiltered: visibleEdges };
  }, [rawNodes, rawEdges, visibleTypes, showHiddenLinks, edgeMinWeight]);

  /* ── Apply layout + filtering to produce ReactFlow nodes/edges ── */
  useEffect(() => {
    if (rawNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Filter nodes by visible types
    const visibleNodes = rawNodes.filter(n => visibleTypes.has(n.entity_type || "PER"));
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));

    // Filter edges: both endpoints visible, optional weight/type filter
    const visibleEdges = rawEdges.filter(e => {
      if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
      if (!showHiddenLinks && e.edge_type === "hidden_link") return false;
      if (edgeMinWeight > 0 && (e.weight || 0) < edgeMinWeight) return false;
      return true;
    });

    // Compute layout
    const positions = applyLayout(layoutMode, visibleNodes, visibleEdges, CANVAS_W, CANVAS_H);

    // Determine highlighted/dimmed based on focusedNodeId
    const neighborIds = new Set<string>();
    if (focusedNodeId) {
      neighborIds.add(focusedNodeId);
      visibleEdges.forEach(e => {
        if (e.source === focusedNodeId) neighborIds.add(e.target);
        if (e.target === focusedNodeId) neighborIds.add(e.source);
      });
    }

    // Build ReactFlow nodes
    const layoutNodes: Node[] = visibleNodes.map((n, idx) => ({
      id: n.id,
      type: "custom",
      position: positions[idx] || { x: 0, y: 0 },
      data: {
        ...n,
        label: n.canonical_value || n.label || n.id,
        _highlighted: focusedNodeId ? neighborIds.has(n.id) : false,
        _dimmed: focusedNodeId ? !neighborIds.has(n.id) : false,
      },
    }));

    // Search highlight
    const q = searchQuery.toLowerCase();
    if (q) {
      layoutNodes.forEach(n => {
        const lbl = String((n.data as any)?.label || "").toLowerCase();
        (n.data as any)._highlighted = lbl.includes(q);
        (n.data as any)._dimmed = !lbl.includes(q);
      });
    }

    const layoutEdges: Edge[] = visibleEdges.map((e, idx) => {
      const isHidden = e.edge_type === "hidden_link";
      const dimEdge = focusedNodeId
        ? !(neighborIds.has(e.source) && neighborIds.has(e.target))
        : false;

      return {
        id: `e-${idx}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        animated: isHidden || (e.score && e.score > 0.8),
        style: {
          stroke: isHidden ? "var(--warn)" : "var(--text-muted)",
          strokeWidth: e.weight ? Math.min(4, Math.max(1.2, e.weight)) : 1.2,
          strokeDasharray: isHidden ? "5,4" : undefined,
          opacity: dimEdge ? 0.12 : 1,
          transition: "opacity 0.3s ease",
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: "var(--text-muted)", width: 12, height: 12 },
        data: e,
      };
    });

    setNodes(layoutNodes);
    setEdges(layoutEdges);

    // Fit view after layout changes
    setTimeout(() => {
      try { reactFlowInstance.fitView({ padding: 0.15, duration: 400 }); } catch {}
    }, 100);
  }, [rawNodes, rawEdges, layoutMode, visibleTypes, edgeMinWeight, showHiddenLinks, searchQuery, focusedNodeId, setNodes, setEdges, reactFlowInstance]);

  /* ── Toggle entity type visibility ── */
  const toggleType = (type: string) => {
    setVisibleTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const showAllTypes = () => setVisibleTypes(new Set(ALL_ENTITY_TYPES));
  const isolateType = (type: string) => setVisibleTypes(new Set([type]));

  /* ── Node/Edge click handlers ── */
  const onNodeClick = (_: any, node: Node) => {
    setSelectedNode(node.data);
    setSelectedEdge(null);
    setFocusedNodeId(node.id);
  };

  const onEdgeClick = (_: any, edge: Edge) => {
    setSelectedEdge(edge.data);
    setSelectedNode(null);
  };

  const clearFocus = () => {
    setFocusedNodeId(null);
    setSelectedNode(null);
    setSelectedEdge(null);
  };

  /* ── Stats for display ── */
  const stats = useMemo(() => {
    const visibleN = nodes.length;
    const visibleE = edges.length;
    const hiddenN = rawNodes.length - visibleN;
    const hiddenE = rawEdges.length - visibleE;
    return { visibleN, visibleE, hiddenN, hiddenE };
  }, [nodes, edges, rawNodes, rawEdges]);

  return (
    <div className="space-y-4 pb-12">
      <CaseContextBar />

      <NeoPageHeader
        title="Entity Connections Graph"
        subtitle="Network topology connecting suspects, devices, financial instruments, and hidden links."
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <NeoButton
              variant={twoHop ? "primary" : "standard"}
              size="sm"
              onClick={() => setTwoHop(v => !v)}
            >
              2-Hop
            </NeoButton>
            <NeoButton
              variant="standard"
              size="sm"
              leftIcon={<RefreshCw size={13} />}
              onClick={fetchGraph}
            >
              Reload
            </NeoButton>
          </div>
        }
      />

      {/* Graph Workspace */}
      <div className="relative h-[700px] w-full rounded-neo overflow-hidden border border-neo-border bg-neo-surface shadow-neo-raised">

        {/* ─── TOP TOOLBAR ─── */}
        <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 rounded-full border border-neo-border bg-neo-surface/90 p-1.5 shadow-neo-raised-sm backdrop-blur-md">
          {/* Search */}
          <div className="w-44">
            <NeoInput
              placeholder="Search nodes..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              leftIcon={<Search size={13} />}
              className="py-1 text-xs rounded-full"
            />
          </div>

          {/* Quick Type Filter Button */}
          <button
            onClick={() => { setShowFilterPanel(v => !v); setShowLayoutPanel(false); }}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-all",
              showFilterPanel
                ? "bg-accent text-white shadow-sm"
                : "border border-neo-border bg-neo-elevated text-secondary hover:text-primary"
            )}
          >
            <SlidersHorizontal size={12} />
            <span>Entities</span>
          </button>

          {/* Layout Selector Button */}
          <button
            onClick={() => { setShowLayoutPanel(v => !v); setShowFilterPanel(false); }}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-all",
              showLayoutPanel
                ? "bg-accent text-white shadow-sm"
                : "border border-neo-border bg-neo-elevated text-secondary hover:text-primary"
            )}
          >
            <GitBranch size={12} />
            <span>Layout</span>
          </button>

          {/* 3D / 2D Toggle */}
          <button
            onClick={() => setIs3D((v) => !v)}
            title={is3D ? "Switch to 2D Graph" : "Switch to 3D Topology"}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-all border border-neo-border",
              is3D ? "bg-accent/15 text-accent border-accent/40 font-bold" : "bg-neo-elevated text-secondary hover:text-primary"
            )}
          >
            {is3D ? <Cuboid size={12} /> : <Layers3 size={12} />}
            <span>{is3D ? "3D" : "2D"}</span>
          </button>

          {/* Clear Focus */}
          {focusedNodeId && (
            <button
              onClick={clearFocus}
              className="flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-1 text-xs font-bold text-rose-500 hover:bg-rose-500/25 transition-colors"
            >
              <X size={12} />
              Reset Focus
            </button>
          )}
        </div>

        {/* Backdrop for closing open floating panels */}
        {(showLayoutPanel || showFilterPanel) && (
          <div
            className="absolute inset-0 z-15"
            onClick={() => { setShowLayoutPanel(false); setShowFilterPanel(false); }}
          />
        )}

        {/* Stats badge */}
        <div className="absolute top-3 right-3 z-10 hidden sm:flex items-center gap-2">
          <span className="rounded-full bg-neo-surface/90 backdrop-blur-md border border-neo-border px-3 py-1 font-mono text-[10px] text-secondary shadow-neo-raised-sm">
            {stats.visibleN} nodes · {stats.visibleE} edges
            {stats.hiddenN > 0 && <span className="text-muted ml-1">({stats.hiddenN} hidden)</span>}
          </span>
        </div>

        {/* ─── LAYOUT PICKER PANEL ─── */}
        {showLayoutPanel && (
          <div className="absolute top-12 left-3 z-20 w-64 neo-card p-3 space-y-1.5 animate-in slide-in-from-top-2 duration-200">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted mb-2">Layout Algorithm</p>
            {LAYOUT_OPTIONS.map(opt => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.value}
                  onClick={() => { setLayoutMode(opt.value); setShowLayoutPanel(false); }}
                  className={cn(
                    "flex w-full items-start gap-2.5 rounded-neo-sm p-2 text-left text-xs transition-all",
                    layoutMode === opt.value
                      ? "bg-accent/10 text-accent font-semibold shadow-neo-inset-sm"
                      : "text-secondary hover:bg-neo-inset hover:text-primary"
                  )}
                >
                  <Icon size={15} className="shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">{opt.label}</p>
                    <p className="text-[10px] text-muted leading-tight mt-0.5">{opt.desc}</p>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* ─── FILTER & VISIBILITY PANEL ─── */}
        {showFilterPanel && (
          <div className="absolute top-12 left-3 z-20 w-72 neo-card p-3 space-y-3 animate-in slide-in-from-top-2 duration-200">
            {/* Entity Types */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-muted">Entity Types</p>
                <button onClick={showAllTypes} className="text-[10px] text-accent hover:underline font-semibold">
                  Show All
                </button>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {ALL_ENTITY_TYPES.map(type => {
                  const cfg = ENTITY_CONFIG[type];
                  const Icon = cfg.icon;
                  const active = visibleTypes.has(type);
                  const count = rawNodes.filter(n => n.entity_type === type).length;
                  return (
                    <button
                      key={type}
                      onClick={() => toggleType(type)}
                      onDoubleClick={() => isolateType(type)}
                      title={`Click: toggle · Double-click: isolate ${cfg.label}`}
                      className={cn(
                        "flex items-center gap-1.5 rounded-neo-sm px-2 py-1.5 text-[11px] font-medium border transition-all",
                        active
                          ? "bg-neo-surface border-neo-border text-primary shadow-neo-raised-sm"
                          : "bg-neo-inset border-transparent text-muted opacity-50"
                      )}
                    >
                      {active ? <Eye size={11} /> : <EyeOff size={11} />}
                      <Icon size={11} className={cfg.color} />
                      <span className="truncate">{cfg.label}</span>
                      <span className="ml-auto font-mono text-[9px] text-muted">{count}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Edge Controls */}
            <div className="border-t border-neo-border pt-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted mb-2">Edge Filters</p>
              <label className="flex items-center justify-between text-xs cursor-pointer">
                <span className="flex items-center gap-1.5 text-secondary">
                  <Sparkles size={12} className="text-warn" />
                  Show AI Hidden Links
                </span>
                <button
                  onClick={() => setShowHiddenLinks(v => !v)}
                  className={cn(
                    "relative h-5 w-9 rounded-full transition-colors",
                    showHiddenLinks ? "bg-accent" : "bg-neo-inset shadow-neo-inset-sm"
                  )}
                >
                  <span className={cn(
                    "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
                    showHiddenLinks ? "left-[18px]" : "left-0.5"
                  )} />
                </button>
              </label>
              <div className="mt-2">
                <label className="text-[10px] text-muted block mb-1">
                  Min Edge Weight: <span className="font-mono font-bold text-primary">{edgeMinWeight.toFixed(1)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={5}
                  step={0.5}
                  value={edgeMinWeight}
                  onChange={e => setEdgeMinWeight(parseFloat(e.target.value))}
                  className="w-full accent-accent h-1.5"
                />
              </div>
            </div>
          </div>
        )}

        {/* ─── 3D / 2D CANVAS ─── */}
        {loading ? (
          <div className="flex h-full w-full items-center justify-center">
            <NeoSkeleton className="h-4/5 w-4/5" />
          </div>
        ) : rawNodes.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center">
            <NeoEmptyState
              icon={<Network size={28} />}
              title="No Entity Graph Available"
              description="Upload investigation evidence to extract entities and generate link topology."
            />
          </div>
        ) : is3D ? (
          <div className="h-full w-full">
            <Graph3DCanvas
              nodes={visibleNodesFiltered.map((n: any) => ({
                id: n.id,
                entity_type: n.entity_type,
                label: n.canonical_value || n.label,
                canonical_value: n.canonical_value || n.label,
                degree_centrality: n.degree_centrality,
                bridge_score: n.bridge_score,
                community_id: n.community_id,
                mention_count: n.mention_count,
                first_seen: n.first_seen,
              }))}
              edges={visibleEdgesFiltered.map((e: any) => ({
                source: e.source,
                target: e.target,
                edge_type: e.edge_type,
                weight: e.weight,
                score: e.score,
                component_scores: e.component_scores,
              }))}
              focusedNodeId={focusedNodeId}
              searchQuery={searchQuery}
              onNodeSelect={(n) => {
                if (!n) {
                  clearFocus();
                } else {
                  const raw = rawNodes.find((r: any) => r.id === n.id);
                  if (raw) {
                    setSelectedNode({ ...raw, label: n.canonical_value || n.label });
                    setSelectedEdge(null);
                    setFocusedNodeId(n.id);
                  }
                }
              }}
              onEdgeSelect={(e) => {
                if (e) setSelectedEdge(e);
              }}
              className="h-full w-full"
            />
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={clearFocus}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.15}
            maxZoom={3}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="var(--text-faint)" gap={24} size={1} style={{ opacity: 0.3 }} />
            <Controls className="!bg-neo-surface !border-neo-border !shadow-neo-raised-sm !rounded-neo-sm" />
            <MiniMap
              className="!bg-neo-surface !border-neo-border !shadow-neo-raised-sm !rounded-neo-sm"
              nodeColor={(n: any) => {
                const cfg = ENTITY_CONFIG[n.data?.entity_type];
                return cfg?.hex || "#64748B";
              }}
              maskColor="var(--neo-inset)"
            />
          </ReactFlow>
        )}

        {/* ─── NODE INSPECTOR DRAWER ─── */}
        {selectedNode && (
          <div className="absolute top-3 right-3 z-20 w-80 rounded-neo neo-card p-4 space-y-3 animate-in slide-in-from-right-4 duration-200 backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-neo-border pb-2">
              <span className="text-[11px] font-bold text-muted uppercase tracking-wider">Entity Inspector</span>
              <button onClick={clearFocus} className="text-muted hover:text-primary p-1">
                <X size={14} />
              </button>
            </div>

            <div>
              <p className="font-mono text-sm font-bold text-primary truncate">{selectedNode.label}</p>
              <NeoBadge variant="accent" size="sm" className="mt-1">
                {ENTITY_CONFIG[selectedNode.entity_type]?.label || selectedNode.entity_type}
              </NeoBadge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 rounded-neo-sm bg-neo-inset border border-neo-border/50">
                <span className="text-[10px] text-muted block">Degree Centrality</span>
                <span className="font-bold text-primary font-mono">
                  {selectedNode.degree_centrality?.toFixed(3) || "--"}
                </span>
              </div>
              <div className="p-2 rounded-neo-sm bg-neo-inset border border-neo-border/50">
                <span className="text-[10px] text-muted block">Bridge Score</span>
                <span className="font-bold text-accent font-mono">
                  {selectedNode.bridge_score ? `${(selectedNode.bridge_score * 100).toFixed(0)}%` : "0%"}
                </span>
              </div>
            </div>

            {/* Focus on Neighbors */}
            <button
              onClick={() => setFocusedNodeId(focusedNodeId === selectedNode.id ? null : selectedNode.id)}
              className={cn(
                "neo-button w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold",
                focusedNodeId === selectedNode.id && "bg-accent/10 text-accent"
              )}
            >
              <Focus size={13} />
              {focusedNodeId === selectedNode.id ? "Show All Nodes" : "Focus on Neighbors"}
            </button>

            {selectedNode.first_seen && (
              <div className="text-[11px] text-muted">
                First seen: {new Date(selectedNode.first_seen).toLocaleDateString()}
              </div>
            )}

            {/* ── Forensic Deep-Linking Actions ── */}
            <div className="border-t border-neo-border pt-2 space-y-1.5">
              <p className="text-[10px] font-bold text-muted uppercase tracking-wider">Forensic Jump</p>
              <button
                onClick={() => router.push(`/dashboard/communications?search=${encodeURIComponent(selectedNode.label)}`)}
                className="neo-button w-full flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-left"
              >
                <PhoneCall size={12} className="text-accent" />
                Search in Communications
              </button>
              <button
                onClick={() => router.push(`/dashboard/transactions?search=${encodeURIComponent(selectedNode.label)}`)}
                className="neo-button w-full flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-left"
              >
                <DollarSign size={12} className="text-accent" />
                Search in Financial Trail
              </button>
              <button
                onClick={() => router.push(`/dashboard/intel?query=${encodeURIComponent(selectedNode.label)}`)}
                className="neo-button w-full flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-left"
              >
                <Globe size={12} className="text-accent" />
                Cross-Case Intel Lookup
              </button>
            </div>
          </div>
        )}

        {/* ─── EDGE INSPECTOR DRAWER ─── */}
        {selectedEdge && !selectedNode && (
          <div className="absolute top-3 right-3 z-20 w-80 rounded-neo neo-card p-4 space-y-3 animate-in slide-in-from-right-4 duration-200 backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-neo-border pb-2">
              <span className="text-[11px] font-bold text-muted uppercase tracking-wider">Link Explainability</span>
              <button onClick={() => setSelectedEdge(null)} className="text-muted hover:text-primary p-1">
                <X size={14} />
              </button>
            </div>

            <div>
              <p className="text-xs font-bold text-primary">
                {selectedEdge.edge_type === "hidden_link" ? "Hidden Predictive Link" : "Observed Evidence Co-occurrence"}
              </p>
              {selectedEdge.score && (
                <p className="text-sm font-bold text-accent font-mono mt-0.5">
                  Confidence: {(selectedEdge.score * 100).toFixed(1)}%
                </p>
              )}
            </div>

            {selectedEdge.component_scores && (
              <div className="space-y-1.5 text-xs border-t border-neo-border/50 pt-2">
                <span className="text-[10.5px] font-semibold text-secondary">
                  Mathematical Components:
                </span>
                {Object.entries(selectedEdge.component_scores).map(([k, v]: any) => (
                  <div key={k} className="flex justify-between font-mono text-[11px]">
                    <span className="text-muted capitalize">{k.replace("_", " ")}:</span>
                    <span className="font-bold text-primary">{Number(v).toFixed(3)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ─── CLUSTER LEGEND (when clustered layout) ─── */}
        {layoutMode === "clustered" && (
          <div className="absolute bottom-14 left-3 z-10 neo-card p-2.5 space-y-1">
            <p className="text-[9px] font-bold uppercase tracking-wider text-muted mb-1.5">Cluster Legend</p>
            {ALL_ENTITY_TYPES.filter(t => visibleTypes.has(t)).map(type => {
              const cfg = ENTITY_CONFIG[type];
              const Icon = cfg.icon;
              const count = rawNodes.filter(n => n.entity_type === type).length;
              return count > 0 ? (
                <div key={type} className="flex items-center gap-1.5 text-[10px]">
                  <span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: cfg.hex }} />
                  <span className="text-secondary font-medium">{cfg.label}</span>
                  <span className="ml-auto font-mono text-muted">{count}</span>
                </div>
              ) : null;
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────
   WRAPPER — provides ReactFlowProvider
   ──────────────────────────────────────────────────────────────── */
export default function EntityGraphPage() {
  return (
    <ReactFlowProvider>
      <EntityGraphInner />
    </ReactFlowProvider>
  );
}
