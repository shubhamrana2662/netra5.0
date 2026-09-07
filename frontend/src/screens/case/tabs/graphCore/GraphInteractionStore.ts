import { useState, useEffect } from 'react';
import {
  GraphInteractionState,
  GraphFilters,
  LayoutMode,
  InteractionMode,
  ViewMode,
} from './graphInteractionTypes';

type StateListener = (state: GraphInteractionState) => void;

class GraphInteractionController {
  private state: GraphInteractionState = {
    selectedNodeIds: new Set<string>(),
    hoveredNodeId: null,
    selectedEdgeId: null,
    hoveredEdgeId: null,
    focusedNodeId: null,
    activePath: null,
    activeHopDepth: 0,
    activeClusterId: null,
    activeFilters: {
      kinds: null,
      minConf: 0,
      minWeight: 0,
      showHidden: false,
      aiThreshold: 35,
    },
    activeLayout: 'force',
    interactionMode: 'explore',
    viewMode: 'GRAPH',
    expandedNodeIds: new Set<string>(),
    searchQuery: '',
  };

  private listeners = new Set<StateListener>();

  getState(): GraphInteractionState {
    return this.state;
  }

  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach(fn => fn({ ...this.state }));
  }

  selectNode(id: string | null, isMulti = false) {
    if (!id) {
      this.state.selectedNodeIds.clear();
      this.state.focusedNodeId = null;
      this.state.interactionMode = 'explore';
    } else if (isMulti) {
      if (this.state.selectedNodeIds.has(id)) {
        this.state.selectedNodeIds.delete(id);
      } else {
        this.state.selectedNodeIds.add(id);
      }
      this.state.focusedNodeId = id;
    } else {
      this.state.selectedNodeIds = new Set([id]);
      this.state.focusedNodeId = id;
    }
    this.state.selectedEdgeId = null;
    this.notify();
  }

  hoverNode(id: string | null) {
    if (this.state.hoveredNodeId !== id) {
      this.state.hoveredNodeId = id;
      this.notify();
    }
  }

  selectEdge(id: string | null) {
    this.state.selectedEdgeId = id;
    if (id) {
      this.state.selectedNodeIds.clear();
      this.state.focusedNodeId = null;
    }
    this.notify();
  }

  hoverEdge(id: string | null) {
    if (this.state.hoveredEdgeId !== id) {
      this.state.hoveredEdgeId = id;
      this.notify();
    }
  }

  expandNeighborhood(nodeId: string, hops: number) {
    this.state.selectedNodeIds = new Set([nodeId]);
    this.state.focusedNodeId = nodeId;
    this.state.activeHopDepth = hops;
    this.state.interactionMode = hops === 1 ? 'neighbor' : hops === 2 ? 'twoHop' : 'explore';
    this.notify();
  }

  setPath(pathNodes: string[] | null) {
    this.state.activePath = pathNodes;
    this.state.interactionMode = pathNodes && pathNodes.length > 0 ? 'path' : 'explore';
    this.notify();
  }

  focusCluster(clusterId: number | null) {
    this.state.activeClusterId = clusterId;
    this.state.interactionMode = clusterId !== null ? 'cluster' : 'explore';
    this.notify();
  }

  setFilters(partial: Partial<GraphFilters>) {
    this.state.activeFilters = {
      ...this.state.activeFilters,
      ...partial,
    };
    this.notify();
  }

  setLayout(layout: LayoutMode) {
    this.state.activeLayout = layout;
    this.notify();
  }

  setViewMode(mode: ViewMode) {
    this.state.viewMode = mode;
    this.notify();
  }

  setSearchQuery(q: string) {
    this.state.searchQuery = q;
    this.notify();
  }

  clearSelection() {
    this.state.selectedNodeIds.clear();
    this.state.focusedNodeId = null;
    this.state.selectedEdgeId = null;
    this.state.activePath = null;
    this.state.activeHopDepth = 0;
    this.state.activeClusterId = null;
    this.state.interactionMode = 'explore';
    this.notify();
  }
}

export const graphInteractionStore = new GraphInteractionController();

/**
 * React hook for consuming and subscribing to the shared graph interaction controller.
 */
export function useGraphInteraction() {
  const [state, setState] = useState<GraphInteractionState>(() => graphInteractionStore.getState());

  useEffect(() => {
    return graphInteractionStore.subscribe(nextState => {
      setState(nextState);
    });
  }, []);

  return {
    state,
    selectNode: (id: string | null, isMulti = false) => graphInteractionStore.selectNode(id, isMulti),
    hoverNode: (id: string | null) => graphInteractionStore.hoverNode(id),
    selectEdge: (id: string | null) => graphInteractionStore.selectEdge(id),
    hoverEdge: (id: string | null) => graphInteractionStore.hoverEdge(id),
    expandNeighborhood: (nodeId: string, hops: number) => graphInteractionStore.expandNeighborhood(nodeId, hops),
    setPath: (pathNodes: string[] | null) => graphInteractionStore.setPath(pathNodes),
    focusCluster: (clusterId: number | null) => graphInteractionStore.focusCluster(clusterId),
    setFilters: (partial: Partial<GraphFilters>) => graphInteractionStore.setFilters(partial),
    setLayout: (layout: LayoutMode) => graphInteractionStore.setLayout(layout),
    setViewMode: (mode: ViewMode) => graphInteractionStore.setViewMode(mode),
    setSearchQuery: (q: string) => graphInteractionStore.setSearchQuery(q),
    clearSelection: () => graphInteractionStore.clearSelection(),
  };
}
