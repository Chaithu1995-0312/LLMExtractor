from flask import Flask, request, jsonify
import os
import sys
from datetime import datetime, timezone
import json
from nexus.vector.embedder import get_embedder

# Adjust the path to import CortexAPI from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api import CortexAPI

# Use the properly installed nexus package
try:
    from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
    from nexus.cognition.assembler import assemble_topic
    from nexus.graph.manager import GraphManager
    from nexus.config import REPO_ROOT
except ImportError:
    # Fallback for development if not installed
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.append(os.path.join(repo_root, "src"))
    from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
    from nexus.cognition.assembler import assemble_topic
    from nexus.graph.manager import GraphManager
    from nexus.config import REPO_ROOT

app = Flask(__name__)
cortex_api = CortexAPI()

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()

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
        return jsonify({"error": str(e)}), 500

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
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Use the read-only recall adapter
    recalled_bricks = recall_bricks_readonly(query, use_genai=use_genai)

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

    result = cortex_api.assemble(topic)
    if result.get("status") == "failed":
        return jsonify(result), 500
    return jsonify(result)

@app.route("/jarvis/assemble-topic", methods=["POST"])
def jarvis_assemble_topic():
    # Alias to the generic endpoint for backward compatibility/UI support
    return cognition_assemble()

if __name__ == "__main__":
    print("Prewarming embedder...")
    get_embedder()
    print("Embedder ready")
    # For development purposes, run with debug true
    # In production, use a production-ready WSGI server like Gunicorn
    app.run(debug=False, port=5001)
