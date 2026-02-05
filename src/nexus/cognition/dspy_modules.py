import dspy
from typing import List, Optional

class FactSignature(dspy.Signature):
    """Extract atomic propositional facts from the context."""
    context = dspy.InputField(desc="Aggregated text from multiple bricks")
    facts = dspy.OutputField(desc="List of atomic statements representing core knowledge")

class DiagramSignature(dspy.Signature):
    """Extract structural relationships and technical diagrams."""
    context = dspy.InputField(desc="Aggregated text")
    latex_formulas = dspy.OutputField(desc="List of LaTeX formatted formulas found or derived")
    mermaid_diagrams = dspy.OutputField(desc="List of Mermaid.js formatted diagrams representing flows or structures")

class CognitiveExtractor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.fact_extractor = dspy.ChainOfThought(FactSignature)
        self.diagram_extractor = dspy.ChainOfThought(DiagramSignature)

    def forward(self, context: str):
        facts_res = self.fact_extractor(context=context)
        diagrams_res = self.diagram_extractor(context=context)
        
        return dspy.Prediction(
            facts=facts_res.facts,
            latex=diagrams_res.latex_formulas,
            mermaid=diagrams_res.mermaid_diagrams
        )
