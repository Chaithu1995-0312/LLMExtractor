import json
import os


class Feedback:
    def __init__(self, path="audit/feedback.json"):
        self.path = path

    def record(self, data):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump([], f)

        with open(self.path, "r+", encoding="utf-8") as f:
            content = json.load(f)
            content.append(data)
            f.seek(0)
            json.dump(content, f, indent=2)
            f.truncate()
