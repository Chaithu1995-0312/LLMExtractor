class LLMGate:
    def __init__(self, threshold=0.75):
        self.threshold = threshold

    def should_call_llm(self, confidence: float) -> bool:
        return confidence < self.threshold
