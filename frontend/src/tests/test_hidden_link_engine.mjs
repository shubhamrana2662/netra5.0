import assert from "node:assert";
import { GraphIntel } from "../screens/case/tabs/graphEngine";

console.log("▶ Verifying Hidden Link Engine Audit & Algorithm Implementation...");

const mockNodes = [
  { id: "u1", name: "Rajesh Kumar", kind: "PERSON" },
  { id: "u2", name: "Device A83F-29", kind: "DEVICE" },
  { id: "u3", name: "Axis Bank ••4821", kind: "ACCOUNT" },
  { id: "u4", name: "Beneficiary #72", kind: "ACCOUNT" },
  { id: "u5", name: "Mule Operator B", kind: "PERSON" },
];

const mockEdges = [
  { id: "e1", a: "u1", b: "u2", type: "uses_device", conf: 90, directed: 1 },
  { id: "e2", a: "u2", b: "u3", type: "associated_with", conf: 85, directed: 0 },
  { id: "e3", a: "u3", b: "u4", type: "transacts_to", conf: 95, directed: 1 },
  { id: "e4", a: "u5", b: "u4", type: "holds", conf: 80, directed: 1 },
];

const analysis = {
  deg: { u1: 1, u2: 2, u3: 2, u4: 2, u5: 1 },
  pr: {},
  prn: () => 0.5,
  bet: null,
  commOf: { u1: 0, u2: 0, u3: 1, u4: 1, u5: 1 },
  communities: [
    { id: "u1", size: 2, rep: "u2", members: ["u1", "u2"] },
    { id: "u3", size: 3, rep: "u3", members: ["u3", "u4", "u5"] },
  ],
  bridges: ["u2", "u3"],
  bridgeScores: { u1: 0, u2: 0.5, u3: 0.5, u4: 0, u5: 0 },
  mostConnected: "u2",
  topPr: "u3",
  riskCount: 1,
};

const inferred = GraphIntel.predictHiddenLinks(mockNodes, mockEdges, analysis, 0.20);
assert(Array.isArray(inferred), "Must return an array of inferred links");
assert(inferred.length > 0, "Must infer at least 1 hidden link candidate");

// 1. Audit Check: Zero self-relationships
for (const link of inferred) {
  assert.notStrictEqual(link.sourceId, link.targetId, `Self-link found: ${link.id}`);
}
console.log("  ✓ Audit passed: Zero self-relationships");

// 2. Audit Check: Zero existing edges re-inferred
const existingPairs = new Set(mockEdges.map(e => `${e.a}::${e.b}`));
mockEdges.forEach(e => existingPairs.add(`${e.b}::${e.a}`));

for (const link of inferred) {
  const pair1 = `${link.sourceId}::${link.targetId}`;
  const pair2 = `${link.targetId}::${link.sourceId}`;
  assert(!existingPairs.has(pair1) && !existingPairs.has(pair2), `Existing edge re-inferred: ${pair1}`);
}
console.log("  ✓ Audit passed: Zero existing evidence edges re-inferred");

// 3. Audit Check: Zero reverse duplicates (u -> v and v -> u)
const seenPairs = new Set();
for (const link of inferred) {
  const key1 = `${link.sourceId}::${link.targetId}`;
  const key2 = `${link.targetId}::${link.sourceId}`;
  assert(!seenPairs.has(key1) && !seenPairs.has(key2), `Duplicate pair generated: ${key1}`);
  seenPairs.add(key1);
}
console.log(`  ✓ Audit passed: Zero duplicate pairs among ${inferred.length} candidate inferences`);

// 4. Audit Check: Explainability reasoning present
for (const link of inferred) {
  assert(link.confidence >= 45 && link.confidence <= 96, "Confidence must be within 45-96%");
  assert(Array.isArray(link.reasons), "Must include explainability reasons");
  assert(link.reasons.length > 0, `Link ${link.id} must have at least one explanation`);
  assert(link.status === "candidate", "Status must be candidate");
}
console.log("  ✓ Audit passed: All inferences have transparent explainability reports and feature contributions");

console.log("✅ HIDDEN LINK ENGINE AUDIT & INFERENCE CORE PASSED PERFECTLY!");
