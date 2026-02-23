"""
G-01 FIX: Internal mutation auth middleware.

Enforces that all state-mutating endpoints carry a verifiable internal
token. This is NOT a full user-authentication system — it is a Freeze-0
provenance anchor that prevents:

  1. Unauthenticated actors writing fabricated provenance to the audit log.
  2. `actor` field being caller-controlled string-injection.
  3. Audit log entries that cannot be attributed to a verified principal.

Protocol:
  - All mutation requests MUST include the header:
      X-Nexus-Actor:  <actor_id>
      X-Nexus-Token:  <HMAC-SHA256(actor_id + ":" + request_path, NEXUS_INTERNAL_SECRET)>

  - NEXUS_INTERNAL_SECRET is read from the environment (never hardcoded).
  - If the env var is unset in development, a warning is printed and a
    dev-only bypass is activated (NEXUS_AUTH_BYPASS=true must be explicitly
    set). In production (NEXUS_ENV=production), missing secret = hard failure.

Usage in server.py:
    from services.cortex.auth import require_internal_auth, extract_verified_actor

    @app.route("/jarvis/node/promote", methods=["POST"])
    @require_internal_auth
    def jarvis_node_promote():
        actor = extract_verified_actor(request)
        ...
"""

import os
import hmac
import hashlib
import functools
from flask import request, jsonify

_SECRET = os.getenv("NEXUS_INTERNAL_SECRET", "").encode("utf-8")
_ENV = os.getenv("NEXUS_ENV", "development")
_BYPASS = os.getenv("NEXUS_AUTH_BYPASS", "false").lower() == "true"


def _compute_token(actor_id: str, path: str) -> str:
    """
    HMAC-SHA256(secret, actor_id + ":" + path)
    Binds the token to both the actor identity and the specific endpoint,
    so a valid token for /jarvis/node/kill cannot be replayed on /jarvis/node/promote.
    """
    message = f"{actor_id}:{path}".encode("utf-8")
    return hmac.new(_SECRET, message, hashlib.sha256).hexdigest()


def _verify_request() -> tuple:
    """
    Returns (is_valid: bool, actor_id: str | None, reason: str).
    """
    if not _SECRET:
        if _ENV == "production":
            return False, None, "NEXUS_INTERNAL_SECRET not set in production — all mutations blocked."
        if _BYPASS:
            # Development bypass: extract actor from header without verification.
            # NEXUS_AUTH_BYPASS=true must be explicitly set — it is NOT the default.
            actor = request.headers.get("X-Nexus-Actor") or (
                request.get_json(silent=True) or {}
            ).get("actor", "dev-bypass")
            print(
                f"[AUTH] WARN: NEXUS_INTERNAL_SECRET not set. "
                f"Dev bypass active. Actor={actor!r}. "
                f"Set NEXUS_INTERNAL_SECRET before production deployment."
            )
            return True, actor, "dev-bypass"
        return (
            False,
            None,
            "NEXUS_INTERNAL_SECRET not set and NEXUS_AUTH_BYPASS is not enabled.",
        )

    actor_id = request.headers.get("X-Nexus-Actor", "").strip()
    provided_token = request.headers.get("X-Nexus-Token", "").strip()

    if not actor_id:
        return False, None, "Missing X-Nexus-Actor header."
    if not provided_token:
        return False, None, "Missing X-Nexus-Token header."

    expected_token = _compute_token(actor_id, request.path)

    # Constant-time comparison to prevent timing attacks.
    if not hmac.compare_digest(provided_token, expected_token):
        return False, None, f"Invalid token for actor={actor_id!r} on path={request.path!r}."

    return True, actor_id, "ok"


def require_internal_auth(fn):
    """
    Decorator: gates the endpoint behind HMAC token verification.
    Injects verified actor into request context (g.verified_actor).

    On failure: returns 401 with a structured error body.
    The error body intentionally does NOT reveal whether the actor or the
    token was wrong — only that authentication failed.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        from flask import g
        is_valid, actor_id, reason = _verify_request()
        if not is_valid:
            print(f"[AUTH] BLOCKED {request.method} {request.path} — {reason}")
            return jsonify({
                "error": "Unauthorized",
                "detail": "Request did not pass internal mutation authentication.",
                "status": 401
            }), 401
        # Store verified actor on Flask's request context.
        # Handlers MUST use extract_verified_actor(request) — NOT request.json["actor"].
        g.verified_actor = actor_id
        return fn(*args, **kwargs)
    return wrapper


def extract_verified_actor(req) -> str:
    """
    Returns the verified actor from Flask's request context.
    Always use this instead of reading `actor` from the request body.

    G-01: The actor written to audit logs MUST come from a verified token,
    never from caller-controlled JSON. This function enforces that contract.
    """
    from flask import g
    actor = getattr(g, "verified_actor", None)
    if not actor:
        # This should never happen if @require_internal_auth was applied,
        # but acts as a hard fallback to prevent silent provenance loss.
        raise RuntimeError(
            "extract_verified_actor() called outside of an authenticated request context. "
            "Ensure @require_internal_auth is applied to this endpoint."
        )
    return actor
