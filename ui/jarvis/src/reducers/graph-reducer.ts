// ============================================================
//  Graph Reducer — Deterministic Delta Processor
//  Receives typed graph events from the WebSocket delta
//  dispatcher and routes them to the graph entity store.
//  NEVER processes events out of order.
// ============================================================

import type {
  NodeCreateEvent,
  NodePatchEvent,
  NodeDeleteEvent,
  EdgeCreateEvent,
  EdgeDeleteEvent,
  GraphSnapshotEvent,
  InboundEvent,
  NodeData,
  EdgeData,
} from '../protocol/event-types';
import { useGraphStore } from '../state/graph-store';

// ─── Raw API → Protocol Adapters ─────────────────────────────
// The current backend API does not yet emit versioned event
// envelopes, so we adapt its raw HTTP response shapes to our
// normalized NodeData/EdgeData format here.

/**
 * Adapt a raw node from /jarvis/graph-index into NodeData.
 */
export function adaptRawNode(raw: Record<string, unknown>): NodeData {
  const id = (raw.id ?? raw.node_id ?? '') as string;
  const statement = (raw.statement ?? raw.label ?? raw.id ?? '') as string;
  const lifecycleRaw = ((raw.status ?? raw.lifecycle ?? 'LOOSE') as string).toUpperCase();

  // Normalize lifecycle values
  const lifecycle = (
    ['LOOSE', 'FORMING', 'FROZEN', 'SUPERSEDED', 'KILLED'].includes(lifecycleRaw)
      ? lifecycleRaw
      : 'LOOSE'
  ) as NodeData['lifecycle'];

  return {
    node_id: id,
    statement,
    lifecycle,
    confidence: typeof raw.confidence === 'number' ? raw.confidence : 0.5,
    source_count: typeof raw.source_count === 'number' ? raw.source_count : 0,
    updated_at: (raw.updated_at ?? raw.created_at ?? undefined) as string | undefined,
    created_at: (raw.created_at ?? undefined) as string | undefined,
    superseded_by: (raw.superseded_by ?? undefined) as string | undefined,
    metadata: (raw.metadata ?? {}) as Record<string, unknown>,
  };
}

/**
 * Adapt a raw edge from /jarvis/graph-index into EdgeData.
 */
export function adaptRawEdge(raw: Record<string, unknown>, index: number): EdgeData {
  const from = (raw.source ?? raw.from ?? '') as string;
  const to = (raw.target ?? raw.to ?? '') as string;
  const edgeType = (raw.type ?? raw.edge_type ?? 'RELATED_TO') as string;
  const edgeId = (raw.id ?? raw.edge_id ?? `${from}-${to}-${index}`) as string;

  return {
    edge_id: edgeId,
    from,
    to,
    type: edgeType.toUpperCase(),
    weight: typeof raw.weight === 'number' ? raw.weight : undefined,
  };
}

// ─── Graph Event Handlers ─────────────────────────────────────

export function handleNodeCreate(event: NodeCreateEvent): void {
  useGraphStore.getState().applyNodeCreate(event.payload);
  useGraphStore.getState().setLastSequence(event.sequence);
}

export function handleNodePatch(event: NodePatchEvent): void {
  useGraphStore.getState().applyNodePatch(event.payload);
  useGraphStore.getState().setLastSequence(event.sequence);
}

export function handleNodeDelete(event: NodeDeleteEvent): void {
  useGraphStore.getState().applyNodeDelete(event.payload.node_id);
  useGraphStore.getState().setLastSequence(event.sequence);
}

export function handleEdgeCreate(event: EdgeCreateEvent): void {
  useGraphStore.getState().applyEdgeCreate(event.payload);
  useGraphStore.getState().setLastSequence(event.sequence);
}

export function handleEdgeDelete(event: EdgeDeleteEvent): void {
  useGraphStore.getState().applyEdgeDelete(event.payload.edge_id);
  useGraphStore.getState().setLastSequence(event.sequence);
}

export function handleGraphSnapshot(event: GraphSnapshotEvent): void {
  const { nodes, edges } = event.payload;
  useGraphStore.getState().hydrateSnapshot(nodes, edges);
  useGraphStore.getState().setLastSequence(event.sequence);
}

/**
 * Hydrate from the current HTTP API response format.
 * Used at boot before WebSocket delta events are established.
 */
export function hydrateFromApiResponse(apiResponse: {
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}): void {
  const nodes = apiResponse.nodes.map(adaptRawNode);
  const edges = apiResponse.edges.map((e, i) => adaptRawEdge(e, i));
  useGraphStore.getState().hydrateSnapshot(nodes, edges);
}

// ─── Main Dispatch Router ─────────────────────────────────────

/**
 * Route any InboundEvent to the correct graph handler.
 * Called by the delta-dispatcher in the runtime layer.
 */
export function dispatchGraphEvent(event: InboundEvent): boolean {
  switch (event.type) {
    case 'NODE_CREATE':
      handleNodeCreate(event as NodeCreateEvent);
      return true;
    case 'NODE_PATCH':
      handleNodePatch(event as NodePatchEvent);
      return true;
    case 'NODE_DELETE':
      handleNodeDelete(event as NodeDeleteEvent);
      return true;
    case 'EDGE_CREATE':
      handleEdgeCreate(event as EdgeCreateEvent);
      return true;
    case 'EDGE_DELETE':
      handleEdgeDelete(event as EdgeDeleteEvent);
      return true;
    case 'GRAPH_SNAPSHOT':
      handleGraphSnapshot(event as GraphSnapshotEvent);
      return true;
    default:
      return false;
  }
}
