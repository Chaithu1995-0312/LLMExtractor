import os

# Base paths
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PACKAGE_ROOT))

# Data paths
DATA_DIR = os.path.join(REPO_ROOT, "data")
INDEX_PATH = os.path.join(DATA_DIR, "index", "index.faiss")
BRICK_IDS_PATH = os.path.join(DATA_DIR, "brick_ids.json")

# Output paths (for synchronization/extraction)
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "output", "nexus")

# Constants
MAX_FILENAME_LENGTH = 120
DEFAULT_WALL_SIZE = 32000
