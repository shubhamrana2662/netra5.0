import {
  SPATIAL_ENTITIES,
  SPATIAL_EDGES,
  type SpatialEntity,
  type SpatialEdge
} from './spatialEngine';
import { STORY_CHAPTERS } from './storyConfig';
import {
  clamp,
  lerp,
  inverseLerp,
  smoothstep,
  easeInOutCubic,
  getActiveChapter,
  getChapterProgress
} from './storyUtils';
import type {
  SceneState,
  CameraState,
  EntityVisualState,
  EdgeVisualState,
  InvestigationPulseState
} from './storyTypes';

/**
 * Pure, deterministic storytelling engine.
 * Computes the complete visual universe state for ANY storyProgress value in [0.0, 1.0].
 * Completely free of side effects, timers, or stateful history.
 */
export function getSceneState(storyProgress: number): SceneState {
  const p = clamp(storyProgress, 0, 1);
  const activeChapter = getActiveChapter(p);
  const localProgress = getChapterProgress(p, activeChapter);

  // ── 1. DETERMINISTIC CAMERA CHOREOGRAPHY ──
  const camera = calculateCamera(p);

  // ── 2. GLOBAL STAGE PARAMETERS ──
  // Noise reduction: 0 (full noise) -> 1 (deep reduction in Ch 5)
  let noiseReduction = 0;
  if (p >= 0.76 && p <= 0.88) {
    // Ramp up noise reduction between 0.76 and 0.81, hold until 0.88
    noiseReduction = smoothstep(inverseLerp(p, 0.76, 0.81));
  }

  // Bridge emphasis: 0 -> 1 during Chapter 5
  let bridgeEmphasis = 0;
  if (p >= 0.80 && p <= 0.88) {
    bridgeEmphasis = smoothstep(inverseLerp(p, 0.80, 0.84));
  } else if (p > 0.88 && p <= 0.94) {
    bridgeEmphasis = lerp(1, 0, inverseLerp(p, 0.88, 0.94));
  }

  // Hidden link reveal progress: 0 -> 1 in Chapter 5
  let hiddenLinkProgress = 0;
  if (p >= 0.83) {
    hiddenLinkProgress = smoothstep(inverseLerp(p, 0.83, 0.87));
  }

  // Planar alignment: 0 (3D scattered) -> 1 (flat 2D isometric in Ch 6)
  let planarAlignment = 0;
  if (p >= 0.92) {
    planarAlignment = easeInOutCubic(inverseLerp(p, 0.92, 0.98));
  }

  // Background particle density factor
  let backgroundDensity = 1.0;
  if (p <= 0.16) {
    backgroundDensity = lerp(0.35, 0.60, p / 0.16);
  } else if (p >= 0.76 && p <= 0.88) {
    backgroundDensity = lerp(1.0, 0.15, noiseReduction);
  } else if (p > 0.88) {
    backgroundDensity = lerp(0.15, 0.70, (p - 0.88) / 0.12);
  }

  // Interface brackets in Chapter 6
  let interfaceFramingAlpha = 0;
  if (p >= 0.94) {
    interfaceFramingAlpha = smoothstep(inverseLerp(p, 0.94, 0.99));
  }

  // ── 3. COMPUTE ENTITY VISUAL STATES ──
  const entityMap = new Map<string, EntityVisualState>();
  const entities: EntityVisualState[] = [];

  for (let i = 0; i < SPATIAL_ENTITIES.length; i++) {
    const e = SPATIAL_ENTITIES[i];
    const entState = calculateEntityVisualState(e, p, noiseReduction, bridgeEmphasis, planarAlignment);
    entityMap.set(e.id, entState);
    entities.push(entState);
  }

  // ── 4. COMPUTE EDGE VISUAL STATES ──
  const edges: EdgeVisualState[] = [];

  for (let i = 0; i < SPATIAL_EDGES.length; i++) {
    const edge = SPATIAL_EDGES[i];
    const source = entityMap.get(edge.a);
    const target = entityMap.get(edge.b);
    if (!source || !target) continue;

    const edgeState = calculateEdgeVisualState(edge, p, source, target, noiseReduction);
    if (edgeState) {
      edges.push(edgeState);
    }
  }

  // ── 5. COMPUTE SEQUENTIAL INVESTIGATION PULSE (CHAPTER 04: 0.54 -> 0.72) ──
  const investigationPulse = calculateInvestigationPulse(p, entityMap);

  return {
    storyProgress: p,
    activeChapter,
    localProgress,
    camera,
    entities,
    edges,
    investigationPulse,
    bridgeEmphasis,
    hiddenLinkProgress,
    noiseReduction,
    planarAlignment,
    backgroundDensity,
    interfaceFramingAlpha,
  };
}

// ── CAMERA PATH CHOREOGRAPHY ──
function calculateCamera(p: number): CameraState {
  let x = 0, y = 0, z = 620, yaw = 0, pitch = 0;

  if (p <= 0.16) {
    // Chapter 01: The Problem (Wide, high survey of empty space)
    const t = p / 0.16;
    z = lerp(660, 600, easeInOutCubic(t));
    y = lerp(-15, -5, t);
    yaw = lerp(-0.02, 0.02, t);
  } else if (p <= 0.35) {
    // Chapter 02: Correlation (Gliding closer as fragments converge)
    const t = (p - 0.16) / 0.19;
    const ep = easeInOutCubic(t);
    z = lerp(600, 360, ep);
    x = lerp(0, -10, ep);
    y = lerp(-5, 5, ep);
    yaw = lerp(0.02, 0.05, ep);
  } else if (p <= 0.54) {
    // Chapter 03: The Graph (Pullback & angled perspective to reveal full scale)
    const t = (p - 0.35) / 0.19;
    const ep = easeInOutCubic(t);
    z = lerp(360, 480, ep);
    x = lerp(-10, 20, ep);
    y = lerp(5, -15, ep);
    yaw = lerp(0.05, -0.12, ep);
    pitch = lerp(0, 0.06, ep);
  } else if (p <= 0.72) {
    // Chapter 04: Evidence Trail (Directional tracking camera flying with the probe)
    const t = (p - 0.54) / 0.18;
    const ep = easeInOutCubic(t);
    z = lerp(380, 280, ep);
    x = lerp(-30, 45, ep);
    y = lerp(-15, 10, ep);
    yaw = lerp(-0.08, 0.04, ep);
    pitch = lerp(0.04, -0.02, ep);
  } else if (p <= 0.88) {
    // Chapter 05: Hidden Patterns (Tight dramatic focus centered on the Bridge)
    const t = (p - 0.72) / 0.16;
    const ep = easeInOutCubic(t);
    z = lerp(280, 230, ep);
    x = lerp(45, 0, ep);
    y = lerp(10, 0, ep);
    yaw = lerp(0.04, 0, ep);
    pitch = lerp(-0.02, 0, ep);
  } else {
    // Chapter 06: Resolution (Straight-on frontal view, serene and stable)
    const t = (p - 0.88) / 0.12;
    const ep = easeInOutCubic(t);
    z = lerp(230, 260, ep);
    x = 0;
    y = 0;
    yaw = 0;
    pitch = 0;
  }

  return { x, y, z, yaw, pitch };
}

// ── ENTITY VISUAL STATE CALCULATION ──
function calculateEntityVisualState(
  e: SpatialEntity,
  p: number,
  noiseReduction: number,
  bridgeEmphasis: number,
  planarAlignment: number
): EntityVisualState {
  let x = e.pIsolated.x;
  let y = e.pIsolated.y;
  let z = e.pIsolated.z;
  let opacity = 1.0;
  let scale = 1.0;
  let pingRadius: number | undefined;
  let pingAlpha: number | undefined;

  // 1. POSITION INTERPOLATION ACROSS CHAPTERS
  if (p <= 0.16) {
    // Chapter 01: Isolated positions
    x = e.pIsolated.x;
    y = e.pIsolated.y;
    z = e.pIsolated.z;
  } else if (p <= 0.35) {
    // Chapter 02: Gravitating from isolated to core
    const t = easeInOutCubic((p - 0.16) / 0.19);
    x = lerp(e.pIsolated.x, e.pCore.x, t);
    y = lerp(e.pIsolated.y, e.pCore.y, t);
    z = lerp(e.pIsolated.z, e.pCore.z, t);
  } else if (p <= 0.54) {
    // Chapter 03: Expanding from core into full multi-cluster graph
    const t = easeInOutCubic((p - 0.35) / 0.19);
    x = lerp(e.pCore.x, e.pGraph.x, t);
    y = lerp(e.pCore.y, e.pGraph.y, t);
    z = lerp(e.pCore.z, e.pGraph.z, t);
  } else if (p <= 0.72) {
    // Chapter 04: Stable in graph topology
    x = e.pGraph.x;
    y = e.pGraph.y;
    z = e.pGraph.z;
  } else if (p <= 0.88) {
    // Chapter 05: Transition toward final layout
    const t = easeInOutCubic((p - 0.72) / 0.16);
    x = lerp(e.pGraph.x, e.pFinal.x, t);
    y = lerp(e.pGraph.y, e.pFinal.y, t);
    z = lerp(e.pGraph.z, e.pFinal.z, t);
  } else {
    // Chapter 06: Settle into planar alignment (z -> 0)
    x = e.pFinal.x;
    y = e.pFinal.y;
    z = lerp(e.pFinal.z, 0, planarAlignment);
  }

  // 2. OPACITY DETERMINATION
  if (e.isCoreFragment) {
    // Core fragments visible throughout, dim during noise reduction if not in suspect path
    if (p <= 0.72) {
      if (p <= 0.04) {
        // Initial fade-in at very beginning of Chapter 01
        opacity = lerp(0.3, 1.0, p / 0.04);
      } else if (p >= 0.54 && p <= 0.72) {
        // Chapter 04: Suspect chain stays 100%, non-suspect core nodes dim to 35%
        opacity = e.isSuspectChain ? 1.0 : 0.35;
      } else {
        opacity = 1.0;
      }
    } else if (p <= 0.88) {
      // Chapter 05: Critical noise reduction
      if (e.isSuspectChain || e.isBridge) {
        opacity = 1.0;
      } else {
        opacity = lerp(0.35, 0.04, noiseReduction);
      }
    } else {
      // Chapter 06: Restores to 1.0
      opacity = 1.0;
    }
  } else {
    // Expansion nodes: COMPLETELY HIDDEN in Chapter 01 and 02!
    if (p < 0.35) {
      opacity = 0.0;
    } else if (p <= 0.54) {
      // Chapter 03: Progressive bloom into view
      const t = clamp((p - 0.35) / 0.10, 0, 1);
      opacity = smoothstep(t);
    } else if (p <= 0.72) {
      // Chapter 04: Recedes into background context (20%)
      opacity = 0.20;
    } else if (p <= 0.88) {
      // Chapter 05: Deep noise reduction (4% ghost)
      opacity = lerp(0.20, 0.04, noiseReduction);
    } else {
      // Chapter 06: Restores in planar equilibrium (80%)
      const t = clamp((p - 0.88) / 0.08, 0, 1);
      opacity = lerp(0.04, 0.80, t);
    }
  }

  // 3. SCALE & EMPHASIS
  if (e.isBridge && bridgeEmphasis > 0) {
    scale = lerp(1.0, 1.35, bridgeEmphasis);
  }

  // 4. RADAR PING IN CHAPTER 01
  if (p <= 0.16 && e.isCoreFragment) {
    const pingPhase = ((p * 15 + e.harmonicPhase) % 1);
    pingRadius = 15 + pingPhase * 55;
    pingAlpha = (1 - pingPhase) * 0.35 * (1 - p / 0.16);
  }

  return {
    id: e.id,
    label: e.label,
    subtext: e.subtext,
    kind: e.kind,
    cluster: e.cluster,
    x,
    y,
    z,
    opacity,
    scale,
    isBridge: e.isBridge,
    isSuspectChain: e.isSuspectChain,
    isHighlighted: (e.isSuspectChain && p >= 0.54) || (e.isBridge && p >= 0.76),
    pingRadius,
    pingAlpha,
  };
}

// ── EDGE VISUAL STATE CALCULATION ──
function calculateEdgeVisualState(
  edge: SpatialEdge,
  p: number,
  source: EntityVisualState,
  target: EntityVisualState,
  noiseReduction: number
): EdgeVisualState | null {
  // In Chapter 01 (p < 0.16): ZERO edges visible!
  if (p < 0.16) return null;

  // Chapter 02 core edges ignite between 0.19 and 0.31
  // Chapter 03 network edges ignite between 0.36 and 0.50
  // Chapter 05 inferred link ignites at 0.75
  if (p < edge.ignitionScroll) return null;

  const ignitionWindow = 0.04;
  const drawProgress = clamp((p - edge.ignitionScroll) / ignitionWindow, 0, 1);
  if (drawProgress <= 0) return null;

  // Ignition flash at connection tip
  let flashAlpha: number | undefined;
  let flashRadius: number | undefined;
  if (drawProgress > 0.05 && drawProgress < 0.95) {
    const fPhase = (drawProgress - 0.05) / 0.90;
    flashRadius = 8 + fPhase * 30;
    flashAlpha = (1 - fPhase) * 0.7;
  }

  if (edge.isHiddenLink) {
    // ── INFERRED HIDDEN LINK (Chapter 05) ──
    const amberOpacity = drawProgress * 0.95;
    const pulsePos = ((p * 12) % 1);
    return {
      id: edge.id,
      sourceId: edge.a,
      targetId: edge.b,
      drawProgress,
      opacity: amberOpacity,
      lineWidth: 2.2,
      strokeStyle: 'rgba(245, 158, 11, ',
      isDashed: true,
      isSuspectChain: false,
      isHiddenLink: true,
      pulsePosition: pulsePos,
      pulseAlpha: 0.9,
      flashAlpha,
      flashRadius,
      label: edge.label,
    };
  }

  if (edge.stage === 'core' && edge.isSuspectChain) {
    // ── CORE SUSPECT CHAIN ──
    let opacity = drawProgress * 0.75;
    let lineWidth = 1.4;
    let strokeStyle = 'rgba(241, 241, 238, ';

    if (p >= 0.54 && p <= 0.72) {
      // Highlighted in Chapter 04 investigation
      opacity = 0.95;
      lineWidth = 2.4;
      strokeStyle = 'rgba(255, 255, 255, ';
    } else if (p > 0.72 && p <= 0.88) {
      // Maintained brightly during Chapter 05 noise reduction
      opacity = 0.88;
      lineWidth = 1.8;
    }

    const pulsePos = ((p * 8) % 1);
    return {
      id: edge.id,
      sourceId: edge.a,
      targetId: edge.b,
      drawProgress,
      opacity,
      lineWidth,
      strokeStyle,
      isDashed: false,
      isSuspectChain: true,
      isHiddenLink: false,
      pulsePosition: pulsePos,
      pulseAlpha: 0.8,
      flashAlpha,
      flashRadius,
      label: edge.label,
    };
  }

  // ── NETWORK BACKGROUND EDGES (Chapter 03+) ──
  let opacity = drawProgress * 0.28;
  if (p >= 0.54 && p <= 0.72) {
    opacity = 0.08; // Dimmed in Chapter 04 to emphasize trail
  } else if (p > 0.72 && p <= 0.88) {
    opacity = lerp(0.08, 0.02, noiseReduction); // Deep reduction in Chapter 05
  } else if (p > 0.88) {
    opacity = 0.24; // Restores in Chapter 06
  }

  return {
    id: edge.id,
    sourceId: edge.a,
    targetId: edge.b,
    drawProgress,
    opacity,
    lineWidth: 0.85,
    strokeStyle: 'rgba(160, 166, 178, ',
    isDashed: false,
    isSuspectChain: false,
    isHiddenLink: false,
    flashAlpha,
    flashRadius,
    label: edge.label,
  };
}

// ── SEQUENTIAL INVESTIGATION PULSE CALCULATION ──
function calculateInvestigationPulse(
  p: number,
  entityMap: Map<string, EntityVisualState>
): InvestigationPulseState {
  // Active only during Chapter 04: [0.54, 0.72]
  if (p < 0.54 || p > 0.72) {
    return {
      active: false,
      progress: 0,
      activeSegment: 0,
      headX: 0,
      headY: 0,
      headZ: 0,
      activeNodeId: '',
      stepLabel: '',
    };
  }

  // Investigation trail sequence:
  // Node 1: ent-phone
  // Node 2: ent-device-a83f
  // Node 3: ent-account-4821
  // Node 4: ent-account-72
  const p1 = entityMap.get('ent-phone');
  const p2 = entityMap.get('ent-device-a83f');
  const p3 = entityMap.get('ent-account-4821');
  const p4 = entityMap.get('ent-account-72');

  const trailProgress = clamp((p - 0.54) / 0.18, 0, 1);
  const segments = 3;
  const scaled = trailProgress * segments;
  const activeSegment = Math.min(Math.floor(scaled), segments - 1);
  const segProgress = scaled - activeSegment;

  let headX = 0, headY = 0, headZ = 0;
  let activeNodeId = 'ent-phone';
  let stepLabel = 'STEP 1: SIGNAL PING (09:42:13)';

  if (p1 && p2 && p3 && p4) {
    if (activeSegment === 0) {
      // Segment 1: Phone -> Device
      headX = lerp(p1.x, p2.x, segProgress);
      headY = lerp(p1.y, p2.y, segProgress);
      headZ = lerp(p1.z, p2.z, segProgress);
      activeNodeId = segProgress > 0.8 ? p2.id : p1.id;
      stepLabel = segProgress > 0.8 ? 'STEP 2: HARDWARE BIND' : 'STEP 1: FIRST SIGNAL';
    } else if (activeSegment === 1) {
      // Segment 2: Device -> Axis Bank
      headX = lerp(p2.x, p3.x, segProgress);
      headY = lerp(p2.y, p3.y, segProgress);
      headZ = lerp(p2.z, p3.z, segProgress);
      activeNodeId = segProgress > 0.8 ? p3.id : p2.id;
      stepLabel = segProgress > 0.8 ? 'STEP 3: MULE HUB' : 'STEP 2: HARDWARE BIND';
    } else {
      // Segment 3: Axis Bank -> Account 72
      headX = lerp(p3.x, p4.x, segProgress);
      headY = lerp(p3.y, p4.y, segProgress);
      headZ = lerp(p3.z, p4.z, segProgress);
      activeNodeId = segProgress > 0.8 ? p4.id : p3.id;
      stepLabel = segProgress > 0.8 ? 'STEP 4: EXFILTRATION TERMINUS' : 'STEP 3: MULE HUB';
    }
  }

  // Shockwave ring expanding at current segment arrival
  const ripplePhase = (segProgress * 3) % 1;
  const shockwaveRadius = 10 + ripplePhase * 35;
  const shockwaveAlpha = (1 - ripplePhase) * 0.85;

  return {
    active: true,
    progress: trailProgress,
    activeSegment,
    headX,
    headY,
    headZ,
    activeNodeId,
    stepLabel,
    shockwaveRadius,
    shockwaveAlpha,
  };
}
