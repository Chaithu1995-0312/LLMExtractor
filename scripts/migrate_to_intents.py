import json
import os
import sys
import uuid
# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from nexus.graph.manager import GraphManager
from nexus.graph.schema import Source, Intent, Edge, EdgeType, IntentLifecycle, IntentType, ScopeNode

def migrate_conversations(json_path: str, db_path: str = None):
    print(f"🚀 Starting migration from {json_path}")
    manager = GraphManager(db_path)
    
    if not os.path.exists(json_path):
        print(f"❌ File not found: {json_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    print(f"📦 Loaded {len(data)} conversations. Processing...")
    
    # 0. Create Default Global Scope
    # Check if exists first? manager.add_scope is idempotent on ID, but we generate new ID if we create new ScopeNode.
    # Let's verify if we want a fixed ID for GLOBAL scope.
    # Ideally yes. Let's force a known ID for migration or just create one.
    # Since we don't have a fixed ID constant, we'll create one and reuse it.
    
    global_scope = ScopeNode(
        name="GLOBAL",
        description="Global scope for migrated intents",
        metadata={"created_by": "migration"}
    )
    # We might want to query if a scope named "GLOBAL" exists? 
    # For now, just add it. If we run migration multiple times, we might get duplicates unless we fix ID.
    # Let's assume migration is a one-off or fresh start.
    manager.add_scope(global_scope)
    print(f"🌐 Created Scope: GLOBAL ({global_scope.id})")

    count_sources = 0
    count_intents = 0
    
    for conv in data:
        conv_id = conv.get("conversation_id", str(uuid.uuid4()))
        title = conv.get("title", "Untitled")
        
        # Create a generic intent for the whole conversation (optional, but good for loose structure)
        # Or better, per message.
        # User said: "All extracted intents start as LOOSE".
        
        for msg in conv.get("messages", []):
            role = msg.get("role")
            content = msg.get("content")
            
            if not content:
                continue
                
            # 1. Create Source Node
            source = Source(
                content=content,
                origin_file="conversations.json",
                metadata={
                    "conversation_id": conv_id,
                    "role": role,
                    "model": msg.get("model_name")
                }
            )
            manager.add_source(source)
            count_sources += 1
            
            # 2. Extract Intent (Heuristic / Placeholder)
            # For now, we wrap the whole message as a LOOSE intent or just leave it as Source.
            # The plan said "Migration adds nodes... extract intents". 
            # We will create a LOOSE intent for non-trivial user messages or system outputs.
            # Heuristic: If it looks like a rule or structure? 
            # For safety, let's create a LOOSE intent for every Assistant message that is substantial.
            
            if role == "assistant" and len(content) > 50:
                intent_stmt = content[:100] + "..." # Simplified statement
                intent = Intent(
                    statement=intent_stmt,
                    lifecycle=IntentLifecycle.LOOSE,
                    intent_type=IntentType.FACT, # Default
                    metadata={"original_source_id": source.id}
                )
                manager.add_intent(intent)
                
                # Link Source -> Intent (Derived From)
                edge = Edge(
                    source_id=intent.id,
                    target_id=source.id,
                    edge_type=EdgeType.DERIVED_FROM
                )
                manager.add_typed_edge(edge)
                
                # Link Intent -> Scope (Applies To)
                edge_scope = Edge(
                    source_id=intent.id,
                    target_id=global_scope.id,
                    edge_type=EdgeType.APPLIES_TO
                )
                manager.add_typed_edge(edge_scope)
                
                count_intents += 1

    print(f"✅ Migration Complete.")
    print(f"   - Sources: {count_sources}")
    print(f"   - Intents: {count_intents}")

if __name__ == "__main__":
    # Default path assuming script is in scripts/ and json in root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "conversations.json")
    
    migrate_conversations(json_path)
