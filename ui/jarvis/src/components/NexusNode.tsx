import React from "react";

export type Lifecycle =
  | "LOOSE"
  | "FORMING"
  | "FROZEN"
  | "KILLED";

export interface NexusNodeProps {
  id: string;
  title: string;
  summary: string;              // ≤ 2 lines (enforced by CSS)
  lifecycle: Lifecycle;
  confidence: number;           // 0 → 1
  sourceCount: number;
  lastUpdatedAt: string;        // ISO or preformatted
  isFocused: boolean;
  onSelect: (id: string) => void;
}

export const NexusNode: React.FC<NexusNodeProps> = ({
  id,
  title,
  summary,
  lifecycle,
  confidence,
  sourceCount,
  lastUpdatedAt,
  isFocused,
  onSelect,
}) => {
  return (
    <div
      className={`nexus-brick lifecycle-${lifecycle.toLowerCase()} ${
        isFocused ? "focused" : ""
      }`}
      onClick={() => onSelect(id)}
      role="button"
      aria-selected={isFocused}
    >
      {/* Header */}
      <div className="brick-header">
        <span className="brick-title">{title}</span>
        <span
          className={`brick-lifecycle-dot ${lifecycle.toLowerCase()}`}
          title={lifecycle}
        />
      </div>

      {/* Summary */}
      <div className="brick-summary">
        {summary}
      </div>

      {/* Confidence */}
      <div className="brick-confidence">
        <div
          className="brick-confidence-fill"
          style={{ width: `${Math.round(confidence * 100)}%` }}
        />
      </div>

      {/* Meta */}
      <div className="brick-meta">
        <span>sources: {sourceCount}</span>
        <span>updated: {lastUpdatedAt}</span>
      </div>
    </div>
  );
};
