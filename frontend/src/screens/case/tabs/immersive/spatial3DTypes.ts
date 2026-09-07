export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface ProjectedPoint {
  x2d: number;
  y2d: number;
  scale: number;
  depthAlpha: number;
  inView: boolean;
  depth: number;
}

export interface CameraState {
  x: number;
  y: number;
  z: number;
  yaw: number;
  pitch: number;
}

export type EdgeLifecycleState =
  | 'hidden'
  | 'emerging'
  | 'connecting'
  | 'stable'
  | 'focused'
  | 'dormant';

export interface SpatialNode {
  id: string;
  name: string;
  kind: string;
  risk?: string;
  cluster: number;
  isBridge: boolean;
  degree: number;
  harmonicPhase: number;
  depthLayer: 'foreground' | 'midground' | 'background';
  basePos: Point3D;
  currentPos: Point3D;
  scale: number;
  opacity: number;
  pingRadius?: number;
  pingAlpha?: number;
}

export interface SpatialFilament {
  id: string;
  sourceId: string;
  targetId: string;
  type: string;
  conf: number;
  is_hidden: boolean;
  directed: number;
  waveIndex: number;          // Wave 1, 2, 3...
  state: EdgeLifecycleState;
  drawProgress: number;       // 0.0 to 1.0 (progressive drawing along edge)
  pulsePosition?: number;     // 0.0 to 1.0 (traveling energy pulse)
  flashRadius?: number;       // Ignition flash ring radius
  flashAlpha?: number;        // Ignition flash ring opacity
  opacity: number;
  lineWidth: number;
  isSuspectPath?: boolean;
}

export interface DustParticle3D {
  x: number;
  y: number;
  z: number;
  size: number;
  speed: number;
  phase: number;
  alpha: number;
}
