"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, Stars, Environment, ContactShadows } from "@react-three/drei";
import * as THREE from "three";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { cn } from "@/lib/utils";

// ── Entity visual config (mirrors graph/page.tsx) ───────────────────────
const ENTITY_COLOR: Record<string, string> = {
  PER: "#3B82F6",
  PHONE: "#8B5CF6",
  UPI: "#D97706",
  ACCOUNT: "#059669",
  BANK: "#059669",
  ORG: "#64748B",
  AMOUNT: "#E11D48",
  LOCATION: "#0EA5E9",
  EMAIL: "#A855F7",
  DEVICE: "#475569",
};
const ENTITY_LABEL: Record<string, string> = {
  PER: "Person",
  PHONE: "Phone",
  UPI: "UPI",
  ACCOUNT: "Account",
  BANK: "Bank",
  ORG: "Org",
  AMOUNT: "Amount",
  LOCATION: "Location",
  EMAIL: "Email",
  DEVICE: "Device",
};

interface GraphNode {
  id: string;
  entity_type: string;
  label?: string;
  canonical_value?: string;
  degree_centrality?: number;
  bridge_score?: number;
  community_id?: number;
  mention_count?: number;
  first_seen?: string;
}
interface GraphEdge {
  source: string;
  target: string;
  edge_type?: string;
  weight?: number;
  score?: number;
  component_scores?: Record<string, number>;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  focusedNodeId?: string | null;
  searchQuery?: string;
  onNodeSelect?: (node: GraphNode | null) => void;
  onEdgeSelect?: (edge: GraphEdge | null) => void;
  className?: string;
}

// ── 3D force layout (Fruchterman-Reingold in 3D) ─────────────────────
function forceLayout3D(
  nodes: GraphNode[],
  edges: GraphEdge[],
  size: number = 22
): Map<string, THREE.Vector3> {
  const N = nodes.length;
  if (N === 0) return new Map();
  if (N === 1) {
    const m = new Map<string, THREE.Vector3>();
    m.set(nodes[0].id, new THREE.Vector3(0, 0, 0));
    return m;
  }

  const k = Math.cbrt((size * size * size) / N) * 0.9;
  const iterations = 70;
  let temp = size / 4;

  const pos = new Map<string, THREE.Vector3>();
  const idToIdx = new Map<string, number>();
  nodes.forEach((n, i) => {
    idToIdx.set(n.id, i);
    // spherical random init
    const r = size * 0.28 * Math.cbrt(Math.random());
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    pos.set(n.id, new THREE.Vector3(r * Math.sin(phi) * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta) * 0.7, r * Math.cos(phi)));
  });

  const disp = new Map<string, THREE.Vector3>();
  for (let iter = 0; iter < iterations; iter++) {
    nodes.forEach((n) => disp.set(n.id, new THREE.Vector3(0, 0, 0)));

    // repulsive
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const a = nodes[i], b = nodes[j];
        const pa = pos.get(a.id)!, pb = pos.get(b.id)!;
        const delta = pa.clone().sub(pb);
        const dist = delta.length() || 0.01;
        const force = (k * k) / dist;
        const dir = delta.clone().normalize().multiplyScalar(force);
        disp.get(a.id)!.add(dir);
        disp.get(b.id)!.sub(dir);
      }
    }
    // attractive along edges
    for (const e of edges) {
      const pa = pos.get(e.source), pb = pos.get(e.target);
      if (!pa || !pb) continue;
      const delta = pa.clone().sub(pb);
      const dist = delta.length() || 0.01;
      const force = (dist * dist) / k * 0.7;
      const dir = delta.clone().normalize().multiplyScalar(force);
      disp.get(e.source)!.sub(dir);
      disp.get(e.target)!.add(dir);
    }
    // gravity to center
    nodes.forEach((n) => {
      const p = pos.get(n.id)!;
      const d = disp.get(n.id)!;
      const centerForce = p.clone().multiplyScalar(-0.015);
      d.add(centerForce);
    });

    // move
    nodes.forEach((n) => {
      const p = pos.get(n.id)!;
      const d = disp.get(n.id)!;
      const len = d.length() || 0.01;
      const scale = Math.min(len, temp) / len;
      p.add(d.clone().multiplyScalar(scale));
      // clamp bounds
      const half = size / 2;
      p.x = THREE.MathUtils.clamp(p.x, -half, half);
      p.y = THREE.MathUtils.clamp(p.y, -half * 0.6, half * 0.6);
      p.z = THREE.MathUtils.clamp(p.z, -half, half);
    });
    temp *= 0.96;
  }
  return pos;
}

// ── Node mesh ─────────────────────────────────────────────────────────
function NodeMesh({
  node,
  pos,
  isFocused,
  isNeighbor,
  isDimmed,
  isSearchHit,
  onSelect,
}: {
  node: GraphNode;
  pos: THREE.Vector3;
  isFocused: boolean;
  isNeighbor: boolean;
  isDimmed: boolean;
  isSearchHit: boolean;
  onSelect: (n: GraphNode) => void;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  const [hovered, setHovered] = useState(false);
  const color = ENTITY_COLOR[node.entity_type] || "#64748B";
  const emissive = isFocused ? color : hovered ? "#7dd3fc" : color;
  const scaleBase = 0.22 + (node.degree_centrality || 0) * 0.35 + (node.bridge_score || 0) * 0.18;

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (!ref.current) return;
    // gentle float + bridge pulse
    const float = Math.sin(t * 0.7 + pos.x) * 0.06;
    ref.current.position.y = pos.y + float;
    if (node.bridge_score && node.bridge_score > 0.6 && !isDimmed) {
      const pulse = 1 + Math.sin(t * 2.8) * 0.12 * node.bridge_score;
      ref.current.scale.setScalar(scaleBase * pulse * (isFocused || hovered ? 1.45 : 1));
    } else {
      ref.current.scale.setScalar(scaleBase * (isFocused || hovered ? 1.45 : 1));
    }
    // emissive intensity
    const mat = ref.current.material as THREE.MeshStandardMaterial;
    if (mat) {
      const target = isFocused || hovered ? 1.8 : isDimmed ? 0.25 : 0.9;
      mat.emissiveIntensity = THREE.MathUtils.lerp(mat.emissiveIntensity, target, 0.12);
    }
  });

  const opacity = isDimmed ? 0.18 : isSearchHit ? 1 : 0.92;
  const showLabel = hovered || isFocused;

  return (
    <group position={[pos.x, 0, pos.z]}>
      <mesh
        ref={ref}
        position={[0, 0, 0]}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = "pointer"; }}
        onPointerOut={(e) => { e.stopPropagation(); setHovered(false); document.body.style.cursor = "auto"; }}
        onClick={(e) => { e.stopPropagation(); onSelect(node); }}
      >
        {/* use icosahedron for high-degree, octahedron for low */}
        {(node.degree_centrality || 0) > 0.5 ? <icosahedronGeometry args={[0.95, 1]} /> : <octahedronGeometry args={[0.95, 0]} />}
        <meshStandardMaterial color={color} emissive={emissive} emissiveIntensity={0.9} metalness={0.35} roughness={0.42} transparent opacity={opacity} />
      </mesh>
      {/* outer rim for critical bridge nodes */}
      {node.bridge_score !== undefined && node.bridge_score > 0.6 && !isDimmed && (
        <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
          <torusGeometry args={[0.55, 0.012, 8, 32]} />
          <meshBasicMaterial color="#fb7185" transparent opacity={isFocused ? 0.65 : 0.35} depthWrite={false} />
        </mesh>
      )}
      {/* selection pillar */}
      {isFocused && (
        <mesh position={[0, -4, 0]}>
          <cylinderGeometry args={[0.015, 0.015, 8, 6, 1, true]} />
          <meshBasicMaterial color={color} transparent opacity={0.22} depthWrite={false} />
        </mesh>
      )}
      {/* Html tooltip */}
      {showLabel && (
        <Html center distanceFactor={14} zIndexRange={[50, 0]} style={{ pointerEvents: "none" }}>
          <div className="pointer-events-none w-max rounded-neo-sm border border-soft cd-glass-heavy px-3 py-2 shadow-glass backdrop-blur-md">
            <p className="font-mono text-[11px] font-bold tracking-tight text-primary max-w-[180px] truncate">
              {node.canonical_value || node.label || node.id.slice(0, 12)}
            </p>
            <p className="mt-1 font-mono text-[9px] tracking-widest text-secondary">
              <span style={{ color }}>{ENTITY_LABEL[node.entity_type] || node.entity_type}</span> · DEG {(node.degree_centrality ?? 0).toFixed(2)}
              {node.bridge_score ? ` · BRIDGE ${(node.bridge_score * 100).toFixed(0)}%` : ""}
            </p>
            {node.mention_count !== undefined && (
              <p className="font-mono text-[9px] text-muted">MENTIONS {node.mention_count}</p>
            )}
          </div>
        </Html>
      )}
    </group>
  );
}

// ── Edge line with curve + traveling packet ───────────────────────────
function EdgeLine({
  a,
  b,
  edge,
  isActive,
  isDimmed,
  packetsOn,
}: {
  a: THREE.Vector3;
  b: THREE.Vector3;
  edge: GraphEdge;
  isActive: boolean;
  isDimmed: boolean;
  packetsOn: boolean;
}) {
  const packetRef = useRef<THREE.Mesh>(null!);
  const offset = useRef(Math.random());
  const isHidden = edge.edge_type === "hidden_link";
  const color = isHidden ? "#f59e0b" : isActive ? "#38bdf8" : "#475569";

  const { line, geo } = useMemo(() => {
    const mid = a.clone().add(b).multiplyScalar(0.5);
    // lift curve based on distance
    const dist = a.distanceTo(b);
    mid.y += Math.min(4.5, 0.8 + dist * 0.18);
    const curve = new THREE.QuadraticBezierCurve3(a.clone().add(new THREE.Vector3(0, 0.05, 0)), mid, b.clone().add(new THREE.Vector3(0, 0.05, 0)));
    const pts = curve.getPoints(32);
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const curveRef = curve;
    return { line: curveRef, geo: g };
  }, [a, b]);

  const mat = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity: isDimmed ? 0.08 : isHidden ? 0.62 : 0.28,
        linewidth: 1,
      }),
    [color, isHidden, isDimmed]
  );

  const lineObj = useMemo(() => new THREE.Line(geo, mat), [geo, mat]);

  useFrame((_, dt) => {
    const d = Math.min(dt, 0.05);
    // opacity damping
    const target = isDimmed ? 0.07 : isActive ? 0.85 : isHidden ? 0.62 : 0.26;
    mat.opacity = THREE.MathUtils.damp(mat.opacity, target, 6, d);
    if (isHidden && !isDimmed) {
      // dashed illusion via opacity pulse
      mat.opacity = 0.55 + Math.sin(performance.now() * 0.004) * 0.15;
    }
    if (packetRef.current && packetsOn && !isDimmed) {
      const speed = isHidden ? 0.32 : 0.16;
      offset.current = (offset.current + d * speed) % 1;
      line.getPoint(offset.current, packetRef.current.position);
      // float slightly above line
      packetRef.current.position.y += 0.08;
    }
  });

  // sync color when isHidden/isActive changes
  useEffect(() => {
    mat.color.set(color);
  }, [color, mat]);

  return (
    <group>
      <primitive object={lineObj} />
      {packetsOn && !isDimmed && (
        <mesh ref={packetRef}>
          <sphereGeometry args={[0.07, 8, 8]} />
          <meshBasicMaterial color={isHidden ? "#fbbf24" : "#7dd3fc"} transparent opacity={0.95} />
        </mesh>
      )}
    </group>
  );
}

// ── Auto-rotation when idle ───────────────────────────────────────────
function AutoRotate({ enabled }: { enabled: boolean }) {
  const { camera } = useThree();
  useFrame((state, dt) => {
    if (!enabled) return;
    const t = state.clock.elapsedTime;
    const d = Math.min(dt, 0.05);
    // slow orbit around y
    const radius = Math.sqrt(camera.position.x * camera.position.x + camera.position.z * camera.position.z);
    const angle = Math.atan2(camera.position.z, camera.position.x) + d * 0.07;
    camera.position.x = Math.cos(angle) * radius;
    camera.position.z = Math.sin(angle) * radius;
    camera.position.y += Math.sin(t * 0.18) * d * 0.06;
    camera.lookAt(0, 0, 0);
  });
  return null;
}

// ── Main canvas ───────────────────────────────────────────────────────
export default function Graph3DCanvas({
  nodes,
  edges,
  focusedNodeId,
  searchQuery,
  onNodeSelect,
  onEdgeSelect,
  className,
}: Props) {
  const [autoRotate, setAutoRotate] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const positions = useMemo(() => forceLayout3D(nodes, edges, 24), [nodes, edges]);

  const neighborSet = useMemo(() => {
    if (!focusedNodeId) return new Set<string>();
    const s = new Set<string>([focusedNodeId]);
    edges.forEach((e) => {
      if (e.source === focusedNodeId) s.add(e.target);
      if (e.target === focusedNodeId) s.add(e.source);
    });
    return s;
  }, [focusedNodeId, edges]);

  const searchLower = (searchQuery || "").toLowerCase();

  if (nodes.length === 0) {
    return (
      <div className={cn("flex h-full w-full items-center justify-center rounded-neo border border-neo-border bg-neo-surface", className)}>
        <div className="text-center">
          <p className="font-mono text-xs tracking-widest text-muted">NO NODES TO RENDER</p>
          <p className="mt-1 text-xs text-muted/70">Upload evidence to generate entity topology</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("relative h-full w-full overflow-hidden rounded-neo border border-neo-border bg-[#020617]", className)}>
      <Canvas
        camera={{ position: [14, 10, 18], fov: 52, near: 0.1, far: 120 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, powerPreference: "high-performance", alpha: true }}
        onPointerMissed={() => onNodeSelect?.(null)}
        style={{ background: "radial-gradient(ellipse 90% 70% at 50% 0%, #0B1A2E 0%, #020617 65%)" }}
      >
        <fog attach="fog" args={["#020617", 28, 62]} />
        <ambientLight intensity={0.65} color="#8fb8e8" />
        <directionalLight position={[10, 14, 10]} intensity={1.15} color="#dbeafe" />
        <pointLight position={[0, 8, 0]} intensity={18} color="#38bdf8" distance={45} decay={2} />
        <pointLight position={[-10, 6, -10]} intensity={10} color="#1e40af" distance={35} />

        <Stars radius={80} depth={30} count={2200} factor={3.4} saturation={0} fade speed={0.6} />
        <Environment preset="city" background={false} />

        {/* ground grid */}
        <gridHelper args={[48, 24, "#1e293b", "#0f172a"]} position={[0, -3.2, 0]} />

        <group>
          {edges.map((e, i) => {
            const a = positions.get(e.source), b = positions.get(e.target);
            if (!a || !b) return null;
            const touchesFocused = focusedNodeId === e.source || focusedNodeId === e.target;
            const dimmed = !!focusedNodeId && !touchesFocused;
            const isActive = touchesFocused;
            return (
              <EdgeLine
                key={`e-${i}-${e.source}-${e.target}`}
                a={a}
                b={b}
                edge={e}
                isActive={isActive}
                isDimmed={dimmed}
                packetsOn={true}
              />
            );
          })}

          {nodes.map((n) => {
            const pos = positions.get(n.id);
            if (!pos) return null;
            const isFocused = focusedNodeId === n.id;
            const isNeighbor = neighborSet.has(n.id);
            const isDimmed = !!focusedNodeId && !isFocused && !isNeighbor;
            const isSearchHit = !!searchLower && (n.canonical_value || n.label || "").toLowerCase().includes(searchLower);
            // if search active, dim non-hits
            const dimmedBySearch = !!searchLower && !isSearchHit;
            return (
              <NodeMesh
                key={n.id}
                node={n}
                pos={pos}
                isFocused={isFocused}
                isNeighbor={isNeighbor}
                isDimmed={isDimmed || dimmedBySearch}
                isSearchHit={isSearchHit}
                onSelect={(node) => onNodeSelect?.(node)}
              />
            );
          })}
        </group>

        <ContactShadows position={[0, -3.18, 0]} opacity={0.45} scale={30} blur={2.8} far={6} color="#020617" />
        <OrbitControls
          enableDamping
          dampingFactor={0.06}
          rotateSpeed={0.42}
          zoomSpeed={0.9}
          minDistance={6}
          maxDistance={42}
          maxPolarAngle={Math.PI / 2.15}
          target={[0, 0, 0]}
        />
        <AutoRotate enabled={autoRotate} />

        <EffectComposer multisampling={2} autoClear={false}>
          <Bloom intensity={0.42} luminanceThreshold={0.68} luminanceSmoothing={0.28} mipmapBlur />
          <Vignette eskil={false} offset={0.14} darkness={0.42} />
        </EffectComposer>
      </Canvas>

      {/* HUD overlay */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-3 p-3">
        <div className="pointer-events-auto flex items-center gap-2">
          <div className="rounded-neo-sm border border-white/10 bg-black/45 px-2.5 py-1.5 backdrop-blur-md">
            <p className="font-mono text-[10px] tracking-[0.14em] text-white/80">
              3D TOPOLOGY · <span className="text-cyan-300">{nodes.length} NODES</span> · <span className="text-amber-300">{edges.length} EDGES</span>
            </p>
            <p className="font-mono text-[9px] tracking-wide text-white/45">DRAG to orbit · SCROLL to zoom · CLICK node to focus</p>
          </div>
        </div>
        <button
          onClick={() => setAutoRotate((v) => !v)}
          className={cn(
            "pointer-events-auto rounded-neo-sm border px-2.5 py-1 text-[11px] font-semibold backdrop-blur-md transition-colors",
            autoRotate ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-200" : "border-white/10 bg-black/40 text-white/70 hover:bg-black/60"
          )}
        >
          {autoRotate ? "● Auto Orbit ON" : "○ Auto Orbit OFF"}
        </button>
      </div>

      {/* Legend */}
      <div className="pointer-events-none absolute bottom-3 left-3 rounded-neo-sm border border-white/10 bg-black/45 px-2.5 py-2 backdrop-blur-md">
        <p className="font-mono text-[9px] font-bold tracking-widest text-white/60">ENTITY TYPES</p>
        <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(ENTITY_COLOR).slice(0, 6).map(([k, col]) => (
            <span key={k} className="flex items-center gap-1.5 font-mono text-[10px] text-white/75">
              <span className="h-2 w-2 rounded-sm" style={{ background: col }} /> {k}
            </span>
          ))}
        </div>
      </div>

      {/* Hidden link indicator */}
      {edges.some((e) => e.edge_type === "hidden_link") && (
        <div className="pointer-events-none absolute bottom-3 right-3 rounded-neo-sm border border-amber-500/20 bg-amber-500/10 px-2.5 py-1.5 backdrop-blur-md">
          <p className="font-mono text-[10px] tracking-wide text-amber-200">⚡ Amber = AI Hidden Link (90%+ precision)</p>
        </div>
      )}
    </div>
  );
}
