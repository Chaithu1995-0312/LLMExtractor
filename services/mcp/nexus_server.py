import os
import json
import asyncio
from mcp.server.fastmcp import FastMCP
from nexus.ask.recall import recall_bricks_readonly
from nexus.graph.manager import GraphManager

# Initialize FastMCP server
mcp = FastMCP("Nexus Knowledge Server")

@mcp.tool()
def search_nexus(query: str, limit: int = 5):
    """Search the Nexus vector index for relevant atomic bricks."""
    results = recall_bricks_readonly(query, k=limit)
    return results

@mcp.tool()
def get_graph_nodes(node_type: str = "intent"):
    """Get nodes from the Nexus knowledge graph by type."""
    gm = GraphManager()
    if node_type == "intent":
        return [vars(i) for i in gm.get_all_intents()]
    elif node_type == "scope":
        return {k: vars(v) for k, v in gm.get_all_scopes().items()}
    return []

@mcp.resource("nexus://config")
def get_config():
    """Access the Nexus system configuration."""
    from nexus.config import DEFAULT_OUTPUT_DIR
    return {
        "output_dir": DEFAULT_OUTPUT_DIR,
        "status": "OPERATIONAL",
        "version": "2026.1.0"
    }

if __name__ == "__main__":
    mcp.run()
