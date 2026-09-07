import assert from "node:assert";
import {
  computeSpatialAnchors,
  computeBasePositions,
} from "../screens/case/tabs/graphEngine";

console.log("▶ Verifying Graph Engine Spatial Visual Redesign...");

// Mock nodes and edges matching CyberDrishti operational data
const mockNodes = [
  { id: "ent-person-04", kind: "PERSON", risk: "HIGH", bridgeScore: 0.82 },
  { id: "ent-device-29", kind: "DEVICE", risk: "NORMAL", bridgeScore: 0.65 },
  { id: "ent-account-4821", kind: "ACCOUNT", risk: "HIGH", bridgeScore: 0.40 },
  { id: "ent-account-72", kind: "ACCOUNT", risk: "NORMAL", bridgeScore: 0.15 },
  { id: "ent-upi-01", kind: "UPI", risk: "NORMAL", bridgeScore: 0.10 },
  { id: "ent-ip-01", kind: "IP", risk: "NORMAL", bridgeScore: 0.05 },
];

const mockEdges = [
  { a: "ent-person-04", b: "ent-device-29" },
  { a: "ent-device-29", b: "ent-account-4821" },
  { a: "ent-account-4821", b: "ent-account-72" },
  { a: "ent-upi-01", b: "ent-account-4821" },
  { a: "ent-ip-01", b: "ent-device-29" },
];

// 1. Verify Spatial Anchors computation
const anchors = computeSpatialAnchors(mockNodes, mockEdges);
assert(anchors, "Anchors must be generated");
assert.strictEqual(Object.keys(anchors).length, mockNodes.length, "All nodes must have spatial anchors");

// 2. Verify 2.5D Depth hierarchy
const bridgeAnchor = anchors["ent-person-04"];
const peripheralAnchor = anchors["ent-ip-01"];

assert(bridgeAnchor.depth.z > 0, "High bridge/risk entity must have foreground anchor (z > 0)");
assert(bridgeAnchor.depth.depthScale > 1.0, "Foreground entity must have scaled up presence (depthScale > 1.0)");
assert(bridgeAnchor.depth.depthOpacity >= 0.75, "Foreground entity must have high opacity");

assert(peripheralAnchor.depth.z < 0, "Peripheral node must reside in deeper space (z < 0)");
assert(peripheralAnchor.depth.depthScale < 1.0, "Peripheral node must have reduced scale");
console.log(`  ✓ 2.5D Depth hierarchy verified: Bridge z=${bridgeAnchor.depth.z.toFixed(1)} (scale=${bridgeAnchor.depth.depthScale.toFixed(2)}) vs Peripheral z=${peripheralAnchor.depth.z.toFixed(1)} (scale=${peripheralAnchor.depth.depthScale.toFixed(2)})`);

// 3. Verify Deterministic Ambient Drift Parameters
for (const [id, anc] of Object.entries(anchors)) {
  assert(anc.driftAmplitude >= 2.0 && anc.driftAmplitude <= 6.5, `Drift amplitude for ${id} must be between 2-6.5px`);
  assert(anc.driftSpeed > 0 && anc.driftSpeed < 0.001, `Drift speed for ${id} must be slow and calm`);
  assert(typeof anc.driftPhase === "number", `Drift phase for ${id} must be a number`);
}
console.log("  ✓ Deterministic subtle ambient drift parameters verified across all nodes");

// 4. Verify Determinism: Two identical calls produce identical spatial anchors
const anchors2 = computeSpatialAnchors(mockNodes, mockEdges);
for (const id of Object.keys(anchors)) {
  assert.strictEqual(anchors[id].baseX, anchors2[id].baseX, "baseX must be deterministic");
  assert.strictEqual(anchors[id].baseY, anchors2[id].baseY, "baseY must be deterministic");
  assert.strictEqual(anchors[id].depth.z, anchors2[id].depth.z, "depth.z must be deterministic");
}
console.log("  ✓ Spatial composition determinism verified (identical seeds produce identical layouts)");

console.log("✅ ALL GRAPH ENGINE SPATIAL REDESIGN SPECIFICATIONS VERIFIED SUCCESSFULLY!");
