from typing import List, Dict, Optional
import json

class UserTriggeredResolver:
    OVERLAP_N = 10  # fixed constant

    def __init__(self, graph_manager):
        self.graph = graph_manager

    def is_triggered(self, user_text: str) -> bool:
        """Detect if the resolution logic should be triggered."""
        lowered = user_text.lower()
        return (
            "continue" in lowered
            or "\n" in user_text.strip()
            or (user_text.strip().startswith("1.") or user_text.strip().startswith("- "))
        )

    def split_user_blocks(self, text: str) -> List[str]:
        """Split user text into potential answer blocks."""
        blocks = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Remove leading numbering if present
            if line[0].isdigit() and "." in line:
                line = line.split(".", 1)[1].strip()
            elif line.startswith("- "):
                line = line[2:].strip()
            
            if line:
                blocks.append(line)
        return blocks

    def is_covered(self, question: str, answer_block: str) -> bool:
        """Deterministic structural coverage check using substring overlap."""
        if len(question) < self.OVERLAP_N:
            return question.lower() in answer_block.lower()
            
        for i in range(len(question) - self.OVERLAP_N + 1):
            chunk = question[i:i + self.OVERLAP_N]
            if chunk.lower() in answer_block.lower():
                return True
        return False

    def resolve(self, topic_id: str, user_message: Dict) -> Optional[Dict]:
        """Run the resolution algorithm on LOOSE bricks."""
        # Enforce flattened text access
        user_text = ""
        if isinstance(user_message.get("content"), dict):
            user_text = user_message["content"].get("text", "")
        else:
            user_text = user_message.get("content", "")

        if not self.is_triggered(user_text):
            return None

        loose = self.graph.get_loose_bricks(topic_id)
        # Order by creation time (oldest first)
        loose = sorted(loose, key=lambda b: b.get("created_at", ""))

        blocks = self.split_user_blocks(user_text)
        positional_allowed = "continue" in user_text.lower()

        resolved = []
        still_loose = []

        for idx, brick in enumerate(loose):
            covered = False
            brick_text = brick.get("statement", brick.get("content", ""))

            # Rule A — direct structural overlap
            for block in blocks:
                if self.is_covered(brick_text, block):
                    covered = True
                    break

            # Rule B — positional mapping (continue / ordered answers)
            if not covered and positional_allowed and idx < len(blocks):
                covered = True

            if covered:
                self.graph.mark_forming(
                    brick_id=brick["id"],
                    resolved_by=user_message.get("message_id"),
                    actor="user"
                )
                resolved.append(brick_text)
            else:
                still_loose.append(brick_text)

        return {
            "resolved": resolved,
            "still_loose": still_loose
        }
