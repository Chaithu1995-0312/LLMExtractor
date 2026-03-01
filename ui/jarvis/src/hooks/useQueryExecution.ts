/**
 * useQueryExecution.ts
 * =====================
 * Hook that wraps POST /api/v2/query and populates the controlPlaneStore.
 *
 * Invariants:
 * - Never modifies confidence values.
 * - Never derives routing logic.
 * - Only responsibility: fetch → store → done.
 */

import { useControlPlaneStore } from '../store/controlPlaneStore';
import { OverrideFlags, QueryExecutionPayload } from '../types/controlPlane';

export const useQueryExecution = () => {
  const { setLoading, setResult, setError, overrides } = useControlPlaneStore();

  const execute = async (
    query: string,
    overrideOverride?: OverrideFlags,
  ): Promise<void> => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);

    // Build the override payload — only send keys that are actually set
    const activeOverrides: OverrideFlags = overrideOverride ?? overrides;
    const body: { query: string; overrides?: OverrideFlags } = { query: trimmed };

    const overridePayload: OverrideFlags = {};
    if (activeOverrides.force_route) {
      overridePayload.force_route = activeOverrides.force_route;
    }
    if (activeOverrides.disable_escalation === true) {
      overridePayload.disable_escalation = true;
    }
    if (
      typeof activeOverrides.threshold_override === 'number' &&
      activeOverrides.threshold_override > 0
    ) {
      overridePayload.threshold_override = activeOverrides.threshold_override;
    }

    if (Object.keys(overridePayload).length > 0) {
      body.overrides = overridePayload;
    }

    try {
      const res = await fetch('/api/v2/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data: QueryExecutionPayload = await res.json();

      if (!res.ok) {
        const msg =
          (data as unknown as { error?: string; message?: string }).error ||
          (data as unknown as { message?: string }).message ||
          `HTTP ${res.status}`;
        setError(msg);
        return;
      }

      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Network error — is the Cortex server running?';
      setError(message);
    }
  };

  return { execute };
};
