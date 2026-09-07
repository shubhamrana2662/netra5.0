import { ModelNode, ModelEdge } from '../graphEngine';
import { LayoutMode, PathFindingResult } from './graphInteractionTypes';

export class GraphAlgorithmService {
  /**
   * 1. Force-Directed Layout (Fruchterman-Reingold)
   * Ported from graph_engine/frontend/react_components/GraphPage.tsx
   */
  static forceDirectedLayout(
    nodes: ModelNode[],
    edges: ModelEdge[],
    width = 1100,
    height = 700
  ): Record<string, { x: number; y: number }> {
    const N = nodes.length;
    const pos: Record<string, { x: number; y: number }> = {};
    if (N === 0) return pos;

    const area = width * height;
    const k = Math.sqrt(area / Math.max(1, N)) * 0.85;
    const iterations = 75;
    const cooling = 0.96;
    let temp = width / 4;

    const positions = nodes.map((_, i) => ({
      x: width / 2 + (Math.sin(i * 1.3) * 0.45 + (Math.random() - 0.5) * 0.2) * width * 0.7,
      y: height / 2 + (Math.cos(i * 1.3) * 0.45 + (Math.random() - 0.5) * 0.2) * height * 0.7,
    }));

    const nodeIdxMap = new Map<string, number>();
    nodes.forEach((n, i) => nodeIdxMap.set(n.id, i));

    for (let iter = 0; iter < iterations; iter++) {
      const disp = positions.map(() => ({ x: 0, y: 0 }));

      // Repulsive forces
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const dx = positions[i].x - positions[j].x;
          const dy = positions[i].y - positions[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
          const force = (k * k) / dist;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          disp[i].x += fx;
          disp[i].y += fy;
          disp[j].x -= fx;
          disp[j].y -= fy;
        }
      }

      // Attractive forces along edges
      for (const e of edges) {
        const si = nodeIdxMap.get(e.a);
        const ti = nodeIdxMap.get(e.b);
        if (si === undefined || ti === undefined) continue;
        const dx = positions[si].x - positions[ti].x;
        const dy = positions[si].y - positions[ti].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const force = (dist * dist) / k;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        disp[si].x -= fx;
        disp[si].y -= fy;
        disp[ti].x += fx;
        disp[ti].y += fy;
      }

      // Displacements
      for (let i = 0; i < N; i++) {
        const dist = Math.sqrt(disp[i].x * disp[i].x + disp[i].y * disp[i].y) || 0.01;
        const scale = Math.min(dist, temp) / dist;
        positions[i].x += disp[i].x * scale;
        positions[i].y += disp[i].y * scale;
        positions[i].x = Math.max(70, Math.min(width - 70, positions[i].x));
        positions[i].y = Math.max(70, Math.min(height - 70, positions[i].y));
      }
      temp *= cooling;
    }

    nodes.forEach((n, i) => {
      pos[n.id] = { x: Math.round(positions[i].x), y: Math.round(positions[i].y) };
    });
    return pos;
  }

  /**
   * 2. Radial Layout
   * Places high-degree hubs at center with concentric rings outward
   */
  static radialLayout(
    nodes: ModelNode[],
    edges: ModelEdge[],
    width = 1100,
    height = 700
  ): Record<string, { x: number; y: number }> {
    const cx = width / 2;
    const cy = height / 2;
    const pos: Record<string, { x: number; y: number }> = {};
    const degreeMap = new Map<string, number>();
    nodes.forEach(n => degreeMap.set(n.id, 0));
    edges.forEach(e => {
      degreeMap.set(e.a, (degreeMap.get(e.a) || 0) + 1);
      degreeMap.set(e.b, (degreeMap.get(e.b) || 0) + 1);
    });

    const sorted = [...nodes].sort((a, b) => (degreeMap.get(b.id) || 0) - (degreeMap.get(a.id) || 0));
    const ringCapacities = [1, 6, 12, 18, 26, 40, 60];
    let nodeIdx = 0;
    let ringIdx = 0;

    while (nodeIdx < sorted.length) {
      const cap = ringCapacities[Math.min(ringIdx, ringCapacities.length - 1)];
      const radius = ringIdx === 0 ? 0 : 95 + ringIdx * 85;
      const countInRing = Math.min(cap, sorted.length - nodeIdx);
      for (let i = 0; i < countInRing; i++) {
        const angle = (i / countInRing) * 2 * Math.PI - Math.PI / 2;
        const node = sorted[nodeIdx];
        pos[node.id] = {
          x: Math.round(cx + Math.cos(angle) * radius),
          y: Math.round(cy + Math.sin(angle) * (radius * 0.75)),
        };
        nodeIdx++;
      }
      ringIdx++;
    }
    return pos;
  }

  /**
   * 3. Hierarchical Layout (Top-down flow via BFS DAG)
   */
  static hierarchicalLayout(
    nodes: ModelNode[],
    edges: ModelEdge[],
    width = 1100,
    height = 700
  ): Record<string, { x: number; y: number }> {
    const pos: Record<string, { x: number; y: number }> = {};
    const adj = new Map<string, string[]>();
    const inDeg = new Map<string, number>();
    nodes.forEach(n => { adj.set(n.id, []); inDeg.set(n.id, 0); });
    edges.forEach(e => {
      adj.get(e.a)?.push(e.b);
      inDeg.set(e.b, (inDeg.get(e.b) || 0) + 1);
    });

    let roots = nodes.filter(n => (inDeg.get(n.id) || 0) === 0).map(n => n.id);
    if (roots.length === 0 && nodes.length > 0) roots = [nodes[0].id];

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

    nodes.forEach(n => {
      if (!visited.has(n.id)) levels.push([n.id]);
    });

    const levelHeight = height / Math.max(1, levels.length + 1);
    levels.forEach((level, li) => {
      const levelWidth = width / (level.length + 1);
      level.forEach((nid, ni) => {
        pos[nid] = {
          x: Math.round(levelWidth * (ni + 1)),
          y: Math.round(levelHeight * (li + 0.6))
        };
      });
    });

    return pos;
  }

  /**
   * 4. Clustered Layout (Grouped by entity kind/type)
   */
  static clusteredLayout(
    nodes: ModelNode[],
    _edges: ModelEdge[],
    width = 1100,
    height = 700
  ): Record<string, { x: number; y: number }> {
    const pos: Record<string, { x: number; y: number }> = {};
    const groups = new Map<string, ModelNode[]>();
    nodes.forEach(n => {
      const k = n.kind || 'OTHER';
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k)!.push(n);
    });

    const types = [...groups.keys()];
    const cols = Math.ceil(Math.sqrt(types.length));
    const rows = Math.ceil(types.length / cols);
    const cellW = width / cols;
    const cellH = height / rows;

    types.forEach((type, gi) => {
      const col = gi % cols;
      const row = Math.floor(gi / cols);
      const cx = cellW * col + cellW / 2;
      const cy = cellH * row + cellH / 2;
      const items = groups.get(type)!;
      const clusterRadius = Math.min(cellW, cellH) * 0.35;

      items.forEach((n, ni) => {
        if (items.length === 1) {
          pos[n.id] = { x: Math.round(cx), y: Math.round(cy) };
        } else {
          const angle = (ni / items.length) * 2 * Math.PI - Math.PI / 2;
          const r = clusterRadius * Math.sqrt((ni + 1) / items.length);
          pos[n.id] = {
            x: Math.round(cx + Math.cos(angle) * r),
            y: Math.round(cy + Math.sin(angle) * r)
          };
        }
      });
    });

    return pos;
  }

  /**
   * Master layout computation
   */
  static computeLayout(
    mode: LayoutMode,
    nodes: ModelNode[],
    edges: ModelEdge[],
    width = 1100,
    height = 700
  ): Record<string, { x: number; y: number }> {
    switch (mode) {
      case 'radial': return this.radialLayout(nodes, edges, width, height);
      case 'hierarchical': return this.hierarchicalLayout(nodes, edges, width, height);
      case 'clustered': return this.clusteredLayout(nodes, edges, width, height);
      case 'force':
      default:
        return this.forceDirectedLayout(nodes, edges, width, height);
    }
  }

  /**
   * Interactive Path Finding: Widest Path (Maximizes minimum bottleneck confidence)
   */
  static findConnectionPath(
    sourceId: string,
    targetId: string,
    edges: ModelEdge[]
  ): PathFindingResult | null {
    if (sourceId === targetId) {
      return {
        nodes: [sourceId],
        edges: [],
        minConfidence: 100,
        hopCount: 0,
        pathDescription: 'Identity path'
      };
    }

    const adj = new Map<string, Array<{ to: string; edgeId: string; conf: number }>>();
    edges.forEach(e => {
      if (!adj.has(e.a)) adj.set(e.a, []);
      if (!adj.has(e.b)) adj.set(e.b, []);
      adj.get(e.a)!.push({ to: e.b, edgeId: e.id, conf: e.conf });
      adj.get(e.b)!.push({ to: e.a, edgeId: e.id, conf: e.conf });
    });

    // Dijkstra variant for widest path (maximum bottleneck capacity)
    const bestCap = new Map<string, number>();
    const prevNode = new Map<string, string>();
    const prevEdge = new Map<string, string>();
    const pq: Array<{ id: string; cap: number }> = [{ id: sourceId, cap: Infinity }];
    bestCap.set(sourceId, Infinity);

    while (pq.length > 0) {
      pq.sort((a, b) => b.cap - a.cap);
      const curr = pq.shift()!;

      if (curr.id === targetId) break;
      if (curr.cap < (bestCap.get(curr.id) || 0)) continue;

      const neighbors = adj.get(curr.id) || [];
      for (const nbr of neighbors) {
        const pathCap = Math.min(curr.cap, nbr.conf);
        if (pathCap > (bestCap.get(nbr.to) || -1)) {
          bestCap.set(nbr.to, pathCap);
          prevNode.set(nbr.to, curr.id);
          prevEdge.set(nbr.to, nbr.edgeId);
          pq.push({ id: nbr.to, cap: pathCap });
        }
      }
    }

    if (!prevNode.has(targetId)) return null;

    // Backtrack path
    const pathNodes: string[] = [targetId];
    const pathEdges: string[] = [];
    let cur = targetId;
    while (cur !== sourceId) {
      const p = prevNode.get(cur)!;
      const e = prevEdge.get(cur)!;
      pathNodes.unshift(p);
      pathEdges.unshift(e);
      cur = p;
    }

    const minConf = bestCap.get(targetId) || 0;
    return {
      nodes: pathNodes,
      edges: pathEdges,
      minConfidence: Math.round(minConf),
      hopCount: pathEdges.length,
      pathDescription: `${pathNodes.length} nodes · ${pathEdges.length} hops · min confidence ${Math.round(minConf)}%`
    };
  }

  /**
   * K-hop neighborhood discovery (1-hop, 2-hop)
   */
  static getNeighborhood(centerId: string, hops: number, edges: ModelEdge[]): Set<string> {
    const result = new Set<string>([centerId]);
    let frontier = [centerId];

    for (let h = 0; h < hops; h++) {
      const nextFrontier: string[] = [];
      for (const cur of frontier) {
        edges.forEach(e => {
          if (e.a === cur && !result.has(e.b)) {
            result.add(e.b);
            nextFrontier.push(e.b);
          }
          if (e.b === cur && !result.has(e.a)) {
            result.add(e.a);
            nextFrontier.push(e.a);
          }
        });
      }
      frontier = nextFrontier;
    }

    return result;
  }
}
