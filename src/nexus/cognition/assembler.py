import json
import os
import hashlib
import dspy
from nexus.cognition.dspy_modules import CognitiveExtractor
import re
from datetime import datetime, timezone
from typing import Dict, List, Set, Any
from nexus.ask.recall import recall_bricks_readonly, get_recall_brick_metadata
from nexus.config import DEFAULT_OUTPUT_DIR
from nexus.graph.manager import GraphManager
from nexus.graph.schema import IntentLifecycle, EdgeType
from nexus.rerank.cross_encoder import CrossEncoderReranker

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
    6. Register provenance in the Knowledge Graph with Monotonic Conflict Resolution.
    
    Returns:
        Path to the saved artifact.
    """
    # 1. Recall Phase
    print(f"DEBUG: recalling bricks for '{topic_query}'")
    candidates = recall_bricks_readonly(topic_query, k=15)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 1.1 Handle empty recall
    if not candidates:
        print("DEBUG: No bricks found. Returning empty artifact.")
        artifact_payload = {
            "topic": topic_query,
            "provenance": {"brick_ids": [], "source_files": []},
            "raw_excerpts": [],
            "coverage_status": "NO_RECALL_MATCHES",
            "extracted_facts": [],
            "decisions": [],
            "constraints": [],
            "edge_cases": [],
            "artifact_type": "TOPIC_COGNITION_V1"
        }
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
    unique_docs: Dict[str, Dict] = {}
    for cand in candidates:
        brick_id = cand["brick_id"]
        meta = get_recall_brick_metadata(brick_id)
        if not meta or "source_file" not in meta:
            continue
        source_path = meta["source_file"]
        try:
            tree_data = _load_tree_file(source_path)
            doc_hash = _calculate_content_hash(tree_data)
            if doc_hash not in unique_docs:
                unique_docs[doc_hash] = {
                    "source_file": source_path,
                    "full_tree": tree_data,
                    "brick_ids": set(),
                    "spans": []
                }
            unique_docs[doc_hash]["brick_ids"].add(brick_id)
            if "source_span" in meta:
                span = meta["source_span"]
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
        normalized = []
        for msg in tree.get("messages", []):
            content = msg.get("content", "")
            blocks = []
            if isinstance(content, str):
                blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
            elif isinstance(content, list):
                blocks = [str(b).strip() for b in content if str(b).strip()]
            normalized.append({
                "message_id": msg.get("message_id") or msg.get("id"),
                "role": msg.get("role"),
                "created_at": msg.get("created_at"),
                "blocks": [{"index": i, "text": b} for i, b in enumerate(blocks)]
            })
        raw_excerpts.append({
            "source_file": doc_info["source_file"],
            "coverage": {"spans": doc_info["spans"]},
            "conversation": normalized
        })
    
    all_brick_ids = set()
    for doc in unique_docs.values():
        all_brick_ids.update(doc["brick_ids"])

    # 3.5 Cognitive Extraction via DSPy
    aggregated_context = ""
    for excerpt in raw_excerpts:
        for msg in excerpt["conversation"]:
            for block in msg["blocks"]:
                aggregated_context += block["text"] + "\n\n"

    extractor = CognitiveExtractor()
    try:
        prediction = extractor.forward(context=aggregated_context)
        facts = prediction.facts if isinstance(prediction.facts, list) else [prediction.facts]
        mermaid = prediction.mermaid if isinstance(prediction.mermaid, list) else [prediction.mermaid]
        latex = prediction.latex if isinstance(prediction.latex, list) else [prediction.latex]
    except Exception as e:
        print(f"DSPy extraction failed: {e}")
        facts, mermaid, latex = [], [], []

    artifact_payload = {
        "topic": topic_query,
        "provenance": {
            "brick_ids": list(sorted(all_brick_ids)),
            "source_files": [d["source_file"] for d in unique_docs.values()]
        },
        "raw_excerpts": raw_excerpts,
        "coverage_status": "ASSEMBLED",
        "extracted_facts": facts,
        "visuals": {"mermaid": mermaid, "latex": latex},
        "decisions": [], "constraints": [], "edge_cases": [],
        "artifact_type": "TOPIC_COGNITION_V1"
    }
    
    # 4. Persistence Phase
    artifact_hash = _calculate_content_hash(artifact_payload)
    final_artifact = {
        "artifact_id": artifact_hash,
        "created_at": timestamp,
        "query": topic_query,
        "derived_from": list(sorted(all_brick_ids)),
        "payload": artifact_payload
    }
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    slug = _get_slug(topic_query)
    filename = f"{slug}_{artifact_hash[:12]}_{int(datetime.now().timestamp())}.json"
    output_path = os.path.join(ARTIFACTS_DIR, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_artifact, f, ensure_ascii=False, indent=2)
        
    print(f"DEBUG: Assembled topic '{topic_query}' to {output_path}")

    # 5. Graph Linkage & Monotonic Conflict Resolution
    try:
        graph = GraphManager()
        reranker = CrossEncoderReranker()
        
        # Node: Artifact
        graph.register_node("artifact", artifact_hash, {
            "topic": topic_query,
            "created_at": timestamp,
            "type": "TOPIC_COGNITION_V1"
        })
        
        # Node: Topic (MERGE operation using slug-based ID)
        topic_node_id = f"topic_{slug}"
        graph.register_node("topic", topic_node_id, {
            "topic_slug": slug,
            "original_query": topic_query,
            "last_assembled": timestamp
        }, merge=True)

        # Edge: Topic -> Artifact (Monotonic growth)
        graph.register_edge(
            src=("topic", topic_node_id),
            dst=("artifact", artifact_hash),
            edge_type=EdgeType.ASSEMBLED_IN
        )
        
        # Resolve conflicts with existing intents for this topic
        existing_intents = graph.get_intents_by_topic(topic_node_id)
        for fact in facts:
            fact_id = hashlib.sha256(fact.encode()).hexdigest()[:16]
            is_overridden = False
            
            # Temporal Confidence logic: 
            # 1. Existing FROZEN intents are anchors.
            # 2. Existing FORMING intents can be superseded by newer FORMING data if similarity is high.
            for existing in existing_intents:
                rank_res = reranker.rank(fact, [{"brick_text": existing.statement}])
                similarity = rank_res[0]["final_score"] if rank_res else 0
                
                if similarity > 0.85:
                    if existing.lifecycle == IntentLifecycle.FROZEN:
                        print(f"DEBUG: Fact '{fact}' is similar to FROZEN intent '{existing.id}'. Respecting anchor.")
                        is_overridden = True
                        graph.register_node("intent", fact_id, {"statement": fact, "lifecycle": IntentLifecycle.FORMING})
                        graph.register_edge(
                            src=("intent", existing.id),
                            dst=("intent", fact_id),
                            edge_type=EdgeType.OVERRIDES
                        )
                        break
                    elif existing.lifecycle == IntentLifecycle.FORMING:
                        # Tie-break: Newer data overrides older FORMING data if similarity is high
                        print(f"DEBUG: Fact '{fact}' supersedes existing FORMING intent '{existing.id}'.")
                        graph.register_node("intent", fact_id, {"statement": fact, "lifecycle": IntentLifecycle.FORMING})
                        graph.register_edge(
                            src=("intent", fact_id),
                            dst=("intent", existing.id),
                            edge_type=EdgeType.OVERRIDES
                        )
                        # We don't break here, we might override multiple forming intents
            
            if not is_overridden:
                graph.register_node("intent", fact_id, {"statement": fact, "lifecycle": IntentLifecycle.FORMING})
                # Link Intent to Topic
                graph.register_edge(
                    src=("topic", topic_node_id),
                    dst=("intent", fact_id),
                    edge_type=EdgeType.ASSEMBLED_IN
                )
        
        for brick_id in all_brick_ids:
            graph.register_node("brick", brick_id, {})
            graph.register_edge(
                src=("artifact", artifact_hash),
                dst=("brick", brick_id),
                edge_type=EdgeType.DERIVED_FROM
            )
            
    except Exception as e:
        print(f"WARN: Graph linkage or conflict resolution failed: {e}")

    return output_path
