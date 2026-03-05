import json
import os
import hashlib
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from nexus.graph.manager import GraphManager
from nexus.compiler.conflict_resolver import ConflictResolver
from nexus.compiler.packaging import ZipPackager
from nexus.config import DATA_DIR

SYNTHESIS_GUARD_PROMPT = """
SYNTHESIS GUARD RULES:
1. You may ONLY summarize based on provided brick IDs.
2. You MAY NOT introduce new entities or logic not present in bricks.
3. You MUST include traceability tags [brick_id: XXXXX] for every claim.
4. If no brick evidence exists for a section, state "No evidence found."
"""

class SynthesisGuardException(Exception):
    """Raised when synthesis violates guardrail rules."""
    pass

class TopicCompiler:
    """
    Topic Canonical Compiler (TCC) for Nexus.
    Generates a deterministic document package for a given Topic.
    """

    def __init__(self, db_path: str = None):
        self.graph_manager = GraphManager(db_path)
        self.conflict_resolver = ConflictResolver()

    def run(self, topic_node_id: str, mode: str = "SYNTHESIS") -> str:
        """
        Main execution flow for Topic Canonical Compilation.
        Returns path to generated ZIP package.
        """
        print(f"[TopicCompiler] Running for topic: {topic_node_id} (Mode: {mode})")
        
        # 1-7. Compilation Core
        documents, manifest, expanded_nodes = self._compile_core(topic_node_id, mode)
        
        # 8. Packaging
        pkg_path = ZipPackager.create_package(topic_node_id, documents, manifest)
        
        return pkg_path

    def run_in_memory(self, topic_node_id: str, mode: str = "SYNTHESIS") -> Any:
        """
        Runs the compilation and returns an in-memory ZIP buffer.
        """
        print(f"[TopicCompiler] Running in-memory for topic: {topic_node_id} (Mode: {mode})")
        
        # 1-7. Compilation Core
        documents, manifest, _ = self._compile_core(topic_node_id, mode)
        
        # 8. In-Memory Packaging
        zip_buffer = ZipPackager.create_in_memory_package(topic_node_id, documents)
        return zip_buffer

    def _compile_core(self, topic_node_id: str, mode: str) -> Tuple[List[Dict], Dict, Set[str]]:
        """
        Encapsulated compilation logic for reuse.
        """
        # 1. Topic Identification
        topic_info = self.graph_manager.get_node(topic_node_id)
        if not topic_info:
            raise ValueError(f"Topic node {topic_node_id} not found")
        
        # 2. VectorRecall
        statement = topic_info[1].get("statement") or topic_info[1].get("name") or ""
        initial_bricks = self.graph_manager.semantic_query(statement, top_k=50)
        
        # 3. GraphExpansion (Depth = 2)
        expanded_nodes = self._expand_graph(topic_node_id)
        
        # 4. Anchor Resolution & Collection (Filtered for Killed)
        all_bricks = self._collect_bricks(expanded_nodes, initial_bricks)
        
        # 5. Conflict Resolution
        resolution = self.conflict_resolver.resolve(all_bricks)
        resolved_bricks = resolution["resolved_bricks"]
        conflicts = resolution.get("conflicts", [])
        
        # 6. Document Assembly
        current_mode = mode
        if current_mode == "SYNTHESIS":
            try:
                documents = self._synthesize_with_guard(resolved_bricks, conflicts)
            except SynthesisGuardException:
                print("[TopicCompiler] Synthesis guard failed. Falling back to STRICT mode.")
                current_mode = "STRICT"
                documents = self._assemble_documents(resolved_bricks, current_mode, conflicts)
        else:
            documents = self._assemble_documents(resolved_bricks, current_mode, conflicts)
        
        # 7. Manifest Generation with Audit Hash
        sorted_brick_ids = sorted([b["id"] for b in resolved_bricks])
        audit_hash = hashlib.sha256("".join(sorted_brick_ids).encode()).hexdigest()
        
        manifest = {
            "topic_node_id": topic_node_id,
            "source_brick_ids": sorted_brick_ids,
            "graph_node_ids": sorted(list(expanded_nodes)),
            "compilation_mode": current_mode,
            "depth": 2,
            "logical_timestamp": "2026-03-02T12:00:00Z", # Logical fixed for determinism
            "audit_hash": audit_hash,
            "synthesis_guard": SYNTHESIS_GUARD_PROMPT if current_mode == "SYNTHESIS" else "STRICT_ONLY"
        }
        
        return documents, manifest, expanded_nodes

    def _expand_graph(self, start_node_id: str) -> Set[str]:
        """
        Hardened Depth = 2 expansion rules with cycle prevention.
        Depth 1: All connected nodes.
        Depth 2: Hard Anchors only.
        """
        visited = {start_node_id}
        depth1_nodes = set()

        # Depth 1: Include all connected
        d1_edges = self.graph_manager.get_edges_for_node(start_node_id)
        # Deterministic sorting of edges
        d1_edges = sorted(d1_edges, key=lambda e: (e.source_id, e.target_id, e.edge_type.value))

        for edge in d1_edges:
            other_id = edge.target_id if edge.source_id == start_node_id else edge.source_id
            if other_id not in visited:
                visited.add(other_id)
                depth1_nodes.add(other_id)

        # Depth 2: Hard Anchors Only
        for d1_id in sorted(list(depth1_nodes)):
            d2_edges = self.graph_manager.get_edges_for_node(d1_id)
            # Deterministic sorting of edges
            d2_edges = sorted(d2_edges, key=lambda e: (e.source_id, e.target_id, e.edge_type.value))
            
            for edge in d2_edges:
                is_hard = edge.metadata.get("anchor_type") == "hard" or edge.edge_type.value == "hard_anchor"
                if is_hard:
                    other_id = edge.target_id if edge.source_id == d1_id else edge.source_id
                    if other_id not in visited:
                        visited.add(other_id)

        return visited

    def _collect_bricks(self, node_ids: Set[str], initial_bricks: List[Dict]) -> List[Dict]:
        """
        Gathers bricks and filters out 'Killed' lifecycle state immediately.
        """
        # 1. Filter initial semantic recall
        brick_map = {
            b["id"]: b for b in initial_bricks 
            if b.get("type") == "brick" and b.get("lifecycle") != "Killed"
        }
        
        # 2. Add bricks from graph traversal
        for node_id in node_ids:
            node = self.graph_manager.get_node(node_id)
            if node and node[0] == "brick":
                data = node[1]
                if data.get("lifecycle") != "killed" and data.get("lifecycle") != "Killed":
                    data["id"] = node_id
                    brick_map[node_id] = data
                
        return list(brick_map.values())

    def _synthesize_with_guard(self, bricks: List[Dict], conflicts: List[Dict] = None) -> List[Dict]:
        """
        Synthesizes documents with LLM and enforces Synthesis Guard Rules.
        """
        docs = self._assemble_documents(bricks, "SYNTHESIS", conflicts)
        
        for doc in docs:
            content = doc["content"]
            paragraphs = [p for p in content.split("\n\n") if p.strip() and not p.startswith("#") and not p.startswith("---") and not p.startswith("- Brick ID")]
            
            for p in paragraphs:
                if "No evidence found" in p:
                    continue
                # a) Every paragraph references [brick_id: XXXXX]
                if not re.search(r"\[brick_id: [a-zA-Z0-9_\-]+\]", p):
                    raise SynthesisGuardException(f"Paragraph missing brick reference: {p[:50]}...")
                
                # b) No entities introduced that do not exist in bricks (Simplified check)
                citations = re.findall(r"\[brick_id: ([a-zA-Z0-9_\-]+)\]", p)
                valid_ids = {b["id"] for b in bricks}
                for cite in citations:
                    if cite not in valid_ids:
                        raise SynthesisGuardException(f"Invalid brick reference: {cite}")

        return docs

    def _assemble_documents(self, bricks: List[Dict], mode: str, conflicts: List[Dict] = None) -> List[Dict]:
        """
        Deterministic Document Assembly.
        Intent-Aware: Bricks are grouped by Intent within each section.
        """
        # Group bricks into 8 virtual documents as per TOPIC_OVERVIEW
        doc_titles = [
            "Overview", "Architecture", "Data Models", "Interfaces", 
            "Security", "Operations", "Compliance", "Roadmap"
        ]
        
        assembled_docs = []
        # Sort bricks for determinism
        sorted_bricks = sorted(bricks, key=lambda x: x["id"])
        
        # Fetch Intent Names for grouping
        intent_ids = list(set(b.get("intent_id") for b in bricks if b.get("intent_id")))
        intent_map = {}
        if intent_ids:
            rows = self.graph_manager._fetch_all(
                "SELECT id, data FROM graph.nodes WHERE id = ANY(%s)",
                (intent_ids,)
            )
            for i_id, i_data_raw in rows:
                i_data = i_data_raw if isinstance(i_data_raw, dict) else json.loads(i_data_raw)
                intent_map[i_id] = i_data.get("name") or i_id

        # Round-robin distribution for demo purposes in Phase 2
        for i, title in enumerate(doc_titles):
            doc_bricks = sorted_bricks[i::8]
            content = f"# {title}\n\n"
            
            # Inject Multi-Frozen Conflict section in the first doc (Overview)
            if i == 0 and conflicts:
                for conflict in conflicts:
                    if conflict["type"] == "MULTI_FROZEN":
                        content += "## MULTI-FROZEN CONFLICT DETECTED\n"
                        content += "Bricks involved:\n"
                        for bid in conflict["brick_ids"]:
                            content += f"- {bid}\n"
                        content += "\nResolution: Unresolved. Manual review required.\n\n"

            if not doc_bricks:
                content += "No data available for this section.\n"
            else:
                # Group by Intent
                bricks_by_intent = {}
                for b in doc_bricks:
                    i_id = b.get("intent_id", "unknown")
                    if i_id not in bricks_by_intent:
                        bricks_by_intent[i_id] = []
                    bricks_by_intent[i_id].append(b)
                
                for i_id, i_bricks in sorted(bricks_by_intent.items()):
                    if i_id != "unknown":
                        content += f"## Intent: {intent_map.get(i_id, i_id)}\n\n"
                    
                    for b in i_bricks:
                        text = b.get("statement") or b.get("content") or ""
                        content += f"{text} [brick_id: {b['id']}]\n\n"
                
                content += "---\n## Footnotes\n"
                for b in doc_bricks:
                    content += f"- Brick ID: {b['id']}\n"
            
            assembled_docs.append({
                "title": title,
                "filename": f"{title.lower().replace(' ', '_')}.md",
                "content": content
            })
            
        return assembled_docs
