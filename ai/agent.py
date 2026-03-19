from services.cortex.mode_router import ModeRouter


class Agent:
    def __init__(self):
        self.router = ModeRouter()

    def decide(self, input_data, mode=None):
        if not mode:
            mode = self.router.route(input_data)

        return {
            "mode": mode,
            "priority": "high" if mode == "trading" else "medium",
        }
