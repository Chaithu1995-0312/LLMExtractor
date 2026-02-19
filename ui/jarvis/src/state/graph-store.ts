// ============================================================
//  Graph Entity Store (Structural Bits — Plane 3)
//  Normalized O(1) entity store for nodes, edges, and
//  adjacency. NEVER replace full graph — delta-patch only.
//  All lifecycle transitions are validated before mutating.
// ============================================================

import { create } from 'zustand';
import type { NodeData, EdgeData, Lifecycle } from '../protocol/event-types';
import { assertLegalTransition } from '../utils/invariant';

// ─── Normalized Graph State ───────────────────────────────────

export interface GraphState {
  // O(1) node/edge lookup
  nodes: Record<string, NodeData>;
  edges: Record<string, EdgeData>;
  // Adjacency: nodeId → [edgeIds]
  adjacency: Record<string, string[]>;

  // Sequence tracking for delta-sync
  lastSequence: number;

  // ─── Actions ─────────────────────────────────────────────

  /** Bootstrap from initial HTTP snapshot */
  hydrateSnapshot: (nodes: NodeData[], edges: EdgeData[]) => void;

  /** Apply a NODE_CREATE delta */
  applyNodeCreate: (node: NodeData) => void;

  /** Apply a NODE_PATCH delta (only changed fields) */
  applyNodePatch: (patch: Partial<NodeData> & { node_id: string }) => void;

  /** Apply a NODE_DELETE delta */
  applyNodeDelete: (node_id: string) => void;

  /** Apply an EDGE_CREATE delta */
  applyEdgeCreate: (edge: EdgeData) => void;

  /** Apply an EDGE_DELETE delta */
  applyEdgeDelete: (edge_id: string) => void;

  /** Update sequence counter */
  setLastSequence: (seq: number) => void;

  // ─── Selectors (memoizable outside store) ────────────────

  /** Get a single node by ID */
  getNode: (id: string) => NodeData | undefined;

  /** Get nodes filtered by lifecycle */
  getNodesByLifecycle: (lifecycle: Lifecycle) => NodeData[];

  /** Get edges for a node */
  getNodeEdges: (nodeId: string) => EdgeData[];
}

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: {},
  edges: {},
  adjacency: {},
  lastSequence: -1,

  hydrateSnapshot(rawNodes, rawEdges) {
    const nodes: Record<string, NodeData> = {};
    const edges: Record<string, EdgeData> = {};
    const adjacency: Record<string, string[]> = {};

    for (const n of rawNodes) {
      nodes[n.node_id] = n;
      adjacency[n.node_id] = adjacency[n.node_id] ?? [];
    }

    for (const e of rawEdges) {
      edges[e.edge_id] = e;
      // Build adjacency in both directions
      if (!adjacency[e.from]) adjacency[e.from] = [];
      adjacency[e.from].push(e.edge_id);
      if (!adjacency[e.to]) adjacency[e.to] = [];
      adjacency[e.to].push(e.edge_id);
    }

    set({ nodes, edges, adjacency });
  },

  applyNodeCreate(node) {
    set((state) => ({
      nodes: { ...state.nodes, [node.node_id]: node },
      adjacency: {
        ...state.adjacency,
        [node.node_id]: state.adjacency[node.node_id] ?? [],
      },
    }));
  },

  applyNodePatch(patch) {
    set((state) => {
      const existing = state.nodes[patch.node_id];
      if (!existing) {
        console.warn(`[GraphStore] NODE_PATCH for unknown node ${patch.node_id}`);
        return state;
      }

      // Validate lifecycle transition if lifecycle is changing
      if (patch.lifecycle && patch.lifecycle !== existing.lifecycle) {
        try {
          assertLegalTransition(existing.lifecycle, patch.lifecycle);
        } catch (e) {
          console.error('[GraphStore] Blocked illegal lifecycle transition:', e);
          return state; // Reject the patch
        }
      }

      return {
        nodes: {
          ...state.nodes,
          [patch.node_id]: { ...existing, ...patch },
        },
      };
    });
  },

  applyNodeDelete(node_id) {
    set((state) => {
      const { [node_id]: _removed, ...remainingNodes } = state.nodes;
      const { [node_id]: _removedAdj, ...remainingAdj } = state.adjacency;

      // Clean up edges connected to this node
      const affectedEdges = state.adjacency[node_id] ?? [];
      const remainingEdges = { ...state.edges };
      for (const edgeId of affectedEdges) {
        delete remainingEdges[edgeId];
      }

      return {
        nodes: remainingNodes,
        edges: remainingEdges,
        adjacency: remainingAdj,
      };
    });
  },

  applyEdgeCreate(edge) {
    set((state) => {
      const newAdjacency = { ...state.adjacency };
      if (!newAdjacency[edge.from]) newAdjacency[edge.from] = [];
      if (!newAdjacency[edge.to]) newAdjacency[edge.to] = [];
      newAdjacency[edge.from] = [...newAdjacency[edge.from], edge.edge_id];
      newAdjacency[edge.to] = [...newAdjacency[edge.to], edge.edge_id];

      return {
        edges: { ...state.edges, [edge.edge_id]: edge },
        adjacency: newAdjacency,
      };
    });
  },

  applyEdgeDelete(edge_id) {
    set((state) => {
      const edge = state.edges[edge_id];
      if (!edge) return state;

      const { [edge_id]: _removed, ...remainingEdges } = state.edges;
      const newAdjacency = { ...state.adjacency };

      if (newAdjacency[edge.from]) {
        newAdjacency[edge.from] = newAdjacency[edge.from].filter((id) => id !== edge_id);
      }
      if (newAdjacency[edge.to]) {
        newAdjacency[edge.to] = newAdjacency[edge.to].filter((id) => id !== edge_id);
      }

      return { edges: remainingEdges, adjacency: newAdjacency };
    });
  },

  setLastSequence(seq) {
    set({ lastSequence: seq });
  },

  getNode(id) {
    return get().nodes[id];
  },

  getNodesByLifecycle(lifecycle) {
    return Object.values(get().nodes).filter((n) => n.lifecycle === lifecycle);
  },

  getNodeEdges(nodeId) {
    const state = get();
    const edgeIds = state.adjacency[nodeId] ?? [];
    return edgeIds.map((id) => state.edges[id]).filter(Boolean);
  },
}));
