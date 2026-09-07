import assert from "node:assert";
import { buildSpatialScene } from "../screens/case/tabs/immersive/spatialSceneBuilder";
import { project3D, createDustPool } from "../screens/case/tabs/immersive/spatialCameraEngine";
import { updateFilamentOrchestration } from "../screens/case/tabs/immersive/connectionOrchestrator";

console.log("▶ Verifying Immersive Living Spatial Network Engine...");

const mockNodes = [
  { id: "p1", name: "Rajesh Kumar", kind: "PERSON", risk: "HIGH", bridgeScore: 0.85 },
  { id: "d1", name: "Hardware IMEI 29", kind: "DEVICE", risk: "NORMAL", bridgeScore: 0.70 },
  { id: "a1", name: "Axis Bank ••4821", kind: "ACCOUNT", risk: "HIGH", bridgeScore: 0.20 },
  { id: "a2", name: "HDFC ••7200", kind: "ACCOUNT", risk: "NORMAL", bridgeScore: 0.0 },
  { id: "ip1", name: "Relay 103.21.x", kind: "IP", risk: "NORMAL", bridgeScore: 0.0, latent: true },
];

const mockEdges = [
  { id: "e1", a: "p1", b: "d1", type: "uses", conf: 90, directed: 1 },
  { id: "e2", a: "d1", b: "a1", type: "operates", conf: 85, directed: 1 },
  { id: "e3", a: "a1", b: "a2", type: "transfers", conf: 95, directed: 1 },
];

const mockAnalysis = {
  deg: { p1: 1, d1: 2, a1: 2, a2: 1, ip1: 0 },
  pr: {},
  prn: () => 0.5,
  bet: null,
  commOf: { p1: 0, d1: 0, a1: 1, a2: 1, ip1: 1 },
  communities: [
    { id: "p1", size: 2, rep: "d1", members: ["p1", "d1"] },
    { id: "a1", size: 3, rep: "a1", members: ["a1", "a2", "ip1"] },
  ],
  bridges: ["p1", "d1"],
  bridgeScores: { p1: 0.85, d1: 0.70, a1: 0.20, a2: 0.0, ip1: 0.0 },
  mostConnected: "d1",
  topPr: "d1",
  riskCount: 2,
};

// 1. Verify Spatial Scene Layout & Broad Viewport Distribution
const { nodes, filaments, clusterCentroids } = buildSpatialScene(mockNodes, mockEdges, mockAnalysis);

assert.strictEqual(nodes.size, mockNodes.length, "All nodes must be mapped into the spatial scene");
assert.strictEqual(filaments.length, mockEdges.length, "All filaments must be initialized");
assert(clusterCentroids.size >= 2, "Must establish wide territorial community centroids");

// Verify wide community territorial separation
const c0 = clusterCentroids.get(0);
const c1 = clusterCentroids.get(1);
const clusterDist = Math.hypot(c0.x - c1.x, c0.y - c1.y, c0.z - c1.z);
assert(clusterDist > 280, `Clusters must be broadly distributed across viewport (found ${clusterDist.toFixed(1)}px)`);
console.log(`  ✓ Wide community territorial distribution verified: ${clusterDist.toFixed(1)}px distance`);

// Verify depth stratification: Bridge and high risk in foreground, latent in background
const bridgeNode = nodes.get("p1");
const latentNode = nodes.get("ip1");
assert(bridgeNode.basePos.z > latentNode.basePos.z, "Bridge broker must have higher Z than latent node");
console.log(`  ✓ 3D Depth stratification verified: Bridge broker z=${bridgeNode.basePos.z} vs Latent z=${latentNode.basePos.z}`);

// 2. Verify 3D Perspective Projection Matching Landing Page
const camera = { x: 0, y: -10, z: 460, yaw: 0, pitch: 0 };
const projFore = project3D({ x: 0, y: 0, z: 120 }, camera, 1000, 600);
const projBack = project3D({ x: 0, y: 0, z: -120 }, camera, 1000, 600);

assert(projFore.scale > projBack.scale, "Foreground point must have larger scale");
assert(projFore.depthAlpha > projBack.depthAlpha, "Foreground point must have higher depth alpha");
console.log(`  ✓ Perspective projection verified: Foreground scale=${projFore.scale.toFixed(2)}, alpha=${projFore.depthAlpha.toFixed(2)} vs Deep background scale=${projBack.scale.toFixed(2)}, alpha=${projBack.depthAlpha.toFixed(2)}`);

// 3. Verify Connection Formation & Guaranteed Immediate Visibility
// Filaments must be visibly drawn from frame 1
updateFilamentOrchestration(filaments, nodes, {
  time: 0,
  selectedNodeId: null,
  showAiLinks: false,
  activePath: [],
  pathStep: 0
});
assert(filaments[0].drawProgress >= 0.60, "Filaments must be visibly drawn immediately (no zero-opacity delay)");
assert(filaments[0].state === "connecting" || filaments[0].state === "stable", "Filaments must be active");
console.log(`  ✓ Guaranteed immediate connection visibility verified: drawProgress = ${(filaments[0].drawProgress * 100).toFixed(1)}%`);

// At t=1.4s, full draw progress reached
updateFilamentOrchestration(filaments, nodes, {
  time: 1400,
  selectedNodeId: null,
  showAiLinks: false,
  activePath: [],
  pathStep: 0
});
const w1Filament = filaments.find(f => f.waveIndex === 1);
if (w1Filament) {
  assert.strictEqual(w1Filament.drawProgress, 1.0, "Filament must reach 100% draw progress");
  console.log(`  ✓ Progressive connection drawing verified: Wave 1 drawProgress = 100%`);
}

// At t=5.0s, living network is stabilized
updateFilamentOrchestration(filaments, nodes, {
  time: 5000,
  selectedNodeId: null,
  showAiLinks: false,
  activePath: [],
  pathStep: 0
});
assert(filaments[0].drawProgress >= 0.99, "Filaments must be fully drawn in living network state");
console.log("  ✓ Living network state stabilization verified");

// 4. Verify Selection Focus & Isolation
updateFilamentOrchestration(filaments, nodes, {
  time: 5000,
  selectedNodeId: "p1",
  showAiLinks: false,
  activePath: [],
  pathStep: 0
});
const directEdge = filaments.find(f => f.sourceId === "p1" || f.targetId === "p1");
const distantEdge = filaments.find(f => f.sourceId === "a1" && f.targetId === "a2");
assert.strictEqual(directEdge.state, "focused", "Direct edge must be focused");
assert.strictEqual(distantEdge.state, "dormant", "Unrelated edge must be dimmed to dormant state");
console.log("  ✓ Selection focus and neighborhood isolation verified");

// 5. Verify Dust Pool Generation
const dust = createDustPool(40);
assert.strictEqual(dust.length, 40, "Dust pool must have requested count");
console.log("  ✓ Ambient 3D dust particle pool verified");

console.log("✅ ALL IMMERSIVE LIVING SPATIAL NETWORK ENGINE VERIFICATIONS PASSED!");
