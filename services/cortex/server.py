from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import os
import sys
import logging
from datetime import datetime, timezone
import json
import sqlite3
from typing import Dict, Any

from nexus.utils_logging import setup_logging
# Initialize logging as early as possible
setup_logging("cortex")

# G-01: Import auth middleware before any endpoint definitions.
from services.cortex.auth import require_internal_auth, extract_verified_actor

# Configure standard logging to use our MultiWriter intercepted stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(message)s')
# Explicitly handle Werkzeug (Flask's server) logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.handlers = [] # Clear existing
werkzeug_logger.addHandler(logging.StreamHandler(sys.stdout))
werkzeug_logger.propagate = False # Prevent double logging if propagate is on

from nexus.vector.embedder import get_embedder

# Suppress transformers architectural warnings and HF Hub warnings
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN_WARNING"] = "1"
try:
    import transformers
    transformers.logging.set_verbosity_error()
except ImportError:
    pass

# Adjust the path to import CortexAPI from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api import CortexAPI
from services.cortex.orchestration import TaskQueue

# Use the properly installed nexus package
try:
    from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
    from nexus.cognition.assembler import assemble_topic
    from nexus.graph.manager import GraphManager
    from nexus.graph.prompt_manager import PromptManager
    from nexus.config import REPO_ROOT, GRAPH_DB_PATH
except ImportError:
    # Fallback for development if not installed
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.append(os.path.join(repo_root, "src"))
    from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
    from nexus.cognition.assembler import assemble_topic
    from nexus.graph.manager import GraphManager
    from nexus.graph.prompt_manager import PromptManager
    from nexus.config import REPO_ROOT, GRAPH_DB_PATH

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
cortex_api = CortexAPI()

# ── Memory Layer Routes ────────────────────────────────────────────────────
# Register the Memory Layer API blueprints. This is additive — it does not
# modify any existing route and cannot affect GraphManager invariants.
try:
    from nexus.memory.api_routes import register_memory_routes
    register_memory_routes(app)
    print("[Cortex] Memory Layer routes registered (/api/v1/memory/*, /api/v1/bricks/from_memory).")
except Exception as _mem_err:
    print(f"[Cortex] WARNING: Memory Layer routes could not be loaded: {_mem_err}")
# ──────────────────────────────────────────────────────────────────────────

# ── Cognitive Control Plane v2 ─────────────────────────────────────────────
# Lazy singleton for QueryOrchestrator — heavy subsystems initialise on first
# request, not at server startup, to avoid blocking the Flask worker.
_query_orchestrator = None

def _get_orchestrator():
    global _query_orchestrator
    if _query_orchestrator is None:
        from nexus.orchestration.query_orchestrator import QueryOrchestrator
        _query_orchestrator = QueryOrchestrator()
    return _query_orchestrator


@app.route("/api/v2/query", methods=["POST"])
def api_v2_query():
    """
    POST /api/v2/query

    Unified Cognitive Control Plane endpoint (v2).

    Accepts:
        {
            "query":     "<natural language question>",
            "overrides": {                       (optional)
                "force_route":          "graph" | "memory" | "hybrid",
                "disable_escalation":   true | false,
                "threshold_override":   0.0–1.0
            }
        }

    Returns:
        Full execution payload from QueryOrchestrator including:
        route, retrieval, confidence breakdown, hybrid_conflict,
        escalation state, execution timeline, system_state, response.

    Always returns HTTP 200 with status in payload body.
    Returns HTTP 400 on missing query.
    Returns HTTP 500 only on unrecoverable orchestration crash.
    """
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    overrides = body.get("overrides") or {}

    if not query:
        return jsonify({
            "status": "failed",
            "error": "query is required and must be a non-empty string",
        }), 400

    # Validate overrides shape — silently strip invalid keys
    sanitised_overrides = {}
    force_route = overrides.get("force_route")
    if force_route in ("graph", "memory", "hybrid"):
        sanitised_overrides["force_route"] = force_route

    disable_esc = overrides.get("disable_escalation")
    if isinstance(disable_esc, bool):
        sanitised_overrides["disable_escalation"] = disable_esc

    threshold = overrides.get("threshold_override")
    if isinstance(threshold, (int, float)) and 0.0 <= float(threshold) <= 1.0:
        sanitised_overrides["threshold_override"] = float(threshold)

    try:
        orchestrator = _get_orchestrator()
        result = orchestrator.execute(query=query, overrides=sanitised_overrides)
        return jsonify(result), 200

    except Exception as exc:
        logging.getLogger(__name__).error(
            "[/api/v2/query] Orchestration error for query='%s': %s",
            query[:80], exc, exc_info=True,
        )
        return jsonify({
            "status": "failed",
            "error": "orchestration_error",
            "message": str(exc)[:300],
        }), 500
# ──────────────────────────────────────────────────────────────────────────

@app.before_request
def log_request_info():
    if request.path.startswith("/jarvis") or request.path.startswith("/api") or request.path.startswith("/cognition"):
        body = ""
        if request.is_json:
            try:
                body = json.dumps(request.json)
            except:
                body = "<invalid json>"
        
        # Mask potentially sensitive headers if any (usually not an issue for local development)
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie']}
        
        print(f"[{datetime.now(timezone.utc).isoformat()}] [API_REQ] {request.method} {request.url}")
        print(f"   Headers: {headers}")
        if body:
            print(f"   Body: {body[:1000]}{'...' if len(body) > 1000 else ''}")

@app.after_request
def log_response_info(response):
    if request.path.startswith("/jarvis") or request.path.startswith("/api") or request.path.startswith("/cognition"):
        print(f"[{datetime.now(timezone.utc).isoformat()}] [API_RES] {request.method} {request.url} -> Status: {response.status_code}")
        
        if response.is_json:
             try:
                resp_body = response.get_data(as_text=True)
                print(f"   Response JSON: {resp_body[:500]}{'...' if len(resp_body) > 500 else ''}")
             except:
                 pass
    return response

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()

# --- Helper for direct DB access (Production Postgres) ---
def get_db_metrics():
    """
    Direct Postgres access for production metrics.
    """
    stats = {
        "conversations": 0,
        "source_runs": 0,
        "bricks": 0,
        "nodes": 0,
        "edges": 0
    }
    
    try:
        from nexus.db import get_adapter
        db = get_adapter()
        
        row = db.fetch_one("SELECT COUNT(*) FROM graph.nodes")
        stats["nodes"] = row[0] if row else 0
        
        row = db.fetch_one("SELECT COUNT(*) FROM graph.edges")
        stats["edges"] = row[0] if row else 0
        
        # 'intents' is a view or subset of nodes, let's query nodes where type='intent'
        row = db.fetch_one("SELECT COUNT(*) FROM graph.nodes WHERE type = 'intent'")
        stats["conversations"] = row[0] if row else 0 
        
        # Original queried 'runs', likely 'sync.source_runs'
        row = db.fetch_one("SELECT COUNT(*) FROM sync.source_runs")
        stats["source_runs"] = row[0] if row else 0

        # Also get bricks count
        row = db.fetch_one("SELECT COUNT(*) FROM sync.bricks")
        stats["bricks"] = row[0] if row else 0
        
    except Exception as e:
        print(f"Error fetching DB metrics from Postgres: {e}")
        
    return stats

def get_lifecycle_distribution():
    """
    Aggregate lifecycle states from Postgres intents.
    """
    distribution = {
        "LOOSE": 0,
        "FORMING": 0,
        "FROZEN": 0,
        "SUPERSEDED": 0,
        "KILLED": 0
    }
    
    try:
        from nexus.db import get_adapter
        db = get_adapter()
        
        # Querying graph.nodes for intents
        query = "SELECT data->>'lifecycle', COUNT(*) FROM graph.nodes WHERE type='intent' GROUP BY data->>'lifecycle'"
        rows = db.fetch_all(query)
        
        for r in rows:
            state = r[0]
            count = r[1]
            if state:
                key = state.upper()
                if key in distribution:
                    distribution[key] = count
                else:
                    distribution[key] = count
            else:
                # Default fallback
                distribution["FORMING"] += count
                
    except Exception as e:
        print(f"Error fetching lifecycle stats from Postgres: {e}")
        
    return distribution

# --- Metrics Endpoints (Task 1) ---

@app.route("/api/metrics/overview", methods=["GET"])
def metrics_overview():
    return jsonify(get_db_metrics())

@app.route("/api/metrics/lifecycle", methods=["GET"])
def metrics_lifecycle():
    return jsonify(get_lifecycle_distribution())

@app.route("/api/health", methods=["GET"])
def system_health():
    # Check DB
    db_status = "healthy"
    try:
        conn = sqlite3.connect(GRAPH_DB_PATH)
        conn.cursor().execute("SELECT 1")
        conn.close()
    except:
        db_status = "unhealthy"
        
    # Check PG Queue status
    try:
        from nexus.db import get_adapter
        db = get_adapter()
        row = db.fetch_one("SELECT COUNT(*) FROM graph.l3_tasks WHERE status = 'pending'")
        pending_tasks = row[0] if row else 0
        queue_status = "healthy"
    except:
        pending_tasks = 0
        queue_status = "unhealthy"
    
    # Check LLM (Simplified availability check)
    llm_status = "available" 
    
    health = {
        "db": db_status,
        "pg_queue": queue_status,
        "pending_tasks": pending_tasks,
        "llm": llm_status,
        "last_sync": datetime.now(timezone.utc).isoformat()
    }
    return jsonify(health)

# --- Existing Endpoints ---

@app.route("/jarvis/graph-index", methods=["GET"])
def jarvis_graph_index():
    try:
        graph_manager = GraphManager()
        nodes = graph_manager.get_all_nodes_raw()
        edges = graph_manager.get_all_edges_raw()
        
        # Backward compatibility: Synthesize overrides list from node metadata
        overrides = []
        for n in nodes:
            if n.get("anchored"):
                overrides.append({
                    "brick_id": n["id"],
                    "action": "promote",
                    "timestamp": n.get("created_at") # Metadata might not have updated_at, fallback to created_at
                })
            elif n.get("rejected"):
                overrides.append({
                    "brick_id": n["id"],
                    "action": "reject",
                    "timestamp": n.get("created_at")
                })
        
        # Try to read index content for context if available
        graph_dir = os.path.join(REPO_ROOT, "src", "nexus", "graph")
        index_path = os.path.join(graph_dir, "index.md")
        index_content = ""
        if os.path.exists(index_path):
             with open(index_path, "r", encoding="utf-8") as f:
                index_content = f.read()

        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "index_content": index_content,
            "anchor_overrides": overrides
        })
    except Exception as e:
        print(f"[graph-index] Backend error: {e}")
        # Return a valid empty graph so the UI doesn't enter a 500 retry loop
        return jsonify({
            "nodes": [],
            "edges": [],
            "index_content": "",
            "anchor_overrides": [],
            "_error": str(e)
        }), 200

@app.route("/jarvis/anchor", methods=["POST"])
@require_internal_auth
def jarvis_anchor():
    # G-01: actor comes from verified token, not request body.
    actor = extract_verified_actor(request)
    data = request.json
    brick_id = data.get("brick_id")
    action = data.get("action")  # "promote" or "reject"

    if not brick_id or action not in ["promote", "reject"]:
        return jsonify({"error": "Invalid anchor data"}), 400

    try:
        graph_manager = GraphManager()

        updates = {}
        if action == "promote":
            updates = {"anchored": True, "rejected": False}
        elif action == "reject":
            updates = {"anchored": False, "rejected": True}

        graph_manager.register_node("brick", brick_id, updates, merge=True)
        return jsonify({"status": "success", "brick_id": brick_id, "action": action, "actor": actor})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/jarvis/node/promote", methods=["POST"])
@require_internal_auth
def jarvis_node_promote():
    # G-01: actor sourced from verified token, not caller body.
    actor = extract_verified_actor(request)
    data = request.json
    node_id = data.get("node_id")
    promote_bricks = data.get("promote_bricks", [])

    if not node_id:
        return jsonify({"error": "node_id required"}), 400

    try:
        graph_manager = GraphManager()
        graph_manager.promote_node_to_frozen(node_id, promote_bricks, actor)

        node_type, node_data = graph_manager.get_node(node_id)
        return jsonify({
            "status": "success",
            "node": {
                "id": node_id,
                "type": node_type,
                **node_data
            }
        })
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/jarvis/node/kill", methods=["POST"])
@require_internal_auth
def jarvis_node_kill():
    # G-01: actor sourced from verified token, not caller body.
    actor = extract_verified_actor(request)
    data = request.json
    node_id = data.get("node_id")
    reason = data.get("reason", "No reason provided")

    if not node_id:
        return jsonify({"error": "node_id required"}), 400

    try:
        graph_manager = GraphManager()
        graph_manager.kill_node(node_id, reason, actor)

        node_type, node_data = graph_manager.get_node(node_id)
        return jsonify({
            "status": "success",
            "node": {
                "id": node_id,
                "type": node_type,
                **node_data
            }
        })
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/jarvis/node/supersede", methods=["POST"])
@require_internal_auth
def jarvis_node_supersede():
    # G-01: actor sourced from verified token, not caller body.
    actor = extract_verified_actor(request)
    data = request.json
    old_node_id = data.get("old_node_id")
    new_node_id = data.get("new_node_id")
    reason = data.get("reason", "Superseded")

    if not old_node_id or not new_node_id:
        return jsonify({"error": "old_node_id and new_node_id required"}), 400

    try:
        graph_manager = GraphManager()
        graph_manager.supersede_node(old_node_id, new_node_id, reason, actor)

        return jsonify({
            "status": "success",
            "old_node_id": old_node_id,
            "new_node_id": new_node_id
        })
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/jarvis/brick-meta", methods=["GET"])
def jarvis_brick_meta():
    brick_id = request.args.get("brick_id")
    if not brick_id:
        return jsonify({"error": "brick_id required"}), 400

    meta = get_recall_brick_metadata(brick_id)
    if not meta:
        return jsonify({"error": "brick not found"}), 404

    source_file = meta["source_file"]
    source_span = meta["source_span"]

    text_sample = ""
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            tree = json.load(f)

        # find matching message + block
        for msg in tree.get("messages", []):
            if (msg.get("message_id") or msg.get("id")) == source_span.get("message_id"):
                content = msg.get("content", "")
                blocks = []
                if isinstance(content, str):
                    # Replicate extractor logic: split by double newlines
                    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
                elif isinstance(content, list):
                    blocks = content
                
                idx = source_span.get("block_index")
                if idx is not None and idx < len(blocks):
                    text_sample = str(blocks[idx])[:500]
                break
    except Exception:
        text_sample = ""

    return jsonify({
        "brick_id": brick_id,
        "source_file": source_file,
        "source_span": source_span,
        "text_sample": text_sample
    })

@app.route("/jarvis/brick-full", methods=["GET"])
def jarvis_brick_full():
    brick_id = request.args.get("brick_id")
    if not brick_id:
        return jsonify({"error": "brick_id required"}), 400

    meta = get_recall_brick_metadata(brick_id)
    if not meta:
        return jsonify({"error": "brick not found"}), 404

    source_file = meta["source_file"]
    span = meta["source_span"]

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            tree = json.load(f)

        for msg in tree.get("messages", []):
            if (msg.get("message_id") or msg.get("id")) == span["message_id"]:
                content = msg.get("content", "")
                blocks = []
                if isinstance(content, str):
                    # Replicate extractor logic: split by double newlines
                    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
                elif isinstance(content, list):
                    blocks = content
                
                idx = span["block_index"]

                if idx is not None and idx < len(blocks):
                    return jsonify({
                        "brick_id": brick_id,
                        "source_file": source_file,
                        "message_id": span["message_id"],
                        "block_index": idx,
                        "role": msg.get("role"),
                        "created_at": msg.get("created_at"),
                        "full_text": blocks[idx]
                    })
    except Exception:
        pass

    return jsonify({"error": "block not found"}), 404



@app.route("/jarvis/ask-preview", methods=["GET"])
def jarvis_ask_preview():
    """
    Hybrid semantic preview.
    ?query=<text>  — required
    ?top_k=10      — optional, default 10
    ?lifecycle=frozen — optional lifecycle filter
    """
    query = request.args.get("query")
    top_k = int(request.args.get("top_k", 10))
    lifecycle_filter = request.args.get("lifecycle") or None

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    result = cortex_api.ask_preview(query=query, top_k=top_k, lifecycle_filter=lifecycle_filter)
    return jsonify(result)


@app.route("/jarvis/system-story", methods=["GET"])
def jarvis_system_story():
    """
    Replayable cognitive narrative stream.
    ?limit=50        — max events to return (default 50)
    ?node_id=<id>    — filter by node
    ?event_type=<t>  — filter by event type
    """
    limit = int(request.args.get("limit", 50))
    node_id = request.args.get("node_id") or None
    event_type = request.args.get("event_type") or None

    result = cortex_api.get_system_story(limit=limit, node_id=node_id, event_type=event_type)
    return jsonify(result)

@app.route("/cognition/assemble", methods=["POST"])
def cognition_assemble():
    """Generic endpoint for topic assembly"""
    data = request.json or {}
    topic = data.get("topic")

    if not topic:
        return jsonify({"error": "topic is required"}), 400

    TaskQueue.enqueue("assemble_topic", {"topic": topic})
    return jsonify({"status": "queued"}), 202

@app.route("/cognition/synthesize", methods=["POST"])
def cognition_synthesize():
    """Trigger automatic relationship discovery"""
    data = request.json or {}
    topic_id = data.get("topic_id")

    TaskQueue.enqueue("synthesize_relationships", {"topic_id": topic_id})
    return jsonify({"status": "queued"}), 202


# =============================================================================
# COGNITIVE COMPILER — Export & Refiner Endpoints  (Spec §7, §8)
# =============================================================================

@app.route("/export/topic/<topic_id>", methods=["GET"])
def export_topic(topic_id: str):
    """
    GET /export/topic/<id>?format=json|md&snapshot=true|false

    Compile and optionally snapshot a topic, then return:
      - format=json  → StructuredDocument as JSON  (default)
      - format=md    → Markdown rendering

    Query params:
        format    : 'json' | 'md'   (default: 'json')
        snapshot  : 'true' | 'false' (default: 'false')
                    When true, persists a versioned snapshot and bumps version.

    The compilation is READ-ONLY with respect to the graph.
    """
    fmt = request.args.get("format", "json").lower()
    save_snap = request.args.get("snapshot", "false").lower() == "true"

    result = cortex_api.export_topic(topic_id, fmt=fmt, save_snapshot=save_snap)

    if "error" in result:
        status_code = 404 if "not found" in result["error"].lower() else 500
        return jsonify(result), status_code

    if fmt == "md":
        # Return raw Markdown as plain text for easy download
        md_content = result.get("markdown", "")
        from flask import Response
        return Response(
            md_content,
            mimetype="text/markdown",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="topic_{topic_id}_{result.get("version", "1.0.0")}.md"'
                )
            },
        )

    return jsonify(result)


@app.route("/export/topic/<topic_id>/snapshot", methods=["GET"])
def get_topic_snapshot(topic_id: str):
    """
    GET /export/topic/<id>/snapshot
    Return the latest persisted snapshot without recompiling.
    """
    result = cortex_api.get_topic_snapshot(topic_id)
    if not result:
        return jsonify({"error": "No snapshot found", "topic_id": topic_id}), 404
    return jsonify(result)


@app.route("/cognition/compile", methods=["POST"])
def queue_topic_compile():
    """
    POST /cognition/compile
    Queue a background compile_topic_document task.

    Body: { "topic_id": "...", "save_snapshot": true }
    """
    data = request.json or {}
    topic_id = data.get("topic_id")
    if not topic_id:
        return jsonify({"error": "topic_id is required"}), 400

    save_snapshot = data.get("save_snapshot", True)
    TaskQueue.enqueue("compile_topic_document", {
        "topic_id": topic_id,
        "save_snapshot": save_snapshot,
    })
    return jsonify({"status": "queued", "topic_id": topic_id}), 202


@app.route("/cognition/refine", methods=["POST"])
def queue_refiner_audit():
    """
    POST /cognition/refine
    Queue a background run_refiner_audit task (advisory, non-destructive).

    Body: { "topic_id": "..." }
    """
    data = request.json or {}
    topic_id = data.get("topic_id")
    if not topic_id:
        return jsonify({"error": "topic_id is required"}), 400

    TaskQueue.enqueue("run_refiner_audit", {"topic_id": topic_id})
    return jsonify({"status": "queued", "topic_id": topic_id}), 202


@app.route("/api/topics/<topic_id>/drift-reports", methods=["GET"])
def get_topic_drift_reports(topic_id: str):
    """
    GET /api/topics/<id>/drift-reports?limit=100
    Return unresolved Refiner advisory reports for a topic.
    """
    limit = request.args.get("limit", default=100, type=int)
    result = cortex_api.get_drift_reports(topic_id, limit=limit)
    return jsonify(result)


@app.route("/api/drift-reports/<report_id>/resolve", methods=["POST"])
def resolve_drift_report(report_id: str):
    """
    POST /api/drift-reports/<id>/resolve
    Mark a drift report as human-resolved.

    Body: { "resolved_by": "actor_name" }
    """
    data = request.json or {}
    resolved_by = data.get("resolved_by", "user")
    result = cortex_api.resolve_drift_report(report_id, resolved_by)
    return jsonify(result)


@app.route("/api/topics/<topic_id>/ontology", methods=["GET"])
def get_topic_ontology(topic_id: str):
    """
    GET /api/topics/<id>/ontology
    Return the ontology parent chain for a topic.
    """
    result = cortex_api.get_topic_ontology(topic_id)
    return jsonify(result)

@app.route("/tasks/sync", methods=["POST"])
def trigger_sync():
    """Manually trigger background sync of bricks to graph nodes"""
    TaskQueue.enqueue("sync_bricks", {})
    return jsonify({"status": "queued"}), 202

@app.route("/jarvis/assemble-topic", methods=["POST"])
def jarvis_assemble_topic():
    # Alias to the generic endpoint for backward compatibility/UI support
    return cognition_assemble()

@app.route("/jarvis/prompts", methods=["GET"])
def jarvis_prompts():
    """Retrieve filtered prompts with complexity scores from processed trees."""
    try:
        min_score = request.args.get("min_score", default=0.0, type=float)
        prompts = cortex_api.get_all_prompts(min_score=min_score)
        return jsonify({
            "status": "success",
            "count": len(prompts),
            "min_score": min_score,
            "prompts": prompts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- P1 Observability Endpoints ---

@app.route("/api/audit/events", methods=["GET"])
def get_audit_events():
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    event_type = request.args.get("event")
    component = request.args.get("component")
    run_id = request.args.get("run_id")
    
    return jsonify(cortex_api.get_audit_events(limit, offset, event_type, component, run_id))

@app.route("/api/runs/<run_id>", methods=["GET"])
def get_run_details(run_id):
    return jsonify(cortex_api.get_run_details(run_id))

@app.route("/api/graph/snapshot", methods=["GET"])
def get_graph_snapshot():
    return jsonify(cortex_api.get_graph_snapshot())

@app.route("/api/prompts", methods=["GET"])
def get_governance_prompts():
    try:
        pm = PromptManager()
        prompts = pm.get_all_system_prompts()
        return jsonify({"prompts": prompts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- New Governance API Endpoints ---

@app.route("/api/topics/<topic_id>/alerts", methods=["GET"])
def get_topic_alerts(topic_id):
    return jsonify(cortex_api.get_alerts(topic_id))

@app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id):
    data = request.json
    actor = data.get("actor", "user")
    return jsonify(cortex_api.acknowledge_alert(alert_id, actor))

@app.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    data = request.json
    actor = data.get("actor", "user")
    action = data.get("action", "UNKNOWN")
    metadata = data.get("metadata", {})
    return jsonify(cortex_api.resolve_alert(alert_id, actor, action, metadata))

@app.route("/api/alerts/<alert_id>/dismiss", methods=["POST"])
def dismiss_alert(alert_id):
    data = request.json
    actor = data.get("actor", "user")
    reason = data.get("reason", "No reason provided")
    return jsonify(cortex_api.dismiss_alert(alert_id, actor, reason))

@app.route("/api/alerts/<alert_id>/archive", methods=["POST"])
def archive_alert(alert_id):
    return jsonify(cortex_api.archive_alert(alert_id))

@app.route("/api/alerts/<alert_id>/suggest-prompts", methods=["POST"])
def suggest_prompts(alert_id):
    data = request.json
    actor = data.get("actor", "user")
    return jsonify(cortex_api.suggest_prompts(alert_id, actor))

@app.route("/api/topics/<topic_id>/score", methods=["GET"])
def get_topic_coverage_score(topic_id):
    return jsonify(cortex_api.get_coverage_score(topic_id))

@socketio.on("connect")
def handle_connect():
    emit("connected", {"status": "Audit stream connected"})

@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected from audit stream")

if __name__ == "__main__":
    print("Prewarming embedder...")
    get_embedder()
    print("Embedder ready")

    # Initial sync of bricks to graph
    print("Performing initial graph sync...")
    try:
        GraphManager().sync_bricks_to_nodes()
    except Exception as e:
        print(f"Initial sync failed: {e}")

    # For development purposes, run with debug true
    # In production, use a production-ready WSGI server like Gunicorn
    print("Starting Cortex Server with SocketIO on port 5001...")
    socketio.run(app, debug=False, port=5001)
