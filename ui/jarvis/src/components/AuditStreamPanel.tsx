import React, { useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";

interface AuditEvent {
  timestamp: string;
  event: string;
  component: string;
  agent: string;
  topic_id?: string;
  run_id?: string;
  model_tier?: string;
  cost?: {
    usd?: number;
    tokens_in?: number;
    tokens_out?: number;
  };
  decision?: {
    action?: string;
    reason?: string;
  };
  metadata?: any;
}

// Connect to the Socket.IO server on port 5001
const socket: Socket = io("http://localhost:5001");

export default function AuditStreamPanel() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    socket.on("connected", (msg) => {
      console.log("SocketIO Connected:", msg);
    });

    socket.on("audit_event", (data: AuditEvent) => {
      console.log("Audit Event Received:", data);
      setEvents((prev) => [data, ...prev.slice(0, 199)]);
    });

    return () => {
      socket.off("connected");
      socket.off("audit_event");
    };
  }, []);

  const filtered = events.filter((e) =>
    filter ? e.component === filter : true
  );

  return (
    <div className="audit-stream-panel" style={{ 
      padding: 16, 
      background: "#fff", 
      border: "1px solid #ddd", 
      borderRadius: 8,
      height: "100%",
      display: "flex",
      flexDirection: "column"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Live Audit Stream</h3>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{ padding: "4px 8px", borderRadius: 4 }}
        >
          <option value="">All Components</option>
          <option value="compiler">Compiler</option>
          <option value="graph">Graph</option>
          <option value="cognition">Cognition</option>
          <option value="resolver">Resolver</option>
        </select>
      </div>

      <div style={{ flex: 1, overflowY: "auto", border: "1px solid #eee", borderRadius: 4 }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 20, textAlign: "center", color: "#888" }}>
            Waiting for events...
          </div>
        ) : (
          filtered.map((e, index) => (
            <div
              key={`${e.timestamp}-${index}`}
              style={{
                padding: "8px 12px",
                borderBottom: "1px solid #eee",
                fontSize: "0.85rem",
                background: e.event.includes("HALLUCINATION") || e.event.includes("REJECTED")
                    ? "#fff0f0"
                    : e.event.includes("FROZEN") || e.event.includes("PROMOTED")
                    ? "#f0fff4"
                    : "#fff",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <strong style={{ color: "#333" }}>{e.event}</strong>
                <span style={{ color: "#888", fontSize: "0.75rem" }}>
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
              </div>
              
              <div style={{ color: "#666", fontSize: "0.8rem", marginBottom: 4 }}>
                <span style={{ background: "#f0f0f0", padding: "1px 4px", borderRadius: 3, marginRight: 6 }}>
                  {e.component}
                </span>
                <span>{e.agent}</span>
              </div>

              {e.decision?.reason && (
                <div style={{ fontStyle: "italic", color: "#555", fontSize: "0.8rem", marginTop: 2 }}>
                  "{e.decision.reason}"
                </div>
              )}

              {e.cost?.usd !== undefined && e.cost.usd > 0 && (
                <div style={{ marginTop: 4, fontWeight: "bold", color: "#2d6a4f" }}>
                  💰 ${e.cost.usd.toFixed(6)}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
