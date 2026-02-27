# ============================================================
# ARCHIVED — DO NOT USE
# ============================================================
# This file is a remnant of the Neo4j integration which has
# been fully replaced by the Postgres graph layer
# (graph.nodes / graph.edges schema).
#
# Audit confirmed: zero active imports in src/ or services/.
# The one import in src/nexus/sync/ingest_history.py is
# wrapped in a try/except and will be superseded separately.
#
# Kept here for historical reference ONLY.
# Do NOT import or instantiate anything below this line.
# For graph operations use: src/nexus/graph/manager.py
# ============================================================
raise ImportError(
    "neo4j_manager is ARCHIVED. "
    "Use nexus.graph.manager (Postgres-backed) instead."
)

# ── original code preserved below for archaeology only ──────

from neo4j import GraphDatabase, exceptions
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class Neo4jGraphManager:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            keep_alive=True
        )
        self.verify_connectivity()

    def verify_connectivity(self):
        try:
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j cluster.")
        except exceptions.ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to verify Neo4j connectivity: {e}")
            raise

    def close(self):
        self.driver.close()

    def add_intent(self, intent_id: str, statement: str, metadata: Dict = None):
        with self.driver.session() as session:
            session.execute_write(self._create_intent_node, intent_id, statement, metadata or {})

    @staticmethod
    def _create_intent_node(tx, intent_id, statement, metadata):
        query = (
            "MERGE (i:Intent {id: $id}) "
            "SET i.statement = $statement, i.metadata = $metadata, i.last_updated = datetime() "
            "RETURN i"
        )
        tx.run(query, id=intent_id, statement=statement, metadata=json.dumps(metadata))

    def add_relationship(self, src_id: str, target_id: str, rel_type: str):
        with self.driver.session() as session:
            session.execute_write(self._create_relationship, src_id, target_id, rel_type)

    @staticmethod
    def _create_relationship(tx, src_id, target_id, rel_type):
        query = (
            "MATCH (a {id: $src_id}), (b {id: $target_id}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            "RETURN r"
        )
        tx.run(query, src_id=src_id, target_id=target_id)

    def find_lineage(self, intent_id: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            return session.execute_read(self._get_lineage, intent_id)

    @staticmethod
    def _get_lineage(tx, intent_id):
        query = (
            "MATCH (i:Intent {id: $id}) "
            "OPTIONAL MATCH p=(i)-[:OVERRIDES*]->(legacy:Intent) "
            "RETURN i, nodes(p) AS lineage_nodes "
            "ORDER BY length(p) DESC LIMIT 1"
        )
        result = tx.run(query, id=intent_id)
        record = result.single()
        if not record:
            return []
        nodes = record["lineage_nodes"]
        if not nodes:
            i_node = record["i"]
            return [{"id": i_node["id"], "statement": i_node["statement"]}]
        return [{"id": n["id"], "statement": n["statement"]} for n in nodes]

    def check_for_cycle(self, src_id: str, target_id: str, rel_type: str = "OVERRIDES") -> bool:
        with self.driver.session() as session:
            return session.execute_read(self._has_path, target_id, src_id, rel_type)

    @staticmethod
    def _has_path(tx, start_id, end_id, rel_type):
        query = (
            "MATCH (a {id: $start_id}), (b {id: $end_id}) "
            f"MATCH p=(a)-[:{rel_type}*]->(b) "
            "RETURN count(p) > 0 AS has_path"
        )
        result = tx.run(query, start_id=start_id, end_id=end_id)
        record = result.single()
        return record["has_path"] if record else False
