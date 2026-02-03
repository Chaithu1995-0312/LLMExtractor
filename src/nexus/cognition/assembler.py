import json
import os
import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, List, Set, Any
from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
from nexus.config import DEFAULT_OUTPUT_DIR
from nexus.graph.manager import GraphManager

# Artifact storage path
ARTIFACTS_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "artifacts")

def _get_slug(text: str) -> str:
    """Create a filename-safe slug from text."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text[:64]

def _calculate_content_hash(content: Any) -> str:
    """Calculate SHA256 hash of JSON-serializable content."""
    json_bytes = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()

def _load_tree_file(path: str) -> Dict:
    """Load a conversation tree file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def assemble_topic(topic_query: str) -> str:
    """
    Assemble a canonical cognition artifact for the given topic.
    
    Pipeline:
    1. Recall relevant bricks (read-only).
    2. Expand to full source documents.
    3. Deduplicate content and track span provenance.
    4. Assemble structured JSON artifact.
    5. Persist to disk with content addressing.
    6. Register provenance in the Knowledge Graph.
    
    Returns:
        Path to the saved artifact.
    """
    # 1. Recall Phase
    print(f"DEBUG: recalling bricks for '{topic_query}'")
    candidates = recall_bricks_readonly(topic_query, k=15) # Boost k slightly for coverage
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # FIX: Explicit early return if recall fails
    if not candidates:
        print("DEBUG: No bricks found. Returning empty artifact with status NO_RECALL_MATCHES.")
        artifact_payload = {
            "topic": topic_query,
            "provenance": {
                "brick_ids": [],
                "source_files": []
            },
            "raw_excerpts": [],
            "coverage_status": "NO_RECALL_MATCHES",
            "extracted_facts": [],
            "decisions": [],
            "constraints": [],
            "edge_cases": [],
            "artifact_type": "TOPIC_COGNITION_V1"
        }
        # IMPORTANT: artifact_payload must remain time-independent to keep content addressing stable
        artifact_hash = _calculate_content_hash(artifact_payload)
        
        final_artifact = {
            "artifact_id": artifact_hash,
            "created_at": timestamp,
            "query": topic_query,
            "derived_from": [],
            "payload": artifact_payload
        }
        
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        slug = _get_slug(topic_query)
        filename = f"{slug}_{artifact_hash[:12]}_{int(datetime.now().timestamp())}.json"
        output_path = os.path.join(ARTIFACTS_DIR, filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_artifact, f, ensure_ascii=False, indent=2)
            
        return output_path
    
    # 2. Expansion & Deduplication Phase
    # Map: source_hash -> { meta, tree, brick_ids, spans }
    unique_docs: Dict[str, Dict] = {}
    
    for cand in candidates:
        brick_id = cand["brick_id"]
        meta = get_recall_brick_metadata(brick_id)
        
        if not meta or "source_file" not in meta:
            print(f"WARN: Missing metadata for brick {brick_id}")
            continue
            
        source_path = meta["source_file"]
        
        try:
            # Load full source
            tree_data = _load_tree_file(source_path)
            
            # Use content hash of the tree data for deduplication
            # If two files have different paths but identical content, they are the same document.
            doc_hash = _calculate_content_hash(tree_data)
            
            if doc_hash not in unique_docs:
                unique_docs[doc_hash] = {
                    "source_file": source_path, # Keep one valid path
                    "full_tree": tree_data,
                    "brick_ids": set(),
                    "spans": [] # List of {message_id, block_index}
                }
            
            # Register provenance
            unique_docs[doc_hash]["brick_ids"].add(brick_id)
            if "source_span" in meta:
                span = meta["source_span"]
                # FIX: Upgrade to span-aware coverage map
                unique_docs[doc_hash]["spans"].append({
                    "message_id": span.get("message_id"),
                    "block_index": span.get("block_index")
                })
                    
        except Exception as e:
            print(f"ERROR: Failed to load source {source_path}: {e}")
            continue

    # 3. Assembly Phase
    raw_excerpts = []
    
    for doc_hash, doc_info in unique_docs.items():
        tree = doc_info["full_tree"]
        
        # FIX: Normalize conversation structure
        normalized = []
        for msg in tree.get("messages", []):
            content = msg.get("content", "")
            blocks = []
            if isinstance(content, str):
                blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
            elif isinstance(content, list):
                # Assuming list of strings
                blocks = [str(b).strip() for b in content if str(b).strip()]
            
            normalized.append({
                "message_id": msg.get("message_id") or msg.get("id"),
                "role": msg.get("role"),
                "created_at": msg.get("created_at"),
                "blocks": [
                    {"index": i, "text": b}
                    for i, b in enumerate(blocks)
                ]
            })
        
        # Construct the structured excerpt
        excerpt = {
            "source_file": doc_info["source_file"],
            "coverage": {
                "spans": doc_info["spans"]
            },
            "conversation": normalized
        }
        raw_excerpts.append(excerpt)
    
    # Gather all brick IDs involved
    all_brick_ids = set()
    for doc in unique_docs.values():
        all_brick_ids.update(doc["brick_ids"])

    artifact_payload = {
        "topic": topic_query,
        "provenance": {
            "brick_ids": list(sorted(all_brick_ids)),
            "source_files": [d["source_file"] for d in unique_docs.values()]
        },
        "raw_excerpts": raw_excerpts,
        "coverage_status": "ASSEMBLED",
        "extracted_facts": [], # Placeholder
        "decisions": [],       # Placeholder
        "constraints": [],     # Placeholder
        "edge_cases": [],      # Placeholder
        "artifact_type": "TOPIC_COGNITION_V1"
    }
    
    # 4. Persistence Phase
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    # IMPORTANT: artifact_payload must remain time-independent to keep content addressing stable
    artifact_hash = _calculate_content_hash(artifact_payload)
    
    # Add metadata envelope
    final_artifact = {
        "artifact_id": artifact_hash,
        "created_at": timestamp,
        "query": topic_query,
        "derived_from": list(sorted(all_brick_ids)),
        "payload": artifact_payload
    }
    
    slug = _get_slug(topic_query)
    filename = f"{slug}_{artifact_hash[:12]}_{int(datetime.now().timestamp())}.json"
    output_path = os.path.join(ARTIFACTS_DIR, filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_artifact, f, ensure_ascii=False, indent=2)
        
    print(f"DEBUG: Assembled topic '{topic_query}' to {output_path}")

    # 5. Graph Linkage
    try:
        graph = GraphManager()
        
        # Node: Artifact
        graph.register_node("artifact", artifact_hash, {
            "topic": topic_query,
            "created_at": timestamp,
            "type": "TOPIC_COGNITION_V1"
        })
        
        # Node: Topic (create slugified topic node)
        topic_node_id = f"topic_{slug}"
        graph.register_node("topic", topic_node_id, {
            "topic_slug": slug,
            "original_query": topic_query
        })

        # Edge: Topic -> Artifact
        graph.register_edge(
            src=("topic", topic_node_id),
            dst=("artifact", artifact_hash),
            edge_type="ASSEMBLED_IN"
        )
        
        # Edges: Artifact -> Bricks
        for brick_id in all_brick_ids:
            # Ensure brick node exists (if we want to be strict, but recall usually implies it exists in index)
            # We register it just in case our graph doesn't have it yet
            graph.register_node("brick", brick_id, {})
            
            graph.register_edge(
                src=("artifact", artifact_hash),
                dst=("brick", brick_id),
                edge_type="DERIVED_FROM"
            )
            
    except Exception as e:
        print(f"WARN: Graph linkage failed: {e}")

    return output_path
