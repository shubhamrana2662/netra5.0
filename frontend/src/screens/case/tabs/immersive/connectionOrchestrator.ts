import { SpatialFilament, SpatialNode } from './spatial3DTypes';
import { clamp, easeInOutCubic } from './spatialCameraEngine';

export interface OrchestrationState {
  time: number;
  selectedNodeId: string | null;
  showAiLinks: boolean;
  activePath: string[]; // Node IDs in investigation trail
  pathStep: number;     // Active hop index
}

/**
 * Updates all filaments according to progressive formation waves and interaction state.
 */
export function updateFilamentOrchestration(
  filaments: SpatialFilament[],
  nodes: Map<string, SpatialNode>,
  state: OrchestrationState
): void {
  const { time, selectedNodeId, showAiLinks, activePath, pathStep } = state;
  const isSelected = !!selectedNodeId;
  const selectedNeighbors = new Set<string>();

  if (selectedNodeId) {
    selectedNeighbors.add(selectedNodeId);
    filaments.forEach(f => {
      if (f.sourceId === selectedNodeId) selectedNeighbors.add(f.targetId);
      if (f.targetId === selectedNodeId) selectedNeighbors.add(f.sourceId);
    });
  }

  // Active path hop edge ID
  let activeHopSource = '';
  let activeHopTarget = '';
  if (activePath.length > 1) {
    const hopIdx = Math.min(activePath.length - 2, pathStep);
    activeHopSource = activePath[hopIdx];
    activeHopTarget = activePath[hopIdx + 1];
  }

  filaments.forEach(filament => {
    // 1. Inferred AI links only animate when showAiLinks is enabled
    if (filament.is_hidden && !showAiLinks) {
      filament.state = 'hidden';
      filament.drawProgress = 0.0;
      filament.opacity = 0.0;
      return;
    }

    // 2. Guaranteed immediate visibility: All relationships are visible on first frame
    const elapsedSeconds = time * 0.001;
    // Fast initial ignition over first 0.6 seconds, but with immediate visible floor of 0.65
    const waveProgress = time < 800
      ? clamp(0.65 + (time / 800) * 0.35, 0.65, 1.0)
      : 1.0;

    filament.state = 'stable';
    filament.drawProgress = waveProgress;

    // Ignition flash ring when line reaches destination
    if (waveProgress > 0.88 && waveProgress < 1.0) {
      const flashP = (waveProgress - 0.88) / 0.12;
      filament.flashRadius = 4 + flashP * 22;
      filament.flashAlpha = (1.0 - flashP) * 0.85;
    } else {
      filament.flashRadius = undefined;
      filament.flashAlpha = undefined;
    }

    // 3. Selection and Focus State
    const isDirectlyConnected = isSelected && (filament.sourceId === selectedNodeId || filament.targetId === selectedNodeId);
    const isNeighborRelation = isSelected && (selectedNeighbors.has(filament.sourceId) && selectedNeighbors.has(filament.targetId));
    const isHopEdge = (filament.sourceId === activeHopSource && filament.targetId === activeHopTarget) ||
                      (filament.sourceId === activeHopTarget && filament.targetId === activeHopSource);

    if (isHopEdge) {
      filament.state = 'focused';
      filament.lineWidth = 2.8;
      filament.opacity = 1.0;
      // High-speed energy pulse traveling along active hop
      filament.pulsePosition = (time * 0.0014) % 1.0;
    } else if (isDirectlyConnected) {
      filament.state = 'focused';
      filament.lineWidth = 2.2;
      filament.opacity = 0.95;
      filament.pulsePosition = (time * 0.0008 + filament.drawProgress) % 1.0;
    } else if (isSelected) {
      filament.state = isNeighborRelation ? 'stable' : 'dormant';
      filament.lineWidth = 0.8;
      filament.opacity = isNeighborRelation ? 0.35 : 0.04; // Deep dimming of unrelated network
      filament.pulsePosition = undefined;
    } else {
      // Normal living network state
      filament.state = waveProgress >= 1.0 ? 'stable' : 'connecting';
      filament.lineWidth = filament.is_hidden ? 2.0 : 1.5;
      filament.opacity = filament.is_hidden ? 0.85 : 0.65;

      // Subtle occasional traveling micro-pulse on high-confidence edges
      if (filament.conf >= 85 && waveProgress >= 1.0) {
        filament.pulsePosition = (time * 0.0004 + (filament.conf % 10) * 0.1) % 1.0;
      } else {
        filament.pulsePosition = undefined;
      }
    }
  });
}
