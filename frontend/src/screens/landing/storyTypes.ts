export type StoryChapterId =
  | 'problem'
  | 'correlation'
  | 'graph'
  | 'evidence'
  | 'patterns'
  | 'resolution';

export interface StoryChapter {
  id: StoryChapterId;
  index: number;
  label: string;
  name: string;
  start: number;
  end: number;
}

export interface CameraState {
  x: number;
  y: number;
  z: number;
  yaw: number;
  pitch: number;
}

export interface EntityVisualState {
  id: string;
  label: string;
  subtext?: string;
  kind: 'PHONE' | 'UPI' | 'DEVICE' | 'ACCOUNT' | 'IP' | 'FILE' | 'PERSON' | 'BANK' | 'SIGNAL';
  cluster: number;
  // 3D coordinates in space
  x: number;
  y: number;
  z: number;
  opacity: number;
  scale: number;
  isBridge?: boolean;
  isSuspectChain?: boolean;
  isHighlighted?: boolean;
  pingRadius?: number;
  pingAlpha?: number;
}

export interface EdgeVisualState {
  id: string;
  sourceId: string;
  targetId: string;
  drawProgress: number; // 0 to 1
  opacity: number;
  lineWidth: number;
  strokeStyle: string;
  isDashed: boolean;
  isSuspectChain: boolean;
  isHiddenLink: boolean;
  flashAlpha?: number;
  flashRadius?: number;
  pulsePosition?: number; // 0 to 1 along edge
  pulseAlpha?: number;
  label?: string;
}

export interface InvestigationPulseState {
  active: boolean;
  progress: number; // 0 to 1 across the whole investigation trail
  activeSegment: number; // 0 to 3
  headX: number;
  headY: number;
  headZ: number;
  activeNodeId: string;
  stepLabel: string;
  shockwaveRadius?: number;
  shockwaveAlpha?: number;
}

export interface SceneState {
  storyProgress: number;
  activeChapter: StoryChapter;
  localProgress: number;
  camera: CameraState;
  entities: EntityVisualState[];
  edges: EdgeVisualState[];
  investigationPulse: InvestigationPulseState;
  bridgeEmphasis: number; // 0 to 1
  hiddenLinkProgress: number; // 0 to 1
  noiseReduction: number; // 0 (full noise) to 1 (pure focus)
  planarAlignment: number; // 0 (3D scattered) to 1 (flat 2D aligned)
  backgroundDensity: number;
  interfaceFramingAlpha: number; // 0 to 1 in Chapter 6
}
