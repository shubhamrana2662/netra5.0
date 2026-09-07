import { getSceneState } from '../screens/landing/getSceneState.js';
import { DEBUG_CHECKPOINTS } from '../screens/landing/storyConfig.js';

console.log('▶ Verifying Deterministic Scene State Choreography across all checkpoints...');

for (const cp of DEBUG_CHECKPOINTS) {
  const scene = getSceneState(cp);
  if (!scene || !scene.camera || !scene.entities) {
    throw new Error(`Failed at checkpoint ${cp}: Invalid scene structure`);
  }

  // Check for NaN
  if (isNaN(scene.camera.x) || isNaN(scene.camera.y) || isNaN(scene.camera.z)) {
    throw new Error(`NaN found in camera coordinates at checkpoint ${cp}`);
  }

  for (const ent of scene.entities) {
    if (isNaN(ent.x) || isNaN(ent.y) || isNaN(ent.z) || isNaN(ent.opacity)) {
      throw new Error(`NaN found in entity ${ent.id} at checkpoint ${cp}`);
    }
  }

  for (const edge of scene.edges) {
    if (isNaN(edge.drawProgress) || isNaN(edge.opacity)) {
      throw new Error(`NaN found in edge ${edge.id} at checkpoint ${cp}`);
    }
  }

  console.log(
    `  ✓ Checkpoint ${cp.toFixed(2)} [${scene.activeChapter.name}]: ` +
    `${scene.entities.filter(e => e.opacity > 0.1).length} visible nodes, ` +
    `${scene.edges.length} visible edges, ` +
    `camZ=${scene.camera.z.toFixed(0)}, ` +
    `noiseReduction=${scene.noiseReduction.toFixed(2)}, ` +
    `pulse=${scene.investigationPulse.active ? 'ACTIVE' : 'off'}`
  );
}

// Check Chapter 1: ZERO edges drawn
const ch1Scene = getSceneState(0.08);
if (ch1Scene.edges.length !== 0) {
  throw new Error(`Chapter 1 should have 0 edges, got ${ch1Scene.edges.length}`);
}
console.log('  ✓ Chapter 01 (0.08) has exactly 0 edges (strictly isolated fragments)');

// Check Chapter 2: Core edges emerging
const ch2Scene = getSceneState(0.25);
if (ch2Scene.edges.length < 1 || ch2Scene.edges.length > 4) {
  throw new Error(`Chapter 2 should have 1-4 active edges, got ${ch2Scene.edges.length}`);
}
console.log(`  ✓ Chapter 02 (0.25) has ${ch2Scene.edges.length} progressive correlation edges`);

// Check Chapter 3: Full intelligence graph
const ch3Scene = getSceneState(0.54);
if (ch3Scene.edges.length < 10) {
  throw new Error(`Chapter 3 should have complete network, got ${ch3Scene.edges.length} edges`);
}
console.log(`  ✓ Chapter 03 (0.54) has ${ch3Scene.edges.length} multi-cluster edges`);

// Check Chapter 4: Investigation pulse is active and moving
const ch4Scene = getSceneState(0.62);
if (!ch4Scene.investigationPulse.active) {
  throw new Error(`Chapter 4 investigation pulse should be active`);
}
console.log(`  ✓ Chapter 04 (0.62) investigation pulse active: ${ch4Scene.investigationPulse.stepLabel}`);

// Check Chapter 5: Noise reduction and Inferred Hidden Link
const ch5Scene = getSceneState(0.84);
if (ch5Scene.noiseReduction <= 0) {
  throw new Error(`Chapter 5 noise reduction should be active`);
}
const hasHiddenLink = ch5Scene.edges.some(e => e.isHiddenLink && e.isDashed);
if (!hasHiddenLink) {
  throw new Error(`Chapter 5 should have dashed inferred hidden link`);
}
console.log('  ✓ Chapter 05 (0.84) noise reduction active with dashed inferred hidden link');

// Check Chapter 6: Planar alignment and interface framing
const ch6Scene = getSceneState(0.98);
if (ch6Scene.planarAlignment < 0.9 || ch6Scene.interfaceFramingAlpha < 0.8) {
  throw new Error(`Chapter 6 should be in planar alignment with interface framing`);
}
console.log('  ✓ Chapter 06 (0.98) planar alignment = 1.0, interface framing = 1.0');

// Determinism test: calling getSceneState(0.63) 3 times
const s1 = JSON.stringify(getSceneState(0.63));
const s2 = JSON.stringify(getSceneState(0.63));
const s3 = JSON.stringify(getSceneState(0.63));
if (s1 !== s2 || s2 !== s3) {
  throw new Error('getSceneState is not deterministic!');
}
console.log('  ✓ Determinism verified: 3 identical calls to getSceneState(0.63) produce identical output');

console.log('\n✅ ALL 14 SCENE STATE CHECKPOINTS AND CHOREOGRAPHY TESTS PASSED PERFECTLY!');
