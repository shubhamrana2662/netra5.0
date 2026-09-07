import assert from 'node:assert';
import { graphInteractionStore } from '../screens/case/tabs/graphCore/GraphInteractionStore';
import { GraphAlgorithmService } from '../screens/case/tabs/graphCore/GraphAlgorithmService';

console.log('▶ Verifying Graph Core Shared Interaction Store and Algorithms...');

const mockNodes = [
  { id: 'p1', name: 'Rajesh Kumar', kind: 'PERSON', risk: 'HIGH' },
  { id: 'd1', name: 'Hardware IMEI 29', kind: 'DEVICE', risk: 'NORMAL' },
  { id: 'u1', name: 'mule.pay@upi', kind: 'UPI', risk: 'NORMAL' },
  { id: 'a1', name: 'Axis Bank ••4821', kind: 'ACCOUNT', risk: 'HIGH' },
  { id: 'a2', name: 'HDFC ••7200', kind: 'ACCOUNT', risk: 'NORMAL' },
];

const mockEdges = [
  { id: 'e1', a: 'p1', b: 'd1', type: 'uses', conf: 90, directed: 1 },
  { id: 'e2', a: 'd1', b: 'u1', type: 'operates', conf: 85, directed: 1 },
  { id: 'e3', a: 'u1', b: 'a1', type: 'transfers', conf: 95, directed: 1 },
  { id: 'e4', a: 'a1', b: 'a2', type: 'settles', conf: 75, directed: 1 },
];

// 1. Verify Selection State & Mutual Synchronization
graphInteractionStore.clearSelection();
assert.strictEqual(graphInteractionStore.getState().selectedNodeIds.size, 0);

graphInteractionStore.selectNode('p1');
assert.strictEqual(graphInteractionStore.getState().selectedNodeIds.size, 1);
assert(graphInteractionStore.getState().selectedNodeIds.has('p1'));
assert.strictEqual(graphInteractionStore.getState().focusedNodeId, 'p1');
console.log('  ✓ Single node selection and focus verified');

// Multi-selection
graphInteractionStore.selectNode('a1', true);
assert.strictEqual(graphInteractionStore.getState().selectedNodeIds.size, 2);
assert(graphInteractionStore.getState().selectedNodeIds.has('p1'));
assert(graphInteractionStore.getState().selectedNodeIds.has('a1'));
console.log('  ✓ Multi-node selection (Cmd/Ctrl + click) verified');

// 2. Verify View Switching Preserves Context
graphInteractionStore.setViewMode('IMMERSIVE');
assert.strictEqual(graphInteractionStore.getState().viewMode, 'IMMERSIVE');
assert(graphInteractionStore.getState().selectedNodeIds.has('p1'), 'Selected entity must persist when entering 3D');

graphInteractionStore.setViewMode('GRAPH');
assert.strictEqual(graphInteractionStore.getState().viewMode, 'GRAPH');
assert(graphInteractionStore.getState().selectedNodeIds.has('p1'), 'Selected entity must persist when returning to 2D');
console.log('  ✓ 2D <-> 3D Cross-view selection persistence verified');

// 3. Verify Neighborhood Discovery (1-hop and 2-hop)
const oneHop = GraphAlgorithmService.getNeighborhood('d1', 1, mockEdges);
assert(oneHop.has('p1') && oneHop.has('u1') && !oneHop.has('a1'), '1-hop must only contain direct neighbors');
console.log('  ✓ 1-Hop neighborhood extraction verified (p1, u1)');

const twoHop = GraphAlgorithmService.getNeighborhood('d1', 2, mockEdges);
assert(twoHop.has('a1') && !twoHop.has('a2'), '2-hop must expand to secondary connections');
console.log('  ✓ 2-Hop neighborhood extraction verified (reaches a1)');

// 4. Verify Interactive Path Finding
const pathResult = GraphAlgorithmService.findConnectionPath('p1', 'a2', mockEdges);
assert(pathResult !== null, 'Path must be found between p1 and a2');
assert.deepStrictEqual(pathResult.nodes, ['p1', 'd1', 'u1', 'a1', 'a2']);
assert.strictEqual(pathResult.minConfidence, 75, 'Bottleneck confidence must be 75%');
console.log(`  ✓ Widest path algorithm verified: ${pathResult.pathDescription}`);

// 5. Verify All 4 Layout Engines
const layouts = ['force', 'radial', 'hierarchical', 'clustered'];
layouts.forEach(mode => {
  const positions = GraphAlgorithmService.computeLayout(mode, mockNodes, mockEdges);
  assert.strictEqual(Object.keys(positions).length, mockNodes.length, `${mode} layout must position all nodes`);
  console.log(`  ✓ ${mode.toUpperCase()} layout algorithm verified`);
});

console.log('✅ ALL GRAPH CORE STORE & ALGORITHM TESTS PASSED SUCCESSFULLY!');
