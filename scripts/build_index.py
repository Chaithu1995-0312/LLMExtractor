import os
import json
import re

OUTPUT_ROOT = "output"          # change if needed
INDEX_FILE = "index.json"

path_pattern = re.compile(r"path_(\d+)\.json")

index = []

for conversation_id in sorted(os.listdir(OUTPUT_ROOT)):
    conv_path = os.path.join(OUTPUT_ROOT, conversation_id)

    if not os.path.isdir(conv_path):
        continue

    paths = []
    for file in os.listdir(conv_path):
        match = path_pattern.match(file)
        if match:
            num = match.group(1)
            paths.append({
                "label": f"Path {num.zfill(3)}",
                "file": f"{conversation_id}/{file}"
            })

    if paths:
        paths.sort(key=lambda x: x["label"])
        index.append({
            "conversation_id": conversation_id,
            "paths": paths
        })

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, indent=2)

print(f"index.json generated with {len(index)} conversations")
