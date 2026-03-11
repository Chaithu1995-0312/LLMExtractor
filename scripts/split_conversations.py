import json
from pathlib import Path
import os
import sys
import uuid
import hashlib
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Audit hooks (non-breaking — all wrapped in try/except)
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass

try:
    from validation.base import NexusValidator
    _AUDIT_ENABLED = True
except ImportError:
    _AUDIT_ENABLED = False
    print("[split] WARN: validation.base not found — audit hooks disabled.")


def _compute_file_checksum(path: Path) -> str:
    """Compute SHA-256 checksum of a file. Returns hex string."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "checksum_unavailable"


def generate_batch_manifest(batch: list, batch_idx: int, source_checksum: str, output_path: Path) -> dict:
    """
    Generate and save a manifest JSON for a batch.
    Stored alongside the batch file as manifest_batch_<idx>.json.

    This is a new capability — non-breaking, errors are swallowed.
    """
    manifest = {
        "batch_id": batch_idx,
        "message_count": len(batch),
        "source_checksum_sha256": source_checksum,
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        "system_metadata": {
            "python_version": sys.version.split()[0],
            "splitter_version": "1.1.0",
            "platform": sys.platform,
        },
    }
    try:
        manifest_path = output_path / f"manifest_batch_{batch_idx}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[split] WARN: Could not write manifest for batch {batch_idx}: {e}")
    return manifest


def split_chatgpt_export_messages(
    input_file: str,
    output_dir: str,
    target_batch_size_mb: float = 3.0
):
    """
    Splits official ChatGPT export conversations.json into message-level batches.
    Flattens conversation structure to individual messages for precise L1 extraction.

    Audit hooks (Phase 1 — non-breaking):
      - Emits SPLIT_START / SPLIT_COMPLETE events to audit.processing_trail
      - Generates manifest_batch_<N>.json alongside each messages_batch_<N>.json
      - Invalid messages are counted and logged (INVALID_MESSAGE) but NOT skipped
        — existing skip logic (empty content / system role) is preserved unchanged
    """

    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # ── Audit: compute source checksum before loading ────────────────────
    source_checksum = "unavailable"
    if input_path.exists():
        source_checksum = _compute_file_checksum(input_path)

    # ── Audit: open validator ────────────────────────────────────────────
    validator = None
    if _AUDIT_ENABLED:
        try:
            validator = NexusValidator(stage="PRE", batch_id=f"split-{input_path.stem}")
            validator._open_db()
            t_split_start = time.time()
            validator.log("SPLIT_START", {
                "input_file": str(input_path),
                "output_dir": output_dir,
                "target_batch_mb": target_batch_size_mb,
                "source_checksum_sha256": source_checksum,
            })
        except Exception as audit_err:
            print(f"[split] WARN: Audit hook failed at start (non-fatal): {audit_err}")
            validator = None

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.")
        if validator:
            try:
                validator.log("SPLIT_FAILURE", {"error": f"File not found: {input_path}"}, status="error")
                validator._close_db()
            except Exception:
                pass
        return

    print(f"Loading '{input_path}'...")
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        if validator:
            try:
                validator.log("SPLIT_FAILURE", {"error": str(e)}, status="error")
                validator._close_db()
            except Exception:
                pass
        return

    if not isinstance(conversations, list):
        raise ValueError("Expected ChatGPT export root to be a list.")

    total_convs = len(conversations)
    print(f"Total conversations found: {total_convs}")
    print("Flattening to message level...")

    batch_idx = 1
    current_batch = []
    current_batch_size = 0
    target_bytes = target_batch_size_mb * 1024 * 1024
    total_messages_processed = 0
    invalid_message_count = 0

    for conv in conversations:
        conversation_id = conv.get("conversation_id") or conv.get("id") or str(uuid.uuid4())
        title = conv.get("title", "Untitled Conversation")
        mapping = conv.get("mapping", {})

        # Walk the mapping to extract messages
        for node_id, node_data in mapping.items():
            message = node_data.get("message")
            if not message:
                continue
            
            # Skip system messages or empty content
            author_role = message.get("author", {}).get("role")
            content_parts = message.get("content", {}).get("parts", [])
            text_content = "".join([str(p) for p in content_parts if isinstance(p, str)])
            
            if not text_content.strip() or author_role == "system":
                continue

            # Create flattened message object
            flat_msg = {
                "id": message.get("id", str(uuid.uuid4())),
                "conversation_id": conversation_id,
                "conversation_title": title,
                "role": author_role,
                "create_time": message.get("create_time"),
                "content": text_content,
                "model_slug": message.get("metadata", {}).get("model_slug")
            }

            # ── Audit: per-message field check (non-blocking) ─────────────
            if validator:
                try:
                    missing = [f for f in ("id", "conversation_id", "role", "content")
                               if not flat_msg.get(f)]
                    if missing:
                        invalid_message_count += 1
                        validator.log(
                            "INVALID_MESSAGE",
                            {"message_id": flat_msg.get("id"), "missing_fields": missing},
                            status="warn",
                        )
                except Exception:
                    pass  # audit hook failure must never break the split

            # Size estimation
            msg_str = json.dumps(flat_msg, ensure_ascii=False)
            msg_bytes = len(msg_str.encode("utf-8"))

            if current_batch and (current_batch_size + msg_bytes > target_bytes):
                save_batch(current_batch, output_path, batch_idx)
                # ── Audit: batch manifest ──────────────────────────────
                try:
                    generate_batch_manifest(current_batch, batch_idx, source_checksum, output_path)
                except Exception:
                    pass
                batch_idx += 1
                current_batch = []
                current_batch_size = 0

            current_batch.append(flat_msg)
            current_batch_size += msg_bytes
            total_messages_processed += 1

    # Save the final batch
    if current_batch:
        save_batch(current_batch, output_path, batch_idx)
        try:
            generate_batch_manifest(current_batch, batch_idx, source_checksum, output_path)
        except Exception:
            pass

    print(f"✅ Splitting complete.")
    print(f"Processed {total_convs} conversations into {total_messages_processed} individual messages.")
    print(f"Created {batch_idx} batches in '{output_dir}'.")

    # ── Audit: SPLIT_COMPLETE ────────────────────────────────────────────
    if validator:
        try:
            validator.log_timed(
                "SPLIT_COMPLETE",
                t_split_start,
                {
                    "conversation_count": total_convs,
                    "message_count": total_messages_processed,
                    "batch_count": batch_idx,
                    "invalid_messages": invalid_message_count,
                    "output_dir": output_dir,
                },
            )
            validator._close_db()
        except Exception as audit_err:
            print(f"[split] WARN: Audit hook failed at completion (non-fatal): {audit_err}")


def save_batch(batch, output_path, idx):
    output_file = output_path / f"messages_batch_{idx}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False)
    
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"Written Batch {idx}: {len(batch)} messages ({file_size_mb:.2f} MB)")


if __name__ == "__main__":
    # Configure for Message-Level Splitting
    split_chatgpt_export_messages(
        input_file="conversations.json",
        output_dir="openaiconversations",
        target_batch_size_mb=3.0
    )
