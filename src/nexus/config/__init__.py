"""Unified config exports for ``nexus.config`` imports.

This package-level module intentionally re-exports:
- Dynamic YAML-based loader helpers (agent/system config)
- Static path/constants used across legacy modules

Reason: both a legacy ``src/nexus/config.py`` module and this ``src/nexus/config/``
package exist. Python resolves ``import nexus.config`` to this package, so constants
must be exposed here for backward compatibility.
"""

from __future__ import annotations

import os

from .loader import get_agent_config, get_section_config, load_nexus_config


# Base paths
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(PACKAGE_ROOT))


# Data / runtime paths
DATABASE_URL = os.getenv("DATABASE_URL")
DATA_DIR = os.path.join(REPO_ROOT, "data")
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
INDEX_PATH = os.path.join(DATA_DIR, "index", "index.faiss")
BRICK_IDS_PATH = os.path.join(DATA_DIR, "brick_ids.json")
GRAPH_DB_PATH = os.path.join(REPO_ROOT, "src", "nexus", "graph", "graph.db")
SYNC_SCHEMA_PATH = os.path.join(REPO_ROOT, "src", "nexus", "graph", "schema_sync.sql")
AUDIT_LOG_PATH = os.path.join(REPO_ROOT, "services", "cortex", "phase3_audit_trace.jsonl")


# Output paths (synchronization / extraction)
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "nexus")
TREES_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "trees")


# Constants
MAX_FILENAME_LENGTH = 120
DEFAULT_WALL_SIZE = 32000
COGNITIVE_SHARD_LIMIT = int(os.getenv("COGNITIVE_SHARD_LIMIT", 10))


__all__ = [
    # Loader exports
    "load_nexus_config",
    "get_section_config",
    "get_agent_config",
    # Path/constants exports
    "PACKAGE_ROOT",
    "REPO_ROOT",
    "DATABASE_URL",
    "DATA_DIR",
    "LOGS_DIR",
    "INDEX_PATH",
    "BRICK_IDS_PATH",
    "GRAPH_DB_PATH",
    "SYNC_SCHEMA_PATH",
    "AUDIT_LOG_PATH",
    "DEFAULT_OUTPUT_DIR",
    "TREES_DIR",
    "MAX_FILENAME_LENGTH",
    "DEFAULT_WALL_SIZE",
    "COGNITIVE_SHARD_LIMIT",
]
