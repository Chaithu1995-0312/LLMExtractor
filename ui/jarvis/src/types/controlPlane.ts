/**
 * controlPlane.ts
 * ================
 * TypeScript contract for the v2 Cognitive Control Plane execution payload.
 * This is the canonical type for all data returned by POST /api/v2/query.
 *
 * UI components MUST NOT infer or derive data — they render these types only.
 */

// ── Confidence ────────────────────────────────────────────────────────────────

export interface ConfidenceComponents {
  M: number; // Top score (cosine similarity)
  S: number; // Score margin (ambiguity)
  E: number; // Embedding alignment
  C: number; // Coverage ratio
}

export interface ConfidenceResult {
  final: number;
  threshold: number;
  components: ConfidenceComponents;
  gate_pass: boolean;
  block_reason: string | null;
  diagnostics: Record<string, unknown>;
}

// ── Routing ───────────────────────────────────────────────────────────────────

export type RouteIntent = 'governance' | 'diagnostic' | 'memory' | 'strategic' | 'factual';
export type RouteSelected = 'graph' | 'memory' | 'hybrid';

export interface RouteDecision {
  intent: RouteIntent;
  selected: RouteSelected;
  hybrid_used: boolean;
  overridden: boolean;
  force_escalate: boolean;
}

// ── Retrieval ─────────────────────────────────────────────────────────────────

export interface GraphResult {
  id: string;
  type: string;
  statement: string;
  lifecycle: string;
  confidence: number;
  final_score: number;
  vector_score: number;
  metadata: Record<string, unknown>;
}

export interface GraphRetrieval {
  results: GraphResult[];
  top_score: number;
  result_count: number;
  error?: string;
}

export interface MemoryChunk {
  chunk_id: string;
  text: string;
  score: number;
  metadata: {
    dataset_id?: string;
    conversation_id?: string;
    role?: string;
    timestamp?: string;
    [key: string]: unknown;
  };
}

export interface MemoryRetrieval {
  chunks: MemoryChunk[];
  retrieval_metadata: {
    top_score?: number;
    chunk_count?: number;
    [key: string]: unknown;
  };
  top_score: number;
  chunk_count: number;
  error?: string;
}

export interface RetrievalState {
  graph: GraphRetrieval | null;
  memory: MemoryRetrieval | null;
}

// ── Hybrid Conflict ───────────────────────────────────────────────────────────

export interface HybridConflict {
  detected: boolean;
  delta: number;
  graph_conf: number;
  memory_conf: number;
  dominant?: RouteSelected;
  recommendation?: string | null;
}

// ── Escalation ────────────────────────────────────────────────────────────────

export interface EscalationResult {
  triggered: boolean;
  tier: number | null;
  model: string | null;
  advisory: string | null;
  error?: string;
}

// ── Timeline ─────────────────────────────────────────────────────────────────

export type TimelineStatus = 'complete' | 'failed' | 'warn' | 'blocked';

export interface TimelineStep {
  step: string;
  status: TimelineStatus;
  detail?: string;
}

// ── System State ──────────────────────────────────────────────────────────────

export type HealthStatus = 'healthy' | 'empty' | 'unavailable' | 'unknown' | 'warn' | 'fail';

export interface SystemState {
  graph_index: HealthStatus;
  memory_index: HealthStatus;
  memory_vector_count: number;
  embedding_model: string;
  budget_pressure: string;
  last_health_check: string;
  graph_node_count?: number;
}

// ── Response ─────────────────────────────────────────────────────────────────

export type ResponseStatus = 'success' | 'blocked' | 'no_content' | 'failed';
export type ResponseSource = 'graph' | 'memory' | 'hybrid' | 'l3' | null;

export interface QueryResponse {
  answer: string | null;
  source: ResponseSource;
  confidence: number;
  status: ResponseStatus;
  block_reason: string | null;
  fragments?: string[];
}

// ── Full Execution Payload ────────────────────────────────────────────────────

export interface QueryExecutionPayload {
  query_id: string;
  query: string;
  elapsed_ms: number;
  route: RouteDecision;
  retrieval: RetrievalState;
  confidence: ConfidenceResult;
  hybrid_conflict: HybridConflict;
  escalation: EscalationResult;
  timeline: TimelineStep[];
  system_state: SystemState;
  response: QueryResponse;
}

// ── Override Flags ────────────────────────────────────────────────────────────

export interface OverrideFlags {
  force_route?: RouteSelected | '';
  disable_escalation?: boolean;
  threshold_override?: number;
}

// ── Store Shape ───────────────────────────────────────────────────────────────

export interface ControlPlaneState {
  query: string;
  loading: boolean;
  result: QueryExecutionPayload | null;
  error: string | null;
  overrides: OverrideFlags;
  advancedOpen: boolean;
}
