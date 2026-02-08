import os

# Base paths
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PACKAGE_ROOT))

# Data paths
DATA_DIR = os.path.join(REPO_ROOT, "data")
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
INDEX_PATH = os.path.join(DATA_DIR, "index", "index.faiss")
BRICK_IDS_PATH = os.path.join(DATA_DIR, "brick_ids.json")
GRAPH_DB_PATH = os.path.join(REPO_ROOT, "src", "nexus", "graph", "graph.db")
SYNC_SCHEMA_PATH = os.path.join(REPO_ROOT, "src", "nexus", "graph", "schema_sync.sql")
AUDIT_LOG_PATH = os.path.join(REPO_ROOT, "services", "cortex", "phase3_audit_trace.jsonl")

# Output paths (for synchronization/extraction)
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "nexus")
TREES_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "trees")

# Constants
MAX_FILENAME_LENGTH = 120
DEFAULT_WALL_SIZE = 32000
