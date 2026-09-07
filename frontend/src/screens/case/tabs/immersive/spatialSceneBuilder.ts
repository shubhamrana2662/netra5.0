import { ModelNode, ModelEdge, IntelAnalysis } from '../graphEngine';
import { SpatialNode, SpatialFilament, Point3D } from './spatial3DTypes';

function seededRng(seed: number) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

export interface SpatialScene {
  nodes: Map<string, SpatialNode>;
  filaments: SpatialFilament[];
  clusterCentroids: Map<number, Point3D>;
}

export function buildSpatialScene(
  nodes: ModelNode[],
  edges: ModelEdge[],
  analysis: IntelAnalysis | null
): SpatialScene {
  const commOf = analysis?.commOf || {};
  const bridgeScores = analysis?.bridgeScores || {};
  const deg = analysis?.deg || {};

  // 1. Establish wide territorial regions for graph communities
  const communities = analysis?.communities || [
    { id: 'c0', size: nodes.length, rep: nodes[0]?.id || '', members: nodes.map(n => n.id) }
  ];

  const clusterCentroids = new Map<number, Point3D>();
  const numComms = Math.max(1, communities.length);

  // Broad spatial distribution filling safe viewing volume
  const territoryConfigs: Point3D[] = [
    { x: -180, y: -25,  z: 35 },  // Community 0: Western quadrant
    { x: 175,  y: 40,   z: -20 }, // Community 1: Eastern financial funnel
    { x: -25,  y: -145, z: 60 },  // Community 2: Northern infrastructure
    { x: 225,  y: -95,  z: 30 },  // Community 3: North-east exfiltration
    { x: -145, y: 120,  z: 15 },  // Community 4: South-west telemetry
    { x: 55,   y: 135,  z: -40 }  // Community 5: Southern peripheral
  ];

  communities.forEach((_, ci) => {
    if (ci < territoryConfigs.length) {
      clusterCentroids.set(ci, { ...territoryConfigs[ci] });
    } else {
      const angle = (ci / numComms) * Math.PI * 2;
      clusterCentroids.set(ci, {
        x: Math.cos(angle) * 240,
        y: Math.sin(angle) * 150,
        z: Math.sin(ci * 1.7) * 55
      });
    }
  });

  const nodeMap = new Map<string, SpatialNode>();

  // 2. Position nodes within their community territories with intentional depth stratification
  nodes.forEach((n, idx) => {
    const ci = commOf[n.id] ?? 0;
    const centroid = clusterCentroids.get(ci) || { x: 0, y: 0, z: 0 };
    const bridge = bridgeScores[n.id] ?? (n.bridgeScore ?? 0);
    const degree = deg[n.id] ?? 1;
    const isHighRisk = n.risk === 'HIGH';

    // Unique deterministic seed
    let hash = idx * 1337;
    for (let i = 0; i < n.id.length; i++) hash = (hash * 31 + n.id.charCodeAt(i)) & 0xffffff;
    const rnd = seededRng(hash);

    const localAngle = rnd() * Math.PI * 2;
    // Core hubs stay near centroid; outer nodes disperse into territory
    const spreadDist = 28 + (1.0 - Math.min(1.0, degree / 6)) * 85 + rnd() * 25;

    let localX = Math.cos(localAngle) * spreadDist;
    let localY = Math.sin(localAngle) * (spreadDist * 0.72);

    let depthLayer: 'foreground' | 'midground' | 'background' = 'midground';
    let baseZ = centroid.z;

    if (bridge > 0.35 || isHighRisk) {
      depthLayer = 'foreground';
      baseZ += 45 + rnd() * 40; // Foreground elevation
    } else if (n.latent || degree <= 1) {
      depthLayer = 'background';
      baseZ -= 60 + rnd() * 35; // Deep background receded
    } else {
      depthLayer = 'midground';
      baseZ += (rnd() - 0.5) * 40;
    }

    let finalX = centroid.x + localX;
    let finalY = centroid.y + localY;

    // Bridge entities pulled toward the central corridor between clusters
    if (bridge > 0.3) {
      const pull = Math.min(0.65, bridge * 0.7);
      finalX = finalX * (1 - pull);
      finalY = finalY * (1 - pull) * 0.7;
      baseZ = Math.max(baseZ, 50);
    }

    const pos: Point3D = {
      x: Math.round(finalX),
      y: Math.round(finalY),
      z: Math.round(baseZ)
    };

    nodeMap.set(n.id, {
      id: n.id,
      name: n.name,
      kind: n.kind,
      risk: n.risk,
      cluster: ci,
      isBridge: bridge > 0.35,
      degree,
      harmonicPhase: rnd() * Math.PI * 2,
      depthLayer,
      basePos: pos,
      currentPos: { ...pos },
      scale: depthLayer === 'foreground' ? 1.25 : depthLayer === 'background' ? 0.82 : 1.0,
      opacity: 1.0,
      pingRadius: 8,
      pingAlpha: 0.6
    });
  });

  // 3. Center the entire graph strictly around origin (0, 0, 0)
  let sumX = 0, sumY = 0, sumZ = 0;
  nodeMap.forEach(node => {
    sumX += node.basePos.x;
    sumY += node.basePos.y;
    sumZ += node.basePos.z;
  });
  const avgX = Math.round(sumX / Math.max(1, nodeMap.size));
  const avgY = Math.round(sumY / Math.max(1, nodeMap.size));
  const avgZ = Math.round(sumZ / Math.max(1, nodeMap.size));

  nodeMap.forEach(node => {
    node.basePos.x -= avgX;
    node.basePos.y -= avgY;
    node.basePos.z -= avgZ;
    node.currentPos = { ...node.basePos };
  });

  clusterCentroids.forEach(c => {
    c.x -= avgX;
    c.y -= avgY;
    c.z -= avgZ;
  });

  // 4. Create filaments with wave index and guaranteed initial visibility
  const filaments: SpatialFilament[] = edges.map((e, idx) => {
    const isHidden = !!e.is_hidden || e.type === 'hidden_link';
    const nA = nodeMap.get(e.a);
    const nB = nodeMap.get(e.b);
    const isCrossCluster = nA && nB && nA.cluster !== nB.cluster;

    let waveIndex = 2; // Default cluster internal
    if (isHidden) {
      waveIndex = 4; // Inferred links appear in discovery phase
    } else if ((nA?.isBridge || nB?.isBridge) || isCrossCluster) {
      waveIndex = 3; // Cross-cluster bridge wave
    } else if ((e.conf >= 85 || (nA && nA.degree >= 3 && nB && nB.degree >= 3)) && idx < 6) {
      waveIndex = 1; // Primary initial correlation wave
    }

    return {
      id: e.id,
      sourceId: e.a,
      targetId: e.b,
      type: isHidden ? 'hidden_link' : e.type,
      conf: e.conf,
      is_hidden: isHidden,
      directed: e.directed,
      waveIndex,
      state: 'stable',
      drawProgress: 1.0,
      opacity: 0.85,
      lineWidth: isHidden ? 1.8 : 1.3,
      isSuspectPath: false
    };
  });

  return { nodes: nodeMap, filaments, clusterCentroids };
}
