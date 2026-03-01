"""
nexus.memory.api_routes
========================
Flask route handlers for the Memory Layer.

Endpoints:
  POST /api/v1/memory/ingest        — ingest ChatGPT export JSON
  POST /api/v1/memory/retrieve      — semantic retrieval (no generation)
  POST /api/v1/memory/summarize     — retrieval + LLM summarization
  GET  /api/v1/memory/datasets      — list all datasets
  GET  /api/v1/memory/datasets/<id> — dataset detail
  POST /api/v1/memory/datasets/<id>/clear   — clear a dataset
  GET  /api/v1/memory/status        — index health
  POST /api/v1/bricks/from_memory   — promote chunk to Brick

Integration:
  Call register_memory_routes(app) from server.py AFTER creating the Flask app.
  The MemoryService is instantiated once and shared across requests.

Invariants:
  - All routes validate required fields and return 400 on missing input.
  - Ingestion is always async — the route returns 202 + dataset_id immediately,
    then the background thread updates the dataset status.
  - Generation is NEVER triggered by /retrieve.
  - /bricks/from_memory routes through MemoryService.promote_to_brick()
    which internally calls GraphManager — not direct DB access.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, Flask, jsonify, request

from nexus.memory.memory_service import MemoryService
from nexus.memory.health import MemoryHealthChecker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

memory_bp = Blueprint("memory", __name__, url_prefix="/api/v1/memory")
bricks_memory_bp = Blueprint("bricks_memory", __name__, url_prefix="/api/v1/bricks")

# Single shared service instance per process.
# ChromaDB and SQLite clients are thread-safe for reads; writes serialise
# through their own internal locks.
_service: MemoryService = None


def _get_service() -> MemoryService:
    """Lazy singleton for MemoryService (initialises on first request)."""
    global _service
    if _service is None:
        _service = MemoryService()
    return _service


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _error(message: str, code: int = 400) -> Any:
    return jsonify({"error": message, "status": "failed"}), code


def _ok(data: Dict) -> Any:
    return jsonify(data), 200


# ---------------------------------------------------------------------------
# POST /api/v1/memory/ingest
# ---------------------------------------------------------------------------

@memory_bp.route("/ingest", methods=["POST"])
def memory_ingest():
    """
    Ingest a ChatGPT export JSON.

    Accepts JSON body:
      {
        "export_data":     [...],           # Required: parsed conversations list
        "source_filename": "export.json",   # Optional display name
        "chunk_size":      800,             # Optional, default 800
        "overlap":         150              # Optional, default 150
      }

    OR multipart/form-data with "file" field (raw JSON file upload).

    Returns 202 Accepted immediately with dataset_id.
    Background thread performs the actual ingestion.
    """
    # Handle file upload.
    if request.content_type and "multipart" in request.content_type:
        file = request.files.get("file")
        if not file:
            return _error("No file provided in multipart upload.")
        try:
            export_data = json.load(file)
        except Exception as exc:
            return _error(f"Invalid JSON in uploaded file: {exc}")
        source_filename = file.filename or "upload.json"
        body: Dict = {}
    else:
        body = request.get_json(silent=True) or {}
        export_data = body.get("export_data")
        source_filename = body.get("source_filename", "chatgpt_export.json")

    if not export_data:
        return _error("export_data is required (JSON array of conversations).")

    if not isinstance(export_data, list):
        return _error("export_data must be a JSON array.")

    chunk_size = int(body.get("chunk_size", 800))
    overlap = int(body.get("overlap", 150))

    # Create a service with the requested chunk configuration.
    svc = MemoryService(chunk_size=chunk_size, overlap=overlap)

    # Create dataset record synchronously so we can return its ID immediately.
    from nexus.memory.dataset_manager import DatasetManager
    dm = DatasetManager()
    dataset = dm.create_dataset(source_filename=source_filename)
    dataset_id = dataset.dataset_id

    def _run_ingestion():
        try:
            logger.info(
                "[memory_ingest] Background ingestion started for dataset %s.", dataset_id
            )
            result = svc.ingest(
                export_data=export_data,
                source_filename=source_filename,
            )
            logger.info(
                "[memory_ingest] Ingestion complete: %s", result
            )
        except Exception as exc:
            logger.error(
                "[memory_ingest] Background ingestion error for %s: %s",
                dataset_id, exc, exc_info=True,
            )

    t = threading.Thread(target=_run_ingestion, daemon=True)
    t.start()

    return jsonify({
        "status": "accepted",
        "dataset_id": dataset_id,
        "source_filename": source_filename,
        "message": "Ingestion started. Poll GET /api/v1/memory/datasets/<id> for status.",
    }), 202


# ---------------------------------------------------------------------------
# POST /api/v1/memory/retrieve
# ---------------------------------------------------------------------------

@memory_bp.route("/retrieve", methods=["POST"])
def memory_retrieve():
    """
    Semantic retrieval — no LLM generation.

    Body:
      {
        "query":      "What did we discuss about...",   # Required
        "top_k":      10,                               # Optional, default 10
        "dataset_id": "abc-123",                        # Optional filter
        "role":       "user" | "assistant"              # Optional filter
      }

    Returns:
      {
        "chunks": [{"chunk_id", "text", "score", "metadata"}, ...],
        "retrieval_metadata": { ... }
      }
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()

    if not query:
        return _error("query is required and must be non-empty.")

    top_k = int(body.get("top_k", 10))
    dataset_id = body.get("dataset_id") or None
    role_filter = body.get("role") or None

    if top_k < 1 or top_k > 100:
        return _error("top_k must be between 1 and 100.")

    try:
        result = _get_service().retrieve(
            query=query,
            top_k=top_k,
            dataset_id=dataset_id,
            role_filter=role_filter,
        )
        return _ok(result)
    except Exception as exc:
        logger.error("[memory_retrieve] Error: %s", exc, exc_info=True)
        return _error(f"Retrieval failed: {exc}", code=500)


# ---------------------------------------------------------------------------
# POST /api/v1/memory/summarize
# ---------------------------------------------------------------------------

@memory_bp.route("/summarize", methods=["POST"])
def memory_summarize():
    """
    Retrieve context then summarize via llama3:latest.

    Body:
      {
        "query":      "...",    # Required
        "top_k":      8,        # Optional
        "dataset_id": "...",    # Optional
        "json_output": false    # Optional: force JSON schema response
      }

    Returns:
      {
        "summary":            str,
        "sources":            [...],
        "retrieval_metadata": {...},
        "model":              str,
        "status":             "success" | "failed" | "no_context"
      }
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()

    if not query:
        return _error("query is required.")

    top_k = int(body.get("top_k", 8))
    dataset_id = body.get("dataset_id") or None
    force_json = bool(body.get("json_output", False))

    try:
        result = _get_service().summarize(
            query=query,
            top_k=top_k,
            dataset_id=dataset_id,
            force_json=force_json,
        )
        status_code = 200 if result.get("status") == "success" else 207
        return jsonify(result), status_code
    except Exception as exc:
        logger.error("[memory_summarize] Error: %s", exc, exc_info=True)
        return _error(f"Summarization failed: {exc}", code=500)


# ---------------------------------------------------------------------------
# GET /api/v1/memory/datasets
# ---------------------------------------------------------------------------

@memory_bp.route("/datasets", methods=["GET"])
def list_datasets():
    """List all memory datasets (ordered by creation time desc)."""
    try:
        datasets = _get_service().list_datasets()
        return _ok({"datasets": datasets, "total": len(datasets)})
    except Exception as exc:
        logger.error("[list_datasets] Error: %s", exc)
        return _error(str(exc), code=500)


# ---------------------------------------------------------------------------
# GET /api/v1/memory/datasets/<dataset_id>
# ---------------------------------------------------------------------------

@memory_bp.route("/datasets/<dataset_id>", methods=["GET"])
def get_dataset(dataset_id: str):
    """Get a single dataset record by ID."""
    try:
        ds = _get_service().get_dataset(dataset_id)
        if not ds:
            return _error(f"Dataset {dataset_id} not found.", code=404)
        return _ok(ds)
    except Exception as exc:
        logger.error("[get_dataset] Error: %s", exc)
        return _error(str(exc), code=500)


# ---------------------------------------------------------------------------
# POST /api/v1/memory/datasets/<dataset_id>/clear
# ---------------------------------------------------------------------------

@memory_bp.route("/datasets/<dataset_id>/clear", methods=["POST"])
def clear_dataset(dataset_id: str):
    """
    Clear all vectors and chunks for a dataset.
    The dataset record is preserved with status CLEARED.
    """
    try:
        result = _get_service().clear_dataset(dataset_id)
        return _ok(result)
    except Exception as exc:
        logger.error("[clear_dataset] Error: %s", exc)
        return _error(str(exc), code=500)


# ---------------------------------------------------------------------------
# GET /api/v1/memory/status
# ---------------------------------------------------------------------------

@memory_bp.route("/status", methods=["GET"])
def memory_status():
    """
    Return memory layer health: index size, dataset count, embedder availability.
    """
    try:
        svc = _get_service()
        datasets = svc.list_datasets()
        index_size = svc.index_size()
        embedder_ok = svc._embedder.check_availability()

        return _ok({
            "index_size": index_size,
            "total_datasets": len(datasets),
            "complete_datasets": sum(1 for d in datasets if d["status"] == "COMPLETE"),
            "embedder_available": embedder_ok,
            "embedding_model": svc._embedder.model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.error("[memory_status] Error: %s", exc)
        return _error(str(exc), code=500)


# ---------------------------------------------------------------------------
# GET /api/v1/memory/health
# ---------------------------------------------------------------------------

@memory_bp.route("/health", methods=["GET"])
def memory_health():
    """
    Run the full MemoryHealthChecker suite and return the report.

    Performs 5 checks:
      1. index_size          — vector index non-empty
      2. count_reconciliation — vector vs metadata count per dataset
      3. embedding_dimension  — live embed returns expected 768 dims
      4. dataset_model_drift  — no mixed embedding models per source file
      5. retrieval_sanity     — round-trip embed → search completes without error

    Returns HTTP 200 if overall_status == 'ok' or 'warn'.
    Returns HTTP 503 if overall_status == 'fail' (index or retrieval broken).

    Response body:
      {
        "overall_status": "ok" | "warn" | "fail",
        "timestamp":      str (ISO 8601),
        "checks": [
          {
            "name":    str,
            "status":  "ok" | "warn" | "fail",
            "message": str,
            "details": dict
          },
          ...
        ]
      }
    """
    try:
        checker = MemoryHealthChecker()
        report = checker.run_all()
        report_dict = report.to_dict()

        http_code = 503 if report.overall_status == "fail" else 200
        return jsonify(report_dict), http_code

    except Exception as exc:
        logger.error("[memory_health] Health check runner errored: %s", exc, exc_info=True)
        return jsonify({
            "overall_status": "fail",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": [],
            "error": str(exc)[:300],
        }), 503


# ---------------------------------------------------------------------------
# POST /api/v1/bricks/from_memory
# ---------------------------------------------------------------------------

@bricks_memory_bp.route("/from_memory", methods=["POST"])
def promote_chunk_to_brick():
    """
    Promote a memory chunk to a Nexus Brick via GraphManager.

    Body:
      {
        "chunk_id": "sha256...",    # Required
        "actor":    "user"          # Optional, defaults to "memory_layer"
      }

    Returns:
      {
        "status":    "success" | "failed" | "not_found",
        "brick_id":  str | null,
        "chunk_id":  str,
        "statement": str (first 200 chars)
      }
    """
    body = request.get_json(silent=True) or {}
    chunk_id = body.get("chunk_id", "").strip()
    actor = body.get("actor", "memory_layer")

    if not chunk_id:
        return _error("chunk_id is required.")

    try:
        result = _get_service().promote_to_brick(chunk_id=chunk_id, actor=actor)

        if result["status"] == "not_found":
            return jsonify(result), 404
        if result["status"] == "failed":
            return jsonify(result), 500

        return jsonify(result), 201

    except Exception as exc:
        logger.error("[promote_chunk_to_brick] Error: %s", exc, exc_info=True)
        return _error(f"Promotion failed: {exc}", code=500)


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

def register_memory_routes(app: Flask) -> None:
    """
    Register all memory layer blueprints on the Flask application.

    Call this from server.py after `app = Flask(__name__)`.

    Example:
        from nexus.memory.api_routes import register_memory_routes
        register_memory_routes(app)
    """
    app.register_blueprint(memory_bp)
    app.register_blueprint(bricks_memory_bp)
    logger.info(
        "[MemoryLayer] Routes registered: /api/v1/memory/* and /api/v1/bricks/from_memory"
    )
