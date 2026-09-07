import assert from "node:assert";

// 3D Spatial projection test
function project3D(p, cam, viewWidth, viewHeight, fov = 540) {
  let dx = p.x - cam.x;
  let dy = p.y - cam.y;
  let dz = p.z - cam.z;

  const cosY = Math.cos(cam.yaw);
  const sinY = Math.sin(cam.yaw);
  const rx = dx * cosY + dz * sinY;
  const rz1 = -dx * sinY + dz * cosY;

  const cosP = Math.cos(cam.pitch);
  const sinP = Math.sin(cam.pitch);
  const ry = dy * cosP - rz1 * sinP;
  const rz = dy * sinP + rz1 * cosP;

  const depth = -rz;
  if (depth <= 15) return { inView: false, depth };

  const scale = fov / depth;
  const cx = viewWidth / 2;
  const cy = viewHeight / 2;
  const x2d = cx + rx * scale;
  const y2d = cy + ry * scale;

  return { x2d, y2d, scale, inView: true, depth };
}

function getCameraForScroll(s) {
  let x = 0, y = 0, z = 700, yaw = 0, pitch = 0;
  if (s <= 0.15) {
    z = 750 - (s / 0.15) * 70;
  } else if (s <= 0.35) {
    z = 680 - ((s - 0.15) / 0.20) * 160;
  } else if (s <= 0.55) {
    z = 520 - ((s - 0.35) / 0.20) * 140;
    yaw = 0.08 - ((s - 0.35) / 0.20) * 0.20;
  } else if (s <= 0.72) {
    z = 380 - ((s - 0.55) / 0.17) * 140;
  } else if (s <= 0.88) {
    z = 240 - ((s - 0.72) / 0.16) * 80;
  } else {
    z = 160 - ((s - 0.88) / 0.12) * 30;
  }
  return { x, y, z, yaw, pitch };
}

console.log("▶ Verifying 3D Spatial Projection Math...");
const testPoint = { x: 0, y: 0, z: 0 };
const camStart = getCameraForScroll(0);
const projStart = project3D(testPoint, camStart, 1920, 1080);
assert.ok(projStart.inView, "Point should be in view at scroll 0");
assert.equal(Math.round(projStart.x2d), 960, "Center X should be at half width (960)");
assert.equal(Math.round(projStart.y2d), 540, "Center Y should be at half height (540)");
console.log(`  ✓ Projected origin: (${projStart.x2d}, ${projStart.y2d}) at depth ${projStart.depth}`);

const camEnd = getCameraForScroll(1.0);
const projEnd = project3D(testPoint, camEnd, 1920, 1080);
assert.ok(projEnd.inView, "Point should remain in view at scroll 1.0");
assert.ok(projEnd.scale > projStart.scale, "Scale should increase as camera advances closer");
console.log(`  ✓ Camera flight: Z starts at ${camStart.z}, zooms into ${camEnd.z}, scale grows ${projStart.scale.toFixed(3)} -> ${projEnd.scale.toFixed(3)}`);

console.log("\n✅ ALL 3D SPATIAL ENGINE MATHEMATICS & TRAJECTORY TESTS PASSED!");
