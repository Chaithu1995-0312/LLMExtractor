import os
from celery import Celery

# Configure Celery
# Default to localhost Redis if not specified
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "nexus_cortex",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.cortex.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker settings
    worker_concurrency=2, # Keep low for local dev
    worker_prefetch_multiplier=1
)

if __name__ == "__main__":
    celery_app.start()
