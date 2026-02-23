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

# Import Celery Tasks
try:
    from services.cortex.tasks import sync_bricks_task, assemble_topic_task, synthesize_relationships_task
    HAS_CELERY = True
except ImportError:
    print("Celery tasks not found. Running in synchronous mode.")
    HAS_CELERY = False

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
cortex_api = CortexAPI()

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
        
    # Check Redis/Celery (Simplified)
    celery_status = "active" if HAS_CELERY else "disabled"
    
    # Check LLM (Simplified availability check)
    llm_status = "available" 
    # In a real scenario, we might ping Ollama or the configured LLM provider
    
    health = {
        "db": db_status,
        "redis": "healthy", # Assuming healthy if server runs, strictly would check connection
        "celery_workers": 1 if HAS_CELERY else 0, # Placeholder
        "llm": llm_status,
        "last_sync": datetime.now(timezone.utc).isoformat() # Placeholder for actual sync timestamp
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
def jarvis_anchor():
    data = request.json
    brick_id = data.get("brick_id")
    action = data.get("action") # "promote" or "reject"
    
    if not brick_id or action not in ["promote", "reject"]:
        return jsonify({"error": "Invalid anchor data"}), 400

    try:
        graph_manager = GraphManager()
        
        updates = {}
        if action == "promote":
            updates = {"anchored": True, "rejected": False}
        elif action == "reject":
            updates = {"anchored": False, "rejected": True}
        
        # Persist to graph database. 
        # Note: We assume the node exists or we are registering a placeholder "brick" node if it doesn't.
        # Ideally, brick nodes are already ingested.
        graph_manager.register_node("brick", brick_id, updates, merge=True)

        return jsonify({"status": "success", "brick_id": brick_id, "action": action})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/jarvis/node/promote", methods=["POST"])
def jarvis_node_promote():
    data = request.json
    node_id = data.get("node_id")
    promote_bricks = data.get("promote_bricks", [])
    actor = data.get("actor", "user") # Default actor

    if not node_id:
        return jsonify({"error": "node_id required"}), 400

    try:
        graph_manager = GraphManager()
        graph_manager.promote_node_to_frozen(node_id, promote_bricks, actor)
        
        # Return updated node state
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
def jarvis_node_kill():
    data = request.json
    node_id = data.get("node_id")
    reason = data.get("reason", "No reason provided")
    actor = data.get("actor", "user")

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
def jarvis_node_supersede():
    data = request.json
    old_node_id = data.get("old_node_id")
    new_node_id = data.get("new_node_id")
    reason = data.get("reason", "Superseded")
    actor = data.get("actor", "user")

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
    query = request.args.get("query")
    use_genai = request.args.get("use_genai", "false").lower() == "true"
    
    print(f"[{get_utc_now()}] [JARVIS_PREVIEW] Processing query: '{query}' (use_genai={use_genai})")

    if not query:
        print(f"[{get_utc_now()}] [JARVIS_PREVIEW] Error: Query parameter is required")
        return jsonify({"error": "Query parameter is required"}), 400

    # Use the read-only recall adapter
    recalled_bricks = recall_bricks_readonly(query, use_genai=use_genai)
    
    print(f"[{get_utc_now()}] [JARVIS_PREVIEW] Recalled {len(recalled_bricks)} bricks for query: '{query}'")

    top_bricks_output = [
        {"brick_id": brick["brick_id"], "confidence": round(brick["confidence"], 4)}
        for brick in recalled_bricks
    ]

    response_data = {
        "query": query,
        "top_bricks": top_bricks_output,
        "status": "preview"
    }
    return jsonify(response_data)

@app.route("/cognition/assemble", methods=["POST"])
def cognition_assemble():
    """Generic endpoint for topic assembly"""
    data = request.json or {}
    topic = data.get("topic")

    if not topic:
        return jsonify({"error": "topic is required"}), 400

    if HAS_CELERY:
        task = assemble_topic_task.delay(topic)
        return jsonify({"status": "accepted", "task_id": task.id}), 202
    else:
        result = cortex_api.assemble(topic)
        if result.get("status") == "failed":
            return jsonify(result), 500
        return jsonify(result)

@app.route("/cognition/synthesize", methods=["POST"])
def cognition_synthesize():
    """Trigger automatic relationship discovery"""
    data = request.json or {}
    topic_id = data.get("topic_id")

    if HAS_CELERY:
        task = synthesize_relationships_task.delay(topic_id=topic_id)
        return jsonify({"status": "accepted", "task_id": task.id}), 202
    else:
        result = cortex_api.synthesize(topic_id=topic_id)
        if result.get("status") == "failed":
            return jsonify(result), 500
        return jsonify(result)

@app.route("/tasks/sync", methods=["POST"])
def trigger_sync():
    """Manually trigger background sync of bricks to graph nodes"""
    if HAS_CELERY:
        task = sync_bricks_task.delay()
        return jsonify({"status": "accepted", "task_id": task.id}), 202
    else:
        # Synchronous fallback
        try:
            GraphManager().sync_bricks_to_nodes()
            return jsonify({"status": "success", "mode": "synchronous"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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
