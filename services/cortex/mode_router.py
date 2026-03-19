class ModeRouter:
    def route(self, input_data):
        if input_data.get("type") == "market":
            return "trading"
        elif input_data.get("type") == "chat":
            return "decision"
        return "default"
