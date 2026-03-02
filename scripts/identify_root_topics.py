import json
import os

def analyze_root_topics():
    nodes_path = 'src/nexus/graph/nodes.json'
    edges_path = 'src/nexus/graph/edges.json'
    anchors_path = 'src/nexus/graph/anchors.override.json'

    with open(nodes_path, 'r') as f:
        nodes = json.load(f)
    with open(edges_path, 'r') as f:
        edges = json.load(f)
    if os.path.exists(anchors_path):
        with open(anchors_path, 'r') as f:
            anchors_data = json.load(f)
            anchors_overrides = anchors_data.get('overrides', [])
    else:
        anchors_overrides = []

    # Map for easy lookup
    node_map = {n['id']: n for n in nodes}
    
    # Calculate connections
    adjacency = {}
    for edge in edges:
        s, t = edge['source'], edge['target']
        adjacency.setdefault(s, set()).add(t)
        adjacency.setdefault(t, set()).add(s)

    # Process each node
    root_topics_map = {}
    
    # We are looking for high-level domains
    potential_roots = [n for n in nodes if n.get('type') in ['topic', 'TOPIC_COGNITION_V1', 'concept']]
    
    for node in potential_roots:
        node_id = node['id']
        
        # Determine label and canonical ID
        label = node.get('topic') or node.get('topic_slug') or node.get('label') or node.get('original_query')
        if not label:
            continue
            
        # Canonical label for merging (e.g., 'nexus memory' vs 'nexus-memory')
        canonical_label = label.lower().replace('-', ' ')
        
        # Hard anchors
        hard_anchors = [a for a in anchors_overrides if a.get('concept_id') == node_id and a.get('action') == 'promote']
        hard_anchor_count = len(hard_anchors)
        
        # Soft anchors
        soft_bricks = node.get('bricks', [])
        soft_anchor_count = len(soft_bricks)
        
        # Connected node count
        connected_nodes = adjacency.get(node_id, set())
        connected_node_count = len(connected_nodes)
        
        # Estimated brick count
        bricks = set(soft_bricks)
        if node.get('type') == 'topic':
            assembled_in = [e['target'] for e in edges if e['source'] == node_id and e['type'] == 'ASSEMBLED_IN']
            for cogn_id in assembled_in:
                cogn_bricks = [e['target'] for e in edges if e['source'] == cogn_id and e['type'] == 'DERIVED_FROM']
                bricks.update(cogn_bricks)
        if node.get('type') == 'TOPIC_COGNITION_V1':
             cogn_bricks = [e['target'] for e in edges if e['source'] == node_id and e['type'] == 'DERIVED_FROM']
             bricks.update(cogn_bricks)

        estimated_brick_count = len(bricks)
        
        # Root Topic Criteria
        if estimated_brick_count >= 5 or connected_node_count >= 3 or hard_anchor_count > 0:
            if canonical_label not in root_topics_map or estimated_brick_count > root_topics_map[canonical_label]['estimated_brick_count']:
                root_topics_map[canonical_label] = {
                    "node_id": node_id,
                    "label": label,
                    "hard_anchor_count": hard_anchor_count,
                    "soft_anchor_count": soft_anchor_count,
                    "connected_node_count": connected_node_count,
                    "estimated_brick_count": estimated_brick_count
                }

    final_roots = list(root_topics_map.values())
    final_roots.sort(key=lambda x: x['estimated_brick_count'], reverse=True)
    
    print(json.dumps(final_roots, indent=2))

if __name__ == "__main__":
    analyze_root_topics()
