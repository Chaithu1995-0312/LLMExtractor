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

class RelationshipSignature(dspy.Signature):
    """Analyze a list of intents and find structural relationships between them."""
    intents = dspy.InputField(desc="List of atomic facts or technical intents with IDs")
    existing_topology = dspy.InputField(desc="List of existing edges to avoid duplication or contradiction")
    relationships = dspy.OutputField(desc="List of dicts: [{'source_id': str, 'target_id': str, 'type': 'DEPENDS_ON' | 'CONFLICTS_WITH' | 'OVERRIDES', 'reason': str}]")

class EntitySignature(dspy.Signature):
    """Identify key entities and technical components mentioned in the text."""
    context = dspy.InputField(desc="Text to analyze")
    entities = dspy.OutputField(desc="List of unique entities, systems, or technical terms found")

class CognitiveExtractor(dspy.Module):
    def __init__(self, max_depth: int = 2):
        super().__init__()
        self.fact_extractor = dspy.ChainOfThought(FactSignature)
        self.diagram_extractor = dspy.ChainOfThought(DiagramSignature)
        self.entity_extractor = dspy.ChainOfThought(EntitySignature)
        self.max_depth = max_depth

    def forward(self, context: str, current_depth: int = 0):
        # 1. Primary Extraction
        facts_res = self.fact_extractor(context=context)
        diagrams_res = self.diagram_extractor(context=context)
        entities_res = self.entity_extractor(context=context)
        
        prediction = dspy.Prediction(
            facts=facts_res.facts,
            latex=diagrams_res.latex_formulas,
            mermaid=diagrams_res.mermaid_diagrams,
            entities=entities_res.entities
        )

        # 2. Recursive Logic: Trigger secondary extraction if entities found
        if current_depth < self.max_depth and entities_res.entities:
            # Note: Recursive triggers would typically be handled by a queue/orchestrator
            # but we define the logical bridge here.
            prediction.recursive_entities = entities_res.entities

        return prediction

class SentimentSignature(dspy.Signature):
    """Analyze the user query for urgency and sentiment."""
    query = dspy.InputField()
    urgency_score = dspy.OutputField(desc="Score from 0.0 to 1.0 (1.0 being critical/emergency)")
    sentiment = dspy.OutputField(desc="Positive, Negative, or Neutral")

class RelationshipSynthesizer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.synthesizer = dspy.ChainOfThought(RelationshipSignature)
        self.sentiment_analyzer = dspy.ChainOfThought(SentimentSignature)

    def analyze_sentiment(self, query: str):
        return self.sentiment_analyzer(query=query)

    def forward(self, intents: List[dict], existing_edges: List[dict] = []):
        # Format intents for the prompt
        intent_str = "\n".join([f"ID: {i['id']} | CONTENT: {i['statement']}" for i in intents])
        edge_str = "\n".join([f"{e['source']} -> {e['type']} -> {e['target']}" for e in existing_edges])
        
        res = self.synthesizer(intents=intent_str, existing_topology=edge_str or "None")
        return dspy.Prediction(relationships=res.relationships)
