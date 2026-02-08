import json
from typing import List, Dict
from nexus.graph.manager import GraphManager
from nexus.graph.schema import Edge, EdgeType, Intent
from nexus.cognition.dspy_modules import RelationshipSynthesizer

def run_relationship_synthesis(topic_id: str = None, batch_size: int = 20):
    """
    Scan for intents and automatically discover relationships between them.
    
    Process:
    1. Fetch intents from GraphManager.
    2. Filter by topic (if provided) or recent additions.
    3. Pass to RelationshipSynthesizer (DSPy).
    4. Register discovered edges.
    """
    print(f"[SYNTHESIZER] Starting relationship synthesis (topic={topic_id})...")
    
    graph = GraphManager()
    
    # 1. Fetch intents
    if topic_id:
        intents = graph.get_intents_by_topic(topic_id)
    else:
        intents = graph.get_all_intents()
        
    if not intents:
        print("[SYNTHESIZER] No intents found for synthesis.")
        return 0

    # 2. Preparation (convert to dicts for DSPy)
    intent_payloads = [
        {"id": i.id, "statement": i.statement}
        for i in intents
    ]
    
    # 3. Batch Synthesis
    # Simple windowing for now
    discovered_count = 0
    synthesizer = RelationshipSynthesizer()
    
    # Pre-fetch existing edges to inform the synthesizer
    all_edges = graph.get_all_edges_raw()
    
    for i in range(0, len(intent_payloads), batch_size):
        batch = intent_payloads[i : i + batch_size]
        print(f"[SYNTHESIZER] Analyzing batch of {len(batch)} intents...")
        
        # Filter edges relevant to this batch (optimization)
        batch_ids = {item['id'] for item in batch}
        relevant_edges = [
            e for e in all_edges 
            if e['source'] in batch_ids or e['target'] in batch_ids
        ]
        
        try:
            prediction = synthesizer.forward(intents=batch, existing_edges=relevant_edges)
            relationships = prediction.relationships
            
            if not relationships:
                continue
                
            if isinstance(relationships, str):
                # DSPy sometimes returns strings if not strictly constrained
                try:
                    relationships = json.loads(relationships)
                except:
                    continue

            # 4. Register Edges
            for rel in relationships:
                try:
                    src_id = rel.get("source_id")
                    dst_id = rel.get("target_id")
                    rel_type = rel.get("type")
                    reason = rel.get("reason", "Automatically synthesized")
                    
                    if not src_id or not dst_id or not rel_type:
                        continue
                        
                    # Map to EdgeType enum
                    try:
                        etype = EdgeType(rel_type)
                    except ValueError:
                        # Fallback for LLM variations
                        if "DEPENDS" in rel_type.upper(): etype = EdgeType.DEPENDS_ON
                        elif "CONFLICT" in rel_type.upper(): etype = EdgeType.CONFLICTS_WITH
                        elif "OVERRIDE" in rel_type.upper(): etype = EdgeType.OVERRIDES
                        else: continue

                    edge = Edge(
                        source_id=src_id,
                        target_id=dst_id,
                        edge_type=etype,
                        metadata={"reason": reason, "synthesized": True}
                    )
                    
                    graph.add_typed_edge(edge)
                    discovered_count += 1
                    print(f"  [+] Discovered: {src_id} --({etype.value})--> {dst_id}")
                except Exception as e:
                    print(f"  [!] Failed to register edge: {e}")
                    
        except Exception as e:
            print(f"[SYNTHESIZER] Batch synthesis failed: {e}")

    print(f"[SYNTHESIZER] Synthesis complete. Discovered {discovered_count} relationships.")
    return discovered_count
