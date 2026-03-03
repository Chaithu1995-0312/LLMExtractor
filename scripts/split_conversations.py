import json
from pathlib import Path
import os
import uuid


def split_chatgpt_export_messages(
    input_file: str,
    output_dir: str,
    target_batch_size_mb: float = 3.0
):
    """
    Splits official ChatGPT export conversations.json into message-level batches.
    Flattens conversation structure to individual messages for precise L1 extraction.
    """

    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.")
        return

    print(f"Loading '{input_path}'...")
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
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

            # Size estimation
            msg_str = json.dumps(flat_msg, ensure_ascii=False)
            msg_bytes = len(msg_str.encode("utf-8"))

            if current_batch and (current_batch_size + msg_bytes > target_bytes):
                save_batch(current_batch, output_path, batch_idx)
                batch_idx += 1
                current_batch = []
                current_batch_size = 0

            current_batch.append(flat_msg)
            current_batch_size += msg_bytes
            total_messages_processed += 1

    # Save the final batch
    if current_batch:
        save_batch(current_batch, output_path, batch_idx)

    print(f"✅ Splitting complete.")
    print(f"Processed {total_convs} conversations into {total_messages_processed} individual messages.")
    print(f"Created {batch_idx} batches in '{output_dir}'.")


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
