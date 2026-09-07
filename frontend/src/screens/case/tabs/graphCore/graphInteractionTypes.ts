export type LayoutMode = 'force' | 'radial' | 'hierarchical' | 'clustered';

export type InteractionMode =
  | 'explore'
  | 'neighbor'
  | 'twoHop'
  | 'path'
  | 'cluster'
  | 'rearrange';

export type ViewMode = 'GRAPH' | 'IMMERSIVE' | 'FLOWS' | 'HIDDEN_LINKS';

export interface GraphFilters {
  kinds: Set<string> | null;
  minConf: number;
  minWeight: number;
  showHidden: boolean;
  aiThreshold: number;
}

export interface PathFindingResult {
  nodes: string[];
  edges: string[];
  minConfidence: number;
  hopCount: number;
  pathDescription: string;
}

export interface EdgeInspectData {
  id: string;
  source: string;
  target: string;
  sourceName: string;
  targetName: string;
  type: string;
  conf: number;
  reason?: string;
  evidenceIds?: string[];
  is_hidden?: boolean;
  score?: number;
  component_scores?: Record<string, number>;
  timestamps?: string[];
}

export interface GraphInteractionState {
  selectedNodeIds: Set<string>;
  hoveredNodeId: string | null;
  selectedEdgeId: string | null;
  hoveredEdgeId: string | null;
  focusedNodeId: string | null;

  activePath: string[] | null;
  activeHopDepth: number; // 0: all, 1: 1-hop, 2: 2-hop
  activeClusterId: number | null;

  activeFilters: GraphFilters;
  activeLayout: LayoutMode;
  interactionMode: InteractionMode;
  viewMode: ViewMode;

  expandedNodeIds: Set<string>;
  searchQuery: string;
}
