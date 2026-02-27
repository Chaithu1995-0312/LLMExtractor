import json
from pathlib import Path
from math import ceil


def split_chatgpt_export(
    input_file: str,
    output_dir: str,
    conversations_per_file: int = 50
):
    """
    Splits official ChatGPT export conversations.json
    without altering schema or internal mapping structure.
    """

    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    if not isinstance(conversations, list):
        raise ValueError("Expected ChatGPT export root to be a list.")

    total = len(conversations)
    total_files = ceil(total / conversations_per_file)

    print(f"Total conversations: {total}")
    print(f"Creating {total_files} files in '{output_dir}'...")

    for i in range(total_files):
        start = i * conversations_per_file
        end = start + conversations_per_file
        chunk = conversations[start:end]

        output_file = output_path / f"conversations_part_{i+1}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)

        print(f"Written: {output_file}")

    print("✅ Done.")


if __name__ == "__main__":
    split_chatgpt_export(
        input_file="conversations.json",
        output_dir="openaiconversations",
        conversations_per_file=10
    )
