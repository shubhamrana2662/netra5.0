import { entities as corpusEntities } from '../data/entities';
import { connections as corpusConnections } from '../data/connections';
import { GraphModel, GraphIntel } from '../screens/case/tabs/graphEngine';
import { buildSpatialScene } from '../screens/case/tabs/immersive/spatialSceneBuilder';
import { project3D } from '../screens/case/tabs/immersive/spatialCameraEngine';

console.log('=== DATA PIPELINE AUDIT ===');
console.log('1. corpusEntities count:', corpusEntities.length);
console.log('2. corpusConnections count:', corpusConnections.length);

const entityKindMap = new Map<string, string>();
corpusEntities.forEach(e => entityKindMap.set(e.id, e.kind));

const allModelNodes = GraphModel.allNodes(corpusEntities, true);
const allModelEdges = GraphModel.allEdges(corpusConnections, entityKindMap, true);

console.log('3. allModelNodes count:', allModelNodes.length);
console.log('4. allModelEdges count:', allModelEdges.length);

const analysis = GraphIntel.analyze(allModelNodes, allModelEdges);
console.log('5. analysis communities:', analysis.communities.length);

const scene = buildSpatialScene(allModelNodes, allModelEdges, analysis);
console.log('6. sceneNodes count:', scene.nodes.size);
console.log('7. sceneFilaments count:', scene.filaments.length);

const sampleNodes = Array.from(scene.nodes.values()).slice(0, 5);
console.log('8. Sample scene nodes:');
sampleNodes.forEach(n => {
  console.log(`   - ${n.id} (${n.name}): basePos=(${n.basePos.x}, ${n.basePos.y}, ${n.basePos.z}), layer=${n.depthLayer}`);
});

console.log('9. Computing 3D graph bounding box...');
let minX = Infinity, maxX = -Infinity;
let minY = Infinity, maxY = -Infinity;
let minZ = Infinity, maxZ = -Infinity;

for (const n of scene.nodes.values()) {
  if (n.basePos.x < minX) minX = n.basePos.x;
  if (n.basePos.x > maxX) maxX = n.basePos.x;
  if (n.basePos.y < minY) minY = n.basePos.y;
  if (n.basePos.y > maxY) maxY = n.basePos.y;
  if (n.basePos.z < minZ) minZ = n.basePos.z;
  if (n.basePos.z > maxZ) maxZ = n.basePos.z;
}

const cx = (minX + maxX) / 2;
const cy = (minY + maxY) / 2;
const cz = (minZ + maxZ) / 2;
const spanX = maxX - minX;
const spanY = maxY - minY;
const maxSpan = Math.max(spanX, spanY);
const suggestedCamZ = Math.round(cz + maxSpan * 0.9 + 180);

console.log(`   - Bounds X: [${minX}, ${maxX}], Y: [${minY}, ${maxY}], Z: [${minZ}, ${maxZ}]`);
console.log(`   - Center: (${cx.toFixed(1)}, ${cy.toFixed(1)}, ${cz.toFixed(1)})`);
console.log(`   - Suggested CamZ: ${suggestedCamZ}`);

const width = 1200;
const height = 800;
const autoCam = { x: cx, y: cy, z: suggestedCamZ, yaw: 0, pitch: 0 };
let autoInView = 0;
for (const n of scene.nodes.values()) {
  const p = project3D(n.currentPos, autoCam, width, height);
  if (p.inView) autoInView++;
}
console.log(`   - Nodes in view with autoCam: ${autoInView} / ${scene.nodes.size}`);

// Check filaments
console.log('10. Sample filaments:');
scene.filaments.slice(0, 5).forEach(f => {
  console.log(`   - ${f.id} (${f.sourceId} -> ${f.targetId}): wave=${f.waveIndex}, state=${f.state}, drawProgress=${f.drawProgress}, opacity=${f.opacity}`);
});
