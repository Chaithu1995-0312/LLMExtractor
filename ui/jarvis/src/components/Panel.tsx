import React from "react";

export interface PanelProps {
  title: string;
  fullText: string;
  sources: string[];
  conflicts: string[];
  supersededBy?: string;
  history: {
    timestamp: string;
    note: string;
  }[];
}

export const Panel: React.FC<PanelProps> = ({
  title,
  fullText,
  sources,
  conflicts,
  supersededBy,
  history,
}) => {
  return (
    <div className="nexus-panel">
      <h2 className="panel-title">{title}</h2>

      <section className="panel-section">
        <p className="panel-text">{fullText}</p>
      </section>

      {sources.length > 0 && (
        <section className="panel-section">
          <h4>Sources</h4>
          <ul>
            {sources.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
      )}

      {conflicts.length > 0 && (
        <section className="panel-section warning">
          <h4>Conflicts</h4>
          <ul>
            {conflicts.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </section>
      )}

      {supersededBy && (
        <section className="panel-section muted">
          <h4>Superseded By</h4>
          <p>{supersededBy}</p>
        </section>
      )}

      {history.length > 0 && (
        <section className="panel-section muted">
          <h4>History</h4>
          <ul>
            {history.map((h, i) => (
              <li key={i}>
                <span>{h.timestamp}</span> — {h.note}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};
