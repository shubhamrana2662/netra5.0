// 3D Spatial Mathematics & Trajectory Engine for CyberDrishti Landing Experience

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

export interface SpatialEntity {
  id: string;
  label: string;
  kind: 'SIGNAL' | 'PERSON' | 'DEVICE' | 'ACCOUNT' | 'IP' | 'FILE' | 'PHONE' | 'UPI' | 'BANK';
  subtext?: string;
  cluster: number;
  isCoreFragment: boolean; // True for the 6 initial isolated fragments (Ch 1 & 2)
  isSuspectChain?: boolean; // True for the 4-step investigation path (Ch 4)
  isBridge?: boolean;       // True for Device A83F-29 (Ch 5 bridge)
  harmonicPhase: number;    // Unique phase for subtle organic drift in Ch 1

  // Distinct coordinates per narrative stage:
  pIsolated: Point3D; // Chapter 1: Widely scattered isolated positions in empty space
  pCore: Point3D;     // Chapter 2: Converged connected core
  pGraph: Point3D;    // Chapter 3 & 4: Multi-cluster graph topology
  pFinal: Point3D;    // Chapter 5 & 6: Planar aligned intelligence map (z ~ 0)
}

export interface SpatialEdge {
  id: string;
  a: string;
  b: string;
  stage: 'core' | 'network' | 'inferred'; // Which narrative stage edge belongs to
  ignitionScroll: number; // Exact scroll value where this edge ignites [0, 1]
  isSuspectChain?: boolean;
  isHiddenLink?: boolean;
  label?: string;
  evidenceBasis?: string;
}

export interface CameraState {
  x: number;
  y: number;
  z: number;
  yaw: number;   // Rotation around Y
  pitch: number; // Rotation around X
}

// ── Smooth cubic easing for milestones ──
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t);
}

export function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

// ── Deterministic PRNG ──
export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ── Canonical Spatial Entities ──
// 6 Core fragments (visible from Chapter 1) + 6 Expansion nodes (appear in Chapter 3)
export const SPATIAL_ENTITIES: SpatialEntity[] = [
  // ── THE 6 INITIAL ISOLATED FRAGMENTS (Visible from Chapter 1 onward) ──
  {
    id: 'ent-phone',
    label: '+91 98201 44821',
    subtext: 'CDR recorded · Jamtara cluster',
    kind: 'PHONE',
    cluster: 0,
    isCoreFragment: true,
    isSuspectChain: true,
    harmonicPhase: 0.1,
    pIsolated: { x: -260, y: -150, z: 80 },  // Far upper-left
    pCore:     { x: -110, y: -60,  z: 30 },  // Gravitates into core
    pGraph:    { x: -170, y: -80,  z: 60 },  // In cluster 0
    pFinal:    { x: -210, y: -50,  z: 0 },   // Planar
  },
  {
    id: 'ent-device-a83f',
    label: 'Device A83F-29',
    subtext: 'Bridge broker · Jamtara',
    kind: 'DEVICE',
    cluster: 0,
    isCoreFragment: true,
    isSuspectChain: true,
    isBridge: true, // Key Boundary Bridge node
    harmonicPhase: 1.4,
    pIsolated: { x: 30,   y: -210, z: 60 },  // Isolated high center
    pCore:     { x: -20,  y: 10,   z: 20 },  // Core junction
    pGraph:    { x: 0,    y: 0,    z: 30 },  // Central bridge
    pFinal:    { x: -20,  y: 0,    z: 0 },   // Planar
  },
  {
    id: 'ent-upi',
    label: 'mule.pay@okhdfcbank',
    subtext: 'Virtual Payment Address',
    kind: 'UPI',
    cluster: 0,
    isCoreFragment: true,
    isSuspectChain: true,
    harmonicPhase: 2.8,
    pIsolated: { x: 230,  y: -130, z: -40 }, // Far upper-right
    pCore:     { x: 60,   y: -40,  z: 20 },  // Converges near device
    pGraph:    { x: 80,   y: -60,  z: 40 },  // Near financial funnel
    pFinal:    { x: 80,   y: -40,  z: 0 },   // Planar
  },
  {
    id: 'ent-account-4821',
    label: 'Axis Bank ••4821',
    subtext: '₹45,000 velocity match · Hub',
    kind: 'ACCOUNT',
    cluster: 1,
    isCoreFragment: true,
    isSuspectChain: true,
    harmonicPhase: 4.1,
    pIsolated: { x: 250,  y: 150,  z: 50 },  // Far lower-right
    pCore:     { x: 130,  y: 50,   z: 20 },  // Converges with UPI
    pGraph:    { x: 140,  y: 20,   z: 40 },  // Cluster 1 hub
    pFinal:    { x: 150,  y: 20,   z: 0 },   // Planar
  },
  {
    id: 'ent-account-72',
    label: 'Account #72',
    subtext: 'Rapid forward · Exfiltration',
    kind: 'ACCOUNT',
    cluster: 1,
    isCoreFragment: true,
    isSuspectChain: true,
    harmonicPhase: 5.3,
    pIsolated: { x: 340,  y: 30,   z: 90 },  // Far outer right
    pCore:     { x: 190,  y: -20,  z: 30 },  // Follows account 4821
    pGraph:    { x: 240,  y: 40,   z: 60 },  // Exfiltration edge
    pFinal:    { x: 240,  y: 40,   z: 0 },   // Planar
  },
  {
    id: 'ent-ip',
    label: '192.0.2.133',
    subtext: 'Egress session IP',
    kind: 'IP',
    cluster: 0,
    isCoreFragment: true,
    isSuspectChain: false,
    harmonicPhase: 3.2,
    pIsolated: { x: -210, y: 180,  z: 70 },  // Far lower-left
    pCore:     { x: -160, y: 90,   z: 40 },  // Inward
    pGraph:    { x: -250, y: 90,   z: 80 },  // Telemetry node
    pFinal:    { x: -260, y: 80,   z: 0 },   // Planar
  },

  // ── THE 6 EXPANSION NODES (Appear in Chapter 3 to form complete multi-cluster network) ──
  {
    id: 'ent-person-04',
    label: 'Rajesh Kumar',
    subtext: 'Primary Operative · Handler',
    kind: 'PERSON',
    cluster: 0,
    isCoreFragment: false,
    isSuspectChain: false,
    harmonicPhase: 0.8,
    pIsolated: { x: -300, y: -220, z: 120 },
    pCore:     { x: -200, y: -140, z: 80 },
    pGraph:    { x: -200, y: -130, z: 70 },
    pFinal:    { x: -180, y: -110, z: 0 },
  },
  {
    id: 'ent-bank-hdfc',
    label: 'HDFC Bank · HDFC000182',
    subtext: 'Clearing settlement node',
    kind: 'BANK',
    cluster: 1,
    isCoreFragment: false,
    isSuspectChain: false,
    harmonicPhase: 2.2,
    pIsolated: { x: 180,  y: 260,  z: 110 },
    pCore:     { x: 140,  y: 160,  z: 80 },
    pGraph:    { x: 150,  y: 120,  z: 70 },
    pFinal:    { x: 160,  y: 100,  z: 0 },
  },
  {
    id: 'ent-hash-bundle',
    label: 'Transfer Slip · SHA:8f3a…',
    subtext: 'NEFT ledger proof',
    kind: 'FILE',
    cluster: 1,
    isCoreFragment: false,
    isSuspectChain: false,
    harmonicPhase: 4.7,
    pIsolated: { x: 280,  y: -210, z: 140 },
    pCore:     { x: 190,  y: -140, z: 90 },
    pGraph:    { x: 180,  y: -130, z: 80 },
    pFinal:    { x: 170,  y: -120, z: 0 },
  },
  {
    id: 'ent-mule-a1',
    label: 'Account ••3120',
    subtext: 'Layering feeder account',
    kind: 'ACCOUNT',
    cluster: 1,
    isCoreFragment: false,
    isSuspectChain: false,
    harmonicPhase: 1.9,
    pIsolated: { x: 360,  y: -100, z: 160 },
    pCore:     { x: 260,  y: -70,  z: 100 },
    pGraph:    { x: 250,  y: -80,  z: 80 },
    pFinal:    { x: 240,  y: -70,  z: 0 },
  },
  {
    id: 'ent-c2-domain',
    label: 'cdn-shadow07.com',
    subtext: 'Phishing panel proxy',
    kind: 'IP',
    cluster: 2,
    isCoreFragment: false,
    isSuspectChain: false,
    harmonicPhase: 3.7,
    pIsolated: { x: -350, y: -80,  z: 180 },
    pCore:     { x: -280, y: -160, z: 120 },
    pGraph:    { x: -260, y: -180, z: 100 },
    pFinal:    { x: -250, y: -170, z: 0 },
  },
  {
    id: 'ent-device-c9a2',
    label: 'Device C9A2-11',
    subtext: 'Secondary relay terminal',
    kind: 'DEVICE',
    cluster: 2,
    isCoreFragment: false,
    isSuspectChain: false,
    harmonicPhase: 5.1,
    pIsolated: { x: -120, y: -300, z: 160 },
    pCore:     { x: -90,  y: -230, z: 110 },
    pGraph:    { x: -90,  y: -210, z: 90 },
    pFinal:    { x: -80,  y: -190, z: 0 },
  },
];

// ── Filament Connections & Ignitions ──
export const SPATIAL_EDGES: SpatialEdge[] = [
  // ── CHAPTER 2 CORE CORRELATION EDGES (Ignite progressively as nodes converge) ──
  {
    id: 'ed-phone-dev',
    a: 'ent-phone',
    b: 'ent-device-a83f',
    stage: 'core',
    ignitionScroll: 0.19, // First ignition
    isSuspectChain: true,
    label: '09:42:13 comms',
    evidenceBasis: 'CDR IMEI overlap'
  },
  {
    id: 'ed-dev-upi',
    a: 'ent-device-a83f',
    b: 'ent-upi',
    stage: 'core',
    ignitionScroll: 0.23, // Second ignition
    isSuspectChain: true,
    label: 'app binding',
    evidenceBasis: 'VPA device fingerprint'
  },
  {
    id: 'ed-upi-acc',
    a: 'ent-upi',
    b: 'ent-account-4821',
    stage: 'core',
    ignitionScroll: 0.27, // Third ignition
    isSuspectChain: true,
    label: '₹45k transfer',
    evidenceBasis: 'Immediate settlement'
  },
  {
    id: 'ed-acc-acc72',
    a: 'ent-account-4821',
    b: 'ent-account-72',
    stage: 'core',
    ignitionScroll: 0.31, // Fourth ignition
    isSuspectChain: true,
    label: 'rapid forward',
    evidenceBasis: 'Velocity match within 4 min'
  },

  // ── CHAPTER 3 NETWORK EDGES (Bloom across the 3 clusters) ──
  {
    id: 'ed-pers-phone',
    a: 'ent-person-04',
    b: 'ent-phone',
    stage: 'network',
    ignitionScroll: 0.36,
    label: 'subscriber',
    evidenceBasis: 'CAF registration'
  },
  {
    id: 'ed-pers-dev',
    a: 'ent-person-04',
    b: 'ent-device-a83f',
    stage: 'network',
    ignitionScroll: 0.38,
    label: 'hardware bind',
    evidenceBasis: 'Shared IMEI'
  },
  {
    id: 'ed-pers-ip',
    a: 'ent-person-04',
    b: 'ent-ip',
    stage: 'network',
    ignitionScroll: 0.40,
    label: 'session auth',
    evidenceBasis: 'Radius login'
  },
  {
    id: 'ed-upi-bank',
    a: 'ent-upi',
    b: 'ent-bank-hdfc',
    stage: 'network',
    ignitionScroll: 0.42,
    label: 'settles_at',
    evidenceBasis: 'IFSC route'
  },
  {
    id: 'ed-acc-hash',
    a: 'ent-account-4821',
    b: 'ent-hash-bundle',
    stage: 'network',
    ignitionScroll: 0.44,
    label: 'ledger proof',
    evidenceBasis: 'Cryptographic match'
  },
  {
    id: 'ed-mule-acc',
    a: 'ent-mule-a1',
    b: 'ent-account-4821',
    stage: 'network',
    ignitionScroll: 0.46,
    label: 'feeder funnel',
    evidenceBasis: 'Micro-layering'
  },
  {
    id: 'ed-pers-c2',
    a: 'ent-person-04',
    b: 'ent-c2-domain',
    stage: 'network',
    ignitionScroll: 0.48,
    label: 'DNS query',
    evidenceBasis: 'Resolver telemetry'
  },
  {
    id: 'ed-c2-dev2',
    a: 'ent-c2-domain',
    b: 'ent-device-c9a2',
    stage: 'network',
    ignitionScroll: 0.50,
    label: 'relay heartbeat',
    evidenceBasis: 'TCP keepalive'
  },

  // ── CHAPTER 5 INFERRED HIDDEN LINK (Sparks in Chapter 5) ──
  {
    id: 'ed-hidden-pers-acc72',
    a: 'ent-person-04',
    b: 'ent-account-72',
    stage: 'inferred',
    ignitionScroll: 0.75, // Dramatic spark in Chapter 5
    isHiddenLink: true,
    label: 'INFERRED · 88.4%',
    evidenceBasis: 'Multi-hop velocity match + shared mule handler'
  }
];

// ── Background Ambient Spatial Dust Particles ──
export interface DustParticle {
  x: number;
  y: number;
  z: number;
  size: number;
  alpha: number;
  speed: number;
  phase: number;
}

export function createDustPool(count = 70): DustParticle[] {
  const rnd = mulberry32(0x94213);
  const dust: DustParticle[] = [];
  for (let i = 0; i < count; i++) {
    dust.push({
      x: (rnd() - 0.5) * 1200,
      y: (rnd() - 0.5) * 800,
      z: rnd() * 1200 - 200,
      size: 0.8 + rnd() * 1.5,
      alpha: 0.10 + rnd() * 0.22,
      speed: 0.4 + rnd() * 0.8,
      phase: rnd() * Math.PI * 2
    });
  }
  return dust;
}

// ── Chapter Boundaries ──
export const CHAPTER_RANGES = {
  CH1: [0.00, 0.16] as const,
  CH2: [0.16, 0.34] as const,
  CH3: [0.34, 0.52] as const,
  CH4: [0.52, 0.70] as const,
  CH5: [0.70, 0.86] as const,
  CH6: [0.86, 1.00] as const,
};

// ── Camera Path Spline based on Scroll Progress [0, 1] ──
export function getCameraForScroll(s: number, mouseX = 0, mouseY = 0): CameraState {
  let x = 0, y = 0, z = 620, yaw = 0, pitch = 0;

  if (s <= 0.16) {
    // ── CHAPTER 01: ISOLATED FRAGMENTS ──
    // Wide, high-altitude perspective surveying empty space
    const p = s / 0.16;
    z = lerp(660, 600, easeInOutCubic(p));
    y = lerp(-15, -5, p);
    yaw = lerp(-0.02, 0.02, p);
  } else if (s <= 0.34) {
    // ── CHAPTER 02: FRAGMENTS ACTIVELY CONNECTING ──
    // Gliding closer to tightly frame the converging core constellation
    const p = (s - 0.16) / 0.18;
    const ep = easeInOutCubic(p);
    z = lerp(600, 360, ep);
    x = lerp(0, -10, ep);
    y = lerp(-5, 5, ep);
    yaw = lerp(0.02, 0.05, ep);
  } else if (s <= 0.52) {
    // ── CHAPTER 03: THE INTELLIGENCE GRAPH EMERGES ──
    // Strategic pullback & angled perspective to reveal the vast 3-cluster universe
    const p = (s - 0.34) / 0.18;
    const ep = easeInOutCubic(p);
    z = lerp(360, 480, ep);
    x = lerp(-10, 20, ep);
    y = lerp(5, -15, ep);
    yaw = lerp(0.05, -0.12, ep);
    pitch = lerp(0, 0.06, ep);
  } else if (s <= 0.70) {
    // ── CHAPTER 04: FOLLOW THE EVIDENCE ──
    // Directional tracking camera following the high-energy probe sequentially
    const p = (s - 0.52) / 0.18;
    const ep = easeInOutCubic(p);
    z = lerp(380, 290, ep);
    x = lerp(-30, 45, ep); // Sweeps across from Phone/Device to Axis Bank/Account 72
    y = lerp(-15, 10, ep);
    yaw = lerp(-0.08, 0.04, ep);
    pitch = lerp(0.04, -0.02, ep);
  } else if (s <= 0.86) {
    // ── CHAPTER 05: HIDDEN PATTERN DISCOVERY ──
    // Tight dramatic focus dead-center on the Bridge entity and inferred span
    const p = (s - 0.70) / 0.16;
    const ep = easeInOutCubic(p);
    z = lerp(290, 230, ep);
    x = lerp(45, 0, ep);
    y = lerp(10, 0, ep);
    yaw = lerp(0.04, 0, ep);
    pitch = lerp(-0.02, 0, ep);
  } else {
    // ── CHAPTER 06: RESOLUTION INTO INTELLIGENCE ──
    // Perfectly stable frontal alignment, flat and calm
    const p = (s - 0.86) / 0.14;
    const ep = easeInOutCubic(p);
    z = lerp(230, 260, ep);
    x = 0;
    y = 0;
    yaw = 0;
    pitch = 0;
  }

  // Subtle interactive parallax offset (controlled & restrained)
  x += mouseX * 25;
  y += mouseY * 18;
  yaw += mouseX * 0.02;
  pitch += mouseY * 0.015;

  return { x, y, z, yaw, pitch };
}

// ── Interpolate Entity Position for Scroll Progress & Time ──
export function getEntityPosition(e: SpatialEntity, s: number, time = 0): Point3D {
  if (s <= 0.16) {
    // Chapter 1: Widely separated isolated positions with subtle organic harmonic float
    const driftX = Math.sin(time * 0.0008 + e.harmonicPhase) * 6;
    const driftY = Math.cos(time * 0.0006 + e.harmonicPhase * 1.5) * 5;
    return {
      x: e.pIsolated.x + driftX,
      y: e.pIsolated.y + driftY,
      z: e.pIsolated.z
    };
  } else if (s <= 0.34) {
    // Chapter 2: Physically gravitating from isolated positions to connected core arrangement!
    const p = easeInOutCubic((s - 0.16) / 0.18);
    return {
      x: lerp(e.pIsolated.x, e.pCore.x, p),
      y: lerp(e.pIsolated.y, e.pCore.y, p),
      z: lerp(e.pIsolated.z, e.pCore.z, p)
    };
  } else if (s <= 0.52) {
    // Chapter 3: Expanding from core into multi-cluster network topology
    const p = easeInOutCubic((s - 0.34) / 0.18);
    return {
      x: lerp(e.pCore.x, e.pGraph.x, p),
      y: lerp(e.pCore.y, e.pGraph.y, p),
      z: lerp(e.pCore.z, e.pGraph.z, p)
    };
  } else if (s <= 0.70) {
    // Chapter 4: Stable in graph topology while investigation pulse traces through
    return {
      x: e.pGraph.x,
      y: e.pGraph.y,
      z: e.pGraph.z
    };
  } else if (s <= 0.86) {
    // Chapter 5: Transitioning into planar alignment
    const p = easeInOutCubic((s - 0.70) / 0.16);
    return {
      x: lerp(e.pGraph.x, e.pFinal.x, p),
      y: lerp(e.pGraph.y, e.pFinal.y, p),
      z: lerp(e.pGraph.z, e.pFinal.z, p)
    };
  } else {
    // Chapter 6: Settled in final planar intelligence map (z ~ 0)
    return {
      x: e.pFinal.x,
      y: e.pFinal.y,
      z: e.pFinal.z
    };
  }
}

// ── Entity Opacity by Chapter State ──
// Controls the absolute presence of nodes across chapters
export function getEntityOpacity(e: SpatialEntity, s: number): number {
  if (e.isCoreFragment) {
    // Core fragments are always visible, but dim appropriately in Chapter 5
    if (s <= 0.52) return 1.0;
    if (s <= 0.70) return e.isSuspectChain ? 1.0 : 0.35;
    if (s <= 0.86) {
      // Chapter 5: Deep noise reduction — only suspect chain and bridge entity remain luminous
      const p = clamp((s - 0.70) / 0.08, 0, 1);
      if (e.isSuspectChain || e.isBridge) return 1.0;
      return lerp(0.35, 0.03, p); // Dims to 3%
    }
    // Chapter 6: Restores to clean planar harmony
    return 1.0;
  } else {
    // Expansion nodes: COMPLETELY HIDDEN in Chapters 1 & 2!
    if (s < 0.34) return 0.0;
    if (s <= 0.52) {
      // Bloom outward into Chapter 3
      const p = clamp((s - 0.34) / 0.10, 0, 1);
      return easeOutQuad(p);
    }
    if (s <= 0.70) {
      // Chapter 4: Recedes into background (20%)
      return 0.20;
    }
    if (s <= 0.86) {
      // Chapter 5: Deep noise reduction (3% ghost presence)
      return 0.03;
    }
    // Chapter 6: Re-emerges in balanced equilibrium (75%)
    const p = clamp((s - 0.86) / 0.10, 0, 1);
    return lerp(0.03, 0.75, p);
  }
}

// ── Project 3D Point to 2D Screen Space ──
export function project3D(
  p: Point3D,
  cam: CameraState,
  viewWidth: number,
  viewHeight: number,
  fov = 540
): ProjectedPoint {
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

  if (depth <= 15) {
    return { x2d: 0, y2d: 0, scale: 0, depthAlpha: 0, inView: false, depth };
  }

  const scale = fov / depth;
  const cx = viewWidth / 2;
  const cy = viewHeight / 2;
  const x2d = cx + rx * scale;
  const y2d = cy + ry * scale;

  const depthAlpha = clamp(1.15 - depth / 1300, 0, 1);
  const inView = x2d >= -100 && x2d <= viewWidth + 100 && y2d >= -100 && y2d <= viewHeight + 100;

  return { x2d, y2d, scale, depthAlpha, inView, depth };
}
