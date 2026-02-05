import os
import sys
# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from nexus.graph.manager import GraphManager
from nexus.graph.projection import project_intent, WallCell, get_intent_edges

def generate_mermaid_projection(db_path: str = None):
    manager = GraphManager(db_path)
    
    # 1. Fetch All Data
    print("Fetching Graph Data...")
    intents = manager.get_all_intents()
    edges = manager.get_all_edges()
    scopes = manager.get_all_scopes()
    sources = manager.get_all_sources()
    
    print(f"Loaded {len(intents)} intents, {len(edges)} edges.")
    
    # 2. Project Intents to Walls
    wall_buckets = {cell: [] for cell in WallCell}
    
    # Create edge lookup map ? Or just pass all edges?
    # project_intent takes list of edges. Filtering inside loop is O(N*M).
    # Optimization: Pre-filter edges per intent.
    # Actually, get_intent_edges is a helper but project_intent takes a list.
    # The current implementation of project_intent expects a list of edges.
    # I should optimize project_intent or pass only relevant edges.
    # Let's map intent_id -> edges list first.
    
    intent_edges_map = {i.id: [] for i in intents}
    for e in edges:
        if e.source_id in intent_edges_map:
            intent_edges_map[e.source_id].append(e)
        if e.target_id in intent_edges_map:
            intent_edges_map[e.target_id].append(e)
            
    # Project
    for intent in intents:
        relevant_edges = intent_edges_map.get(intent.id, [])
        cell = project_intent(intent, relevant_edges, scopes, sources)
        wall_buckets[cell].append(intent)
        
    # 3. Generate Mermaid
    lines = ["graph TD"]
    
    # Define Subgraphs for Walls
    # 3x3 Grid Layout in Mermaid is hard, but we can use subgraphs.
    # We can try to enforce layout with hidden edges if needed, but simple subgraphs are fine.
    
    for cell in WallCell:
        cell_name = cell.name.replace("_", " ").title()
        lines.append(f'    subgraph Wall_{cell.value} ["{cell.value}. {cell_name}"]')
        
        for intent in wall_buckets[cell]:
            # sanitize id and label
            safe_id = intent.id.replace("-", "")
            label = (intent.statement[:30] + "...") if len(intent.statement) > 30 else intent.statement
            label = label.replace('"', "'")
            lines.append(f'        {safe_id}["{label}"]')
            
        lines.append("    end")
        
    # Add Edges (OVERRIDES, CONFLICTS)
    # Only draw edges between displayed intents
    displayed_ids = {i.id for i in intents}
    
    for edge in edges:
        if edge.source_id in displayed_ids and edge.target_id in displayed_ids:
            # We only care about Intent-Intent edges for the Wall View usually
            # OVERRIDES, CONFLICTS, REFINES, DEPENDS_ON
            
            # Map edge types to styles
            style = "-->"
            if edge.edge_type.value == "overrides":
                style = "==>|OVERRIDES|"
            elif edge.edge_type.value == "conflicts_with":
                style = "-.->|CONFLICTS|"
            
            src_safe = edge.source_id.replace("-", "")
            tgt_safe = edge.target_id.replace("-", "")
            
            lines.append(f"    {src_safe} {style} {tgt_safe}")
            
    mermaid_code = "\n".join(lines)
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "wall_projection.mmd")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mermaid_code)
        
    print(f"✅ Projection generated at {output_path}")

if __name__ == "__main__":
    generate_mermaid_projection()
