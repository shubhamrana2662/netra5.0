import { Point3D, ProjectedPoint, CameraState, DustParticle3D } from './spatial3DTypes';

export function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t);
}

/**
 * Exact 3D perspective projection formula matching the CyberDrishti landing page.
 */
export function project3D(
  p: Point3D,
  cam: CameraState,
  viewWidth: number,
  viewHeight: number,
  fov = 580
): ProjectedPoint {
  const dx = p.x - cam.x;
  const dy = p.y - cam.y;
  const dz = p.z - cam.z;

  // Yaw rotation around Y
  const cosY = Math.cos(cam.yaw);
  const sinY = Math.sin(cam.yaw);
  const rx = dx * cosY + dz * sinY;
  const rz1 = -dx * sinY + dz * cosY;

  // Pitch rotation around X
  const cosP = Math.cos(cam.pitch);
  const sinP = Math.sin(cam.pitch);
  const ry = dy * cosP - rz1 * sinP;
  const rz = dy * sinP + rz1 * cosP;

  const depth = -rz;

  if (depth <= 15) {
    return { x2d: 0, y2d: 0, scale: 0, depthAlpha: 0, inView: false, depth };
  }

  const scale = fov / depth;
  const cx = viewWidth / 2;
  const cy = viewHeight / 2;
  const x2d = cx + rx * scale;
  const y2d = cy + ry * scale;

  // Depth attenuation: foreground is luminous and crisp, background gently recedes
  const depthAlpha = clamp(1.2 - depth / 1400, 0.05, 1.0);
  const inView = x2d >= -120 && x2d <= viewWidth + 120 && y2d >= -120 && y2d <= viewHeight + 120;

  return { x2d, y2d, scale, depthAlpha, inView, depth };
}

/**
 * Creates ambient 3D dust particle pool for physical atmosphere
 */
export function createDustPool(count = 55): DustParticle3D[] {
  const pool: DustParticle3D[] = [];
  let seed = 7123;
  const rnd = () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  for (let i = 0; i < count; i++) {
    pool.push({
      x: (rnd() - 0.5) * 1200,
      y: (rnd() - 0.5) * 800,
      z: (rnd() - 0.5) * 600,
      size: 1.0 + rnd() * 1.8,
      speed: 0.5 + rnd() * 0.8,
      phase: rnd() * Math.PI * 2,
      alpha: 0.15 + rnd() * 0.35,
    });
  }
  return pool;
}

export interface GraphBoundsInfo {
  center: Point3D;
  size: { width: number; height: number; depth: number };
  optimalCamZ: number;
}

export function computeGraphBounds(
  nodes: Array<{ basePos: Point3D }> | Iterable<{ basePos: Point3D }>
): GraphBoundsInfo {
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  let minZ = Infinity, maxZ = -Infinity;
  let count = 0;

  for (const n of nodes) {
    count++;
    if (n.basePos.x < minX) minX = n.basePos.x;
    if (n.basePos.x > maxX) maxX = n.basePos.x;
    if (n.basePos.y < minY) minY = n.basePos.y;
    if (n.basePos.y > maxY) maxY = n.basePos.y;
    if (n.basePos.z < minZ) minZ = n.basePos.z;
    if (n.basePos.z > maxZ) maxZ = n.basePos.z;
  }

  if (count === 0) {
    return {
      center: { x: 0, y: 0, z: 0 },
      size: { width: 400, height: 300, depth: 100 },
      optimalCamZ: 580
    };
  }

  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const cz = (minZ + maxZ) / 2;
  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const maxSpan = Math.max(spanX, spanY, 280);
  const optimalCamZ = cz + maxSpan * 0.95 + 130;

  return {
    center: { x: Math.round(cx), y: Math.round(cy), z: Math.round(cz) },
    size: { width: Math.round(spanX), height: Math.round(spanY), depth: Math.round(maxZ - minZ) },
    optimalCamZ: clamp(Math.round(optimalCamZ), 460, 850)
  };
}
