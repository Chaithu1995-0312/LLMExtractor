import sys
import os
import io
from datetime import datetime, timezone
from nexus.config import LOGS_DIR

class MultiWriter:
    """Simultaneously writes to multiple streams."""
    def __init__(self, *streams):
        self.streams = streams
        # Inherit encoding and errors from the primary stream (usually sys.stdout)
        self.encoding = getattr(streams[0], 'encoding', 'utf-8')
        self.errors = getattr(streams[0], 'errors', 'strict')

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        # We return False to ensure libraries don't attempt terminal-specific formatting
        # which can cause issues when redirecting to files.
        return False

def setup_logging(prefix: str):
    """
    Sets up logging to both console and a uniquely named file in LOGS_DIR.
    Returns the path to the log file.
    """
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_filename = f"{prefix}_{timestamp}.log"
    log_path = os.path.join(LOGS_DIR, log_filename)

    # Open the log file
    log_file = open(log_path, "w", encoding="utf-8")

    # Wrap stdout and stderr
    sys.stdout = MultiWriter(sys.stdout, log_file)
    sys.stderr = MultiWriter(sys.stderr, log_file)

    print(f"[{datetime.now(timezone.utc).isoformat()}] [LOGGING] Initialized. Log file: {log_path}")
    return log_path
