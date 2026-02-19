// ============================================================
//  JARVIS UI Governance Validators
//  Reads ui_rules.json at runtime and enforces lifecycle
//  transition rules BEFORE any API call is dispatched.
//  This makes the frontend policy-aware and prevents illegal
//  state transitions from ever reaching the backend.
// ============================================================

import type { Lifecycle } from './event-types';

// ─── Types mirroring ui_rules.json schema ────────────────────

export type NodeAction = 'promote' | 'kill' | 'supersede';

interface TransitionGuard {
  guard_id: string;
  description: string;
  condition: {
    current_lifecycle?: Lifecycle;
    attempted_action?: NodeAction;
    new_node_id?: null;
  };
  effect: {
    block: boolean;
    error_message: string;
  };
}

interface LifecycleRule {
  allowed_next: Lifecycle[];
  forbidden_next: Lifecycle[];
  ui_display: {
    color: string;
    immutable: boolean;
    badge?: string;
    show_promote_button: boolean;
    show_kill_button: boolean;
    show_supersede_button?: boolean;
    opacity?: number;
    grayscale?: boolean;
  };
}

interface UIRules {
  version: string;
  lifecycle_transitions: Record<Lifecycle, LifecycleRule>;
  mutation_guards: TransitionGuard[];
  audit_requirements: {
    always_log_actor: boolean;
    require_reason_for: NodeAction[];
    min_reason_length: number;
  };
}

// ─── Validation Result ───────────────────────────────────────

export interface ValidationResult {
  allowed: boolean;
  error?: string;
  guard_id?: string;
}

// ─── Load rules (cached singleton) ───────────────────────────

let _rules: UIRules | null = null;

async function loadRules(): Promise<UIRules> {
  if (_rules) return _rules;
  try {
    const res = await fetch('/ui_rules.json');
    if (!res.ok) throw new Error('Failed to load ui_rules.json');
    _rules = await res.json();
    return _rules!;
  } catch (e) {
    console.warn('[JARVIS] ui_rules.json not found, using built-in defaults');
    _rules = BUILT_IN_DEFAULTS;
    return _rules;
  }
}

// ─── Main Validator ──────────────────────────────────────────

/**
 * Validate a lifecycle mutation BEFORE dispatching to API.
 * Returns { allowed: true } if the action is permitted.
 * Returns { allowed: false, error: string } if blocked by policy.
 */
export async function validateMutation(
  currentLifecycle: Lifecycle,
  action: NodeAction,
  data?: { new_node_id?: string; reason?: string }
): Promise<ValidationResult> {
  const rules = await loadRules();

  // Check all mutation guards
  for (const guard of rules.mutation_guards) {
    const { condition, effect } = guard;

    const lifecycleMatch =
      !condition.current_lifecycle ||
      condition.current_lifecycle === currentLifecycle;

    const actionMatch =
      !condition.attempted_action ||
      condition.attempted_action === action;

    const newNodeIdNull =
      condition.new_node_id === null
        ? !data?.new_node_id
        : true;

    if (lifecycleMatch && actionMatch && newNodeIdNull) {
      if (effect.block) {
        return {
          allowed: false,
          error: effect.error_message,
          guard_id: guard.guard_id,
        };
      }
    }
  }

  // Check audit requirements
  const auditReqs = rules.audit_requirements;
  if (auditReqs.require_reason_for.includes(action)) {
    const reason = data?.reason?.trim() ?? '';
    if (reason.length < auditReqs.min_reason_length) {
      return {
        allowed: false,
        error: `A reason of at least ${auditReqs.min_reason_length} characters is required for "${action}".`,
        guard_id: 'audit-reason-required',
      };
    }
  }

  return { allowed: true };
}

/**
 * Synchronous version using cached rules only.
 * Use this when async is not possible (e.g., render-time guards).
 */
export function validateMutationSync(
  currentLifecycle: Lifecycle,
  action: NodeAction,
  data?: { new_node_id?: string; reason?: string }
): ValidationResult {
  const rules = _rules ?? BUILT_IN_DEFAULTS;

  for (const guard of rules.mutation_guards) {
    const { condition, effect } = guard;

    const lifecycleMatch =
      !condition.current_lifecycle ||
      condition.current_lifecycle === currentLifecycle;

    const actionMatch =
      !condition.attempted_action ||
      condition.attempted_action === action;

    const newNodeIdNull =
      condition.new_node_id === null
        ? !data?.new_node_id
        : true;

    if (lifecycleMatch && actionMatch && newNodeIdNull) {
      if (effect.block) {
        return {
          allowed: false,
          error: effect.error_message,
          guard_id: guard.guard_id,
        };
      }
    }
  }

  const auditReqs = rules.audit_requirements;
  if (auditReqs.require_reason_for.includes(action)) {
    const reason = data?.reason?.trim() ?? '';
    if (reason.length < auditReqs.min_reason_length) {
      return {
        allowed: false,
        error: `A reason of at least ${auditReqs.min_reason_length} characters is required for "${action}".`,
        guard_id: 'audit-reason-required',
      };
    }
  }

  return { allowed: true };
}

/**
 * Get the UI display config for a given lifecycle state.
 */
export async function getLifecycleDisplay(lifecycle: Lifecycle) {
  const rules = await loadRules();
  return rules.lifecycle_transitions[lifecycle]?.ui_display ?? null;
}

/**
 * Pre-load rules into cache. Call this at app boot.
 */
export function preloadRules(): Promise<UIRules> {
  return loadRules();
}

// ─── Built-in fallback defaults ──────────────────────────────
// Used if ui_rules.json cannot be fetched.

const BUILT_IN_DEFAULTS: UIRules = {
  version: '1.0.0',
  lifecycle_transitions: {
    LOOSE: {
      allowed_next: ['FORMING'],
      forbidden_next: ['FROZEN', 'SUPERSEDED', 'KILLED'],
      ui_display: {
        color: 'cyan',
        immutable: false,
        show_promote_button: true,
        show_kill_button: true,
      },
    },
    FORMING: {
      allowed_next: ['FROZEN', 'KILLED'],
      forbidden_next: ['LOOSE', 'SUPERSEDED'],
      ui_display: {
        color: 'amber',
        immutable: false,
        show_promote_button: true,
        show_kill_button: true,
      },
    },
    FROZEN: {
      allowed_next: ['SUPERSEDED'],
      forbidden_next: ['LOOSE', 'FORMING', 'KILLED'],
      ui_display: {
        color: 'emerald',
        immutable: true,
        badge: 'IMMUTABLE',
        show_promote_button: false,
        show_kill_button: false,
        show_supersede_button: true,
      },
    },
    SUPERSEDED: {
      allowed_next: [],
      forbidden_next: ['LOOSE', 'FORMING', 'FROZEN', 'KILLED'],
      ui_display: {
        color: 'indigo',
        immutable: true,
        badge: 'SUPERSEDED',
        show_promote_button: false,
        show_kill_button: false,
        opacity: 0.5,
      },
    },
    KILLED: {
      allowed_next: [],
      forbidden_next: ['LOOSE', 'FORMING', 'FROZEN', 'SUPERSEDED'],
      ui_display: {
        color: 'red',
        immutable: true,
        badge: 'TERMINATED',
        show_promote_button: false,
        show_kill_button: false,
        grayscale: true,
      },
    },
  },
  mutation_guards: [
    {
      guard_id: 'no-kill-frozen',
      description: 'FROZEN nodes cannot be directly killed',
      condition: { current_lifecycle: 'FROZEN', attempted_action: 'kill' },
      effect: {
        block: true,
        error_message: 'FROZEN nodes must be SUPERSEDED before termination.',
      },
    },
    {
      guard_id: 'no-promote-killed',
      description: 'KILLED nodes cannot be promoted',
      condition: { current_lifecycle: 'KILLED', attempted_action: 'promote' },
      effect: { block: true, error_message: 'Terminated nodes cannot be promoted.' },
    },
    {
      guard_id: 'no-promote-superseded',
      description: 'SUPERSEDED nodes cannot be promoted',
      condition: {
        current_lifecycle: 'SUPERSEDED',
        attempted_action: 'promote',
      },
      effect: { block: true, error_message: 'Superseded nodes are immutable.' },
    },
    {
      guard_id: 'supersede-requires-new-node',
      description: 'Supersede action requires a valid new_node_id',
      condition: { attempted_action: 'supersede', new_node_id: null },
      effect: {
        block: true,
        error_message: 'Must specify a replacement node ID.',
      },
    },
  ],
  audit_requirements: {
    always_log_actor: true,
    require_reason_for: ['kill', 'supersede'],
    min_reason_length: 10,
  },
};
