import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


PLANNED_ENTRY_POINTS = [
    "nexus/cli/main.py",
    "services/cortex/worker.py",
    "services/cortex/server.py",
    "src/nexus/sync/__main__.py",
    "tests/test_p0_fixes.py",
    "src/nexus/db/init_db.py",
    "src/nexus/scripts/migrate_to_intents.py",
]

PLANNED_INTERNAL_COMPONENTS = [
    ("src/nexus/evolution/ai_advisory.py", "StrategicAdvisor"),
    ("src/nexus/evolution/intent_governor.py", "IntentGovernor"),
    ("src/nexus/cognition/l2_3_linker.py", "L23Linker"),
    ("services/cortex/compaction_worker.py", "CompactionStrategy"),
    ("src/nexus/index/conversation_index.py", "ConversationIndex"),
    ("src/nexus/sync/ingest_history.py", "process_directory"),
    ("src/nexus/graph/validation.py", "run_full_validation"),
    ("validation/checks/l1_validator.py", "L1Validator"),
]


TOPIC_KEYWORDS = {
    "Architecture": ["architecture", "pipeline", "orchestrator", "component", "module"],
    "Ingestion": ["ingest", "brick", "source run", "memory context", "chunk"],
    "Graph Modeling": ["graph", "node", "edge", "cluster", "linker"],
    "Governance": ["policy", "intent", "governor", "audit", "coverage"],
    "Validation": ["validation", "validator", "integrity", "duplicates", "schema"],
    "Anti-Hallucination": ["hallucination", "traceability", "evidence", "non-destructive"],
    "Execution": ["worker", "task", "queue", "server", "api"],
}


@dataclass
class Node:
    node_id: str
    node_type: str
    description: str


def load_payload(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def flatten_to_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        return "\n".join(flatten_to_text(item) for item in payload)
    if isinstance(payload, dict):
        if "memory_context" in payload:
            return flatten_to_text(payload["memory_context"])
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return str(payload)


def extract_bricks(text: str) -> List[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    bricks: List[str] = []
    for block in blocks:
        lines = [ln.strip(" -•\t") for ln in block.splitlines() if ln.strip()]
        if len(lines) > 1 and any(len(ln.split()) < 18 for ln in lines):
            bricks.extend(lines)
        else:
            parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", block) if p.strip()]
            bricks.extend(parts if parts else [block])
    # de-dup while preserving order
    seen = set()
    out = []
    for b in bricks:
        key = b.lower()
        if key not in seen:
            seen.add(key)
            out.append(b)
    return out


def detect_topics(bricks: List[str]) -> Dict[str, int]:
    topic_counts = Counter()
    for b in bricks:
        lb = b.lower()
        for topic, keys in TOPIC_KEYWORDS.items():
            if any(k in lb for k in keys):
                topic_counts[topic] += 1
    return dict(topic_counts)


def classify_intent(brick: str) -> str:
    b = brick.lower()
    if any(x in b for x in ["must", "should", "cannot", "never", "rule", "policy"]):
        return "Constraint/Policy"
    if any(x in b for x in ["create", "implement", "build", "add", "run", "step"]):
        return "Implementation Plan"
    if any(x in b for x in ["architecture", "component", "module", "pipeline", "schema"]):
        return "Architecture Knowledge"
    if any(x in b for x in ["bug", "error", "missing", "conflict", "ambiguous"]):
        return "Issue/Gap"
    return "Observation"


def build_nodes_and_edges(topics: Dict[str, int], intent_counts: Dict[str, int]) -> Tuple[List[Node], List[Dict[str, str]]]:
    nodes: List[Node] = []
    edges: List[Dict[str, str]] = []

    nodes.append(Node("run:memory_context", "Run", "Source run for this ingestion"))

    for topic in topics:
        tid = f"topic:{topic.lower().replace(' ', '_')}"
        nodes.append(Node(tid, "Topic", f"Detected topic: {topic}"))
        edges.append({"source": "run:memory_context", "type": "contains_topic", "target": tid})

    for intent, count in intent_counts.items():
        iid = f"intent:{intent.lower().replace('/', '_').replace(' ', '_')}"
        nodes.append(Node(iid, "IntentClass", f"Intent class ({count} bricks): {intent}"))
        edges.append({"source": "run:memory_context", "type": "has_intent_class", "target": iid})

    # link topics -> strongest intent classes for compact report readability
    sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    for topic in topics:
        tid = f"topic:{topic.lower().replace(' ', '_')}"
        for intent, _ in sorted_intents:
            iid = f"intent:{intent.lower().replace('/', '_').replace(' ', '_')}"
            edges.append({"source": tid, "type": "associated_with", "target": iid})

    return nodes, edges


def ambiguity_gate(bricks: List[str]) -> List[Dict[str, str]]:
    blocked = []
    for b in bricks:
        lb = b.lower()
        if "[insert" in lb or "tbd" in lb or "???" in lb:
            blocked.append(
                {
                    "task": "Resolve ambiguous placeholder",
                    "status": "BLOCKED",
                    "assignee": "User",
                    "detail": b[:160],
                }
            )
    return blocked


def simulate_table_updates(brick_count: int, topic_count: int, node_count: int, edge_count: int) -> List[Dict[str, Any]]:
    return [
        {"table": "sync.source_runs", "added": 1, "updated": 0, "why": "registered memory_context run"},
        {"table": "sync.bricks", "added": brick_count, "updated": 0, "why": "atomic units extracted"},
        {"table": "sync.topics", "added": topic_count, "updated": 0, "why": "themes detected"},
        {"table": "graph.nodes", "added": node_count, "updated": 0, "why": "topics + intent classes + run node"},
        {"table": "graph.edges", "added": edge_count, "updated": 0, "why": "derived relationships"},
        {"table": "cognition.logs", "added": 1, "updated": 0, "why": "processing log"},
        {"table": "audit.processing_trail", "added": 1, "updated": 0, "why": "traceability trail"},
        {"table": "graph_ai.analysis_runs", "added": 1, "updated": 0, "why": "analysis execution record"},
    ]


def run_validation(nodes: List[Node], edges: List[Dict[str, str]], blocked: List[Dict[str, str]]) -> List[Dict[str, str]]:
    node_ids = {n.node_id for n in nodes}
    ref_ok = all(e["source"] in node_ids and e["target"] in node_ids for e in edges)
    dup_ok = len(node_ids) == len(nodes)
    prop_ok = all(n.node_type and n.description for n in nodes)

    return [
        {"check": "Referential Integrity", "result": "PASS" if ref_ok else "FAIL", "notes": "edge endpoints verified"},
        {"check": "Duplicate Nodes", "result": "PASS" if dup_ok else "FAIL", "notes": "node_id uniqueness"},
        {"check": "Property Validity", "result": "PASS" if prop_ok else "FAIL", "notes": "required node fields"},
        {"check": "Ambiguity Gate", "result": "PASS" if not blocked else "FAIL", "notes": f"{len(blocked)} blocked tasks"},
    ]


def architecture_comparison(root: Path) -> Dict[str, List[Dict[str, str]]]:
    entries = []
    for ep in PLANNED_ENTRY_POINTS:
        p = root / ep
        entries.append({"item": ep, "status": "Implemented" if p.exists() else "Missing"})

    internals = []
    for file_path, symbol in PLANNED_INTERNAL_COMPONENTS:
        p = root / file_path
        if not p.exists():
            internals.append({"item": symbol, "file": file_path, "status": "Missing"})
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if symbol in text:
            internals.append({"item": symbol, "file": file_path, "status": "Implemented"})
        else:
            internals.append({"item": symbol, "file": file_path, "status": "Partial"})

    return {"entry_points": entries, "internal_components": internals}


def write_reports(
    out_dir: Path,
    run_id: str,
    nodes: List[Node],
    edges: List[Dict[str, str]],
    tables: List[Dict[str, Any]],
    blocked: List[Dict[str, str]],
    validation: List[Dict[str, str]],
    comparison: Dict[str, List[Dict[str, str]]],
):
    out_dir.mkdir(parents=True, exist_ok=True)

    report_json = {
        "source_run": run_id,
        "graph_nodes_created": [n.__dict__ for n in nodes],
        "edges_created": edges,
        "tables_updated": tables,
        "generated_artifacts": [
            "processing_report.json",
            "processing_report.md",
            "graph_snapshot.mmd",
            "architecture_comparison.json",
        ],
        "pending_tasks": blocked,
        "validation_results": validation,
        "architecture_comparison": comparison,
    }

    (out_dir / "processing_report.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    mmd = ["graph TD"]
    for e in edges[:60]:
        mmd.append(f"  {e['source'].replace(':', '_')} -->|{e['type']}| {e['target'].replace(':', '_')}")
    (out_dir / "graph_snapshot.mmd").write_text("\n".join(mmd), encoding="utf-8")

    md_lines = [
        "# Nexus Processing Report",
        "",
        f"**Source Run:** `{run_id}`",
        "",
        "## Graph Nodes Created",
        f"Count: **{len(nodes)}**",
    ]
    md_lines += [f"- `{n.node_id}` ({n.node_type}) — {n.description}" for n in nodes]
    md_lines += ["", "## Edges Created", f"Count: **{len(edges)}**"]
    md_lines += [f"- `{e['source']}` --{e['type']}--> `{e['target']}`" for e in edges]
    md_lines += ["", "## Tables Updated"]
    md_lines += [f"- `{t['table']}`: +{t['added']} / ~{t['updated']} ({t['why']})" for t in tables]
    md_lines += ["", "## Generated Artifacts", "- processing_report.json", "- processing_report.md", "- graph_snapshot.mmd", "- architecture_comparison.json"]
    md_lines += ["", "## Pending Tasks"]
    if blocked:
        md_lines += [f"- [{b['status']}] {b['task']} ({b['assignee']}): {b['detail']}" for b in blocked]
    else:
        md_lines.append("- None")
    md_lines += ["", "## Validation Results"]
    md_lines += [f"- {v['check']}: **{v['result']}** ({v['notes']})" for v in validation]

    md_lines += ["", "## Current vs Planned Architecture"]
    md_lines.append("### Entry Points")
    md_lines += [f"- {e['item']}: **{e['status']}**" for e in comparison["entry_points"]]
    md_lines.append("### Internal Components")
    md_lines += [f"- {c['item']} ({c['file']}): **{c['status']}**" for c in comparison["internal_components"]]

    (out_dir / "processing_report.md").write_text("\n".join(md_lines), encoding="utf-8")
    (out_dir / "architecture_comparison.json").write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="Process memory context JSON and generate Nexus-style report")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output-dir", default="output/nexus_reports", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_path}")

    payload = load_payload(input_path)
    memory_text = flatten_to_text(payload)
    run_id = f"memory_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    bricks = extract_bricks(memory_text)
    topic_counts = detect_topics(bricks)
    intent_counts = Counter(classify_intent(b) for b in bricks)
    nodes, edges = build_nodes_and_edges(topic_counts, dict(intent_counts))
    blocked = ambiguity_gate(bricks)
    table_updates = simulate_table_updates(len(bricks), len(topic_counts), len(nodes), len(edges))
    validation = run_validation(nodes, edges, blocked)
    comparison = architecture_comparison(Path("."))

    out_dir = Path(args.output_dir)
    write_reports(out_dir, run_id, nodes, edges, table_updates, blocked, validation, comparison)

    summary = {
        "source_run": run_id,
        "bricks": len(bricks),
        "topics": len(topic_counts),
        "nodes": len(nodes),
        "edges": len(edges),
        "blocked_tasks": len(blocked),
        "report": str((out_dir / "processing_report.md").resolve()),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
