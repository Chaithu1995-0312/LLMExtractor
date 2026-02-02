from flask import Flask, request, jsonify
import os
import sys
from datetime import datetime, timezone
import json

# Adjust the path to import CortexAPI from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api import CortexAPI

# Use the properly installed nexus package
try:
    from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
    from nexus.config import REPO_ROOT
except ImportError:
    # Fallback for development if not installed
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.append(os.path.join(repo_root, "src"))
    from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
    from nexus.config import REPO_ROOT

app = Flask(__name__)
cortex_api = CortexAPI()

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()

@app.route("/jarvis/graph-index", methods=["GET"])
def jarvis_graph_index():
    graph_dir = os.path.join(REPO_ROOT, "src", "nexus", "graph")
    nodes_path = os.path.join(graph_dir, "nodes.json")
    edges_path = os.path.join(graph_dir, "edges.json")
    index_path = os.path.join(graph_dir, "index.md")
    overrides_path = os.path.join(graph_dir, "anchors.override.json")

    try:
        if not (os.path.exists(nodes_path) and os.path.exists(edges_path) and os.path.exists(index_path)):
             return jsonify({"error": "Graph index files not found"}), 404

        with open(nodes_path, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        
        with open(edges_path, "r", encoding="utf-8") as f:
            edges = json.load(f)

        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        overrides = []
        if os.path.exists(overrides_path):
            try:
                with open(overrides_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    overrides = data.get("overrides", [])
            except Exception:
                overrides = []

        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "index_content": index_content,
            "anchor_overrides": overrides
        })
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
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Use the read-only recall adapter
    recalled_bricks = recall_bricks_readonly(query)

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

if __name__ == "__main__":
    # For development purposes, run with debug true
    # In production, use a production-ready WSGI server like Gunicorn
    app.run(debug=True, port=5001)
