// ============================================================
//  Invariant Enforcement Utility
//  Hard assertions for runtime invariants. If an invariant
//  is violated, it throws in development and logs + no-ops
//  in production (to avoid crashing the cognitive runtime).
// ============================================================

const IS_DEV = import.meta.env.DEV;

/**
 * Assert a condition is true. Throws in dev, logs in prod.
 *
 * @example
 * invariant(node.lifecycle !== 'KILLED', 'Cannot promote KILLED node');
 */
export function invariant(
  condition: unknown,
  message: string
): asserts condition {
  if (!condition) {
    const error = new InvariantError(message);
    if (IS_DEV) {
      throw error;
    } else {
      console.error(`[INVARIANT VIOLATION] ${message}`, error.stack);
    }
  }
}

/**
 * Assert a value is defined (not null or undefined).
 *
 * @example
 * const node = assertDefined(nodeMap.get(id), `Node ${id} not found`);
 */
export function assertDefined<T>(
  value: T | null | undefined,
  message: string
): T {
  invariant(value !== null && value !== undefined, message);
  return value as T;
}

/**
 * Assert a lifecycle transition is valid.
 * These are hard invariants that MUST match backend rules.
 */
export function assertLegalTransition(
  from: string,
  to: string
): void {
  const LEGAL_TRANSITIONS: Record<string, string[]> = {
    LOOSE: ['FORMING'],
    FORMING: ['FROZEN', 'KILLED'],
    FROZEN: ['SUPERSEDED'],
    SUPERSEDED: [],
    KILLED: [],
  };

  const allowed = LEGAL_TRANSITIONS[from] ?? [];
  invariant(
    allowed.includes(to),
    `Illegal lifecycle transition: ${from} → ${to}. Allowed: [${allowed.join(', ') || 'none'}]`
  );
}

/**
 * Assert a normalized graph store has O(1) lookup consistency.
 * Use sparingly — only in debug/dev flows.
 */
export function assertGraphConsistency(
  nodes: Map<string, unknown>,
  edges: Map<string, unknown>,
  adjacency: Map<string, string[]>
): void {
  if (!IS_DEV) return;

  adjacency.forEach((edgeIds, nodeId) => {
    invariant(
      nodes.has(nodeId),
      `Adjacency map references node ${nodeId} which does not exist in entity store`
    );
    edgeIds.forEach((edgeId) => {
      invariant(
        edges.has(edgeId),
        `Adjacency map references edge ${edgeId} which does not exist in entity store`
      );
    });
  });
}

// ─── Custom Error Class ──────────────────────────────────────

class InvariantError extends Error {
  constructor(message: string) {
    super(`[JARVIS INVARIANT] ${message}`);
    this.name = 'InvariantError';
    // Maintains proper stack trace in V8 (Node/Chrome only)
    if ((Error as unknown as Record<string, unknown>)['captureStackTrace']) {
      (Error as unknown as { captureStackTrace: (t: object, c: object) => void }).captureStackTrace(this, InvariantError);
    }
  }
}
