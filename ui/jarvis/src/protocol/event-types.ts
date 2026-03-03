// ============================================================
//  JARVIS Graph Delta Protocol — Event Type Definitions
//  All WebSocket events between Cortex (backend) and UI must
//  use these typed envelopes. Sequence numbers enable gap
//  detection and delta-resync.
// ============================================================

export type Lifecycle =
  | 'LOOSE'
  | 'FORMING'
  | 'FROZEN'
  | 'SUPERSEDED'
  | 'KILLED';

export type SystemStatus = 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'LOCK_RISK';
export type CognitivePhase = 'IDLE' | 'SYNCING' | 'COMPILING' | 'SYNTHESIZING' | 'STREAMING';

// ─── Node / Edge Payloads ────────────────────────────────────

export interface NodeData {
  node_id: string;
  statement: string;
  lifecycle: Lifecycle;
  confidence: number;
  source_count?: number;
  updated_at?: string;
  created_at?: string;
  superseded_by?: string;
  actor?: string;
  metadata?: Record<string, unknown>;
}

export interface EdgeData {
  edge_id: string;
  from: string;
  to: string;
  type: 'DERIVED_FROM' | 'SUPERSEDES' | 'OVERRIDES' | 'RELATED_TO' | string;
  weight?: number;
  metadata?: Record<string, unknown>;
}

// ─── Event Envelope ──────────────────────────────────────────

export interface EventEnvelope<T = unknown> {
  event_id: string;
  sequence: number;
  timestamp: number; // Unix ms
  type: GraphEventType | SystemEventType | StreamEventType;
  payload: T;
}

// ─── Graph Events ─────────────────────────────────────────────

export type GraphEventType =
  | 'NODE_CREATE'
  | 'NODE_PATCH'
  | 'NODE_DELETE'
  | 'EDGE_CREATE'
  | 'EDGE_DELETE'
  | 'GRAPH_SNAPSHOT'
  | 'REQUEST_DELTA_SYNC';

export interface NodeCreateEvent extends EventEnvelope<NodeData> {
  type: 'NODE_CREATE';
}

export interface NodePatchEvent
  extends EventEnvelope<Partial<NodeData> & { node_id: string }> {
  type: 'NODE_PATCH';
}

export interface NodeDeleteEvent
  extends EventEnvelope<{ node_id: string; reason?: string }> {
  type: 'NODE_DELETE';
}

export interface EdgeCreateEvent extends EventEnvelope<EdgeData> {
  type: 'EDGE_CREATE';
}

export interface EdgeDeleteEvent
  extends EventEnvelope<{ edge_id: string }> {
  type: 'EDGE_DELETE';
}

export interface GraphSnapshotEvent
  extends EventEnvelope<{ nodes: NodeData[]; edges: EdgeData[] }> {
  type: 'GRAPH_SNAPSHOT';
}

export interface RequestDeltaSyncEvent
  extends EventEnvelope<{ last_sequence: number }> {
  type: 'REQUEST_DELTA_SYNC';
}

// ─── System Events ────────────────────────────────────────────

export type SystemEventType = 'SYSTEM_HEALTH' | 'COGNITIVE_PHASE';

export interface SystemHealthEvent
  extends EventEnvelope<{
    sync: SystemStatus;
    llm: SystemStatus;
    db: SystemStatus;
    celery_workers: number;
    last_sync: string;
  }> {
  type: 'SYSTEM_HEALTH';
}

export interface CognitivePhaseEvent
  extends EventEnvelope<{ phase: CognitivePhase; topic_id?: string }> {
  type: 'COGNITIVE_PHASE';
}

// ─── Stream Events ────────────────────────────────────────────

export type StreamEventType = 'AUDIT_EVENT' | 'TOKEN_STREAM';

export interface AuditEventPayload {
  timestamp: string;
  event: string;
  component: string;
  agent: string;
  topic_id?: string;
  run_id?: string;
  model_tier?: string;
  cost?: { usd: number; tokens_in: number; tokens_out: number };
  decision: { action: string; reason: string };
  metadata?: Record<string, unknown>;
}

export interface AuditStreamEvent extends EventEnvelope<AuditEventPayload> {
  type: 'AUDIT_EVENT';
}

// ─── Union type for all inbound events ───────────────────────

export type InboundEvent =
  | NodeCreateEvent
  | NodePatchEvent
  | NodeDeleteEvent
  | EdgeCreateEvent
  | EdgeDeleteEvent
  | GraphSnapshotEvent
  | SystemHealthEvent
  | CognitivePhaseEvent
  | AuditStreamEvent;
