import sys
sys.path.insert(0, "src")
from nexus.evolution.concept_evolution import ConceptEvolutionAPI, ConceptRoot, NodeDetail, ConceptChain, EvolutionNode
from nexus.evolution.promotion_engine import PromotionEngine, ResolutionStrategy, ConflictSeverity, PromotionResult, ConflictReport
from nexus.evolution.ai_advisory import AIAdvisory, SuggestionType
print("✅ All Evolution V2 modules imported successfully")
print("  ConceptEvolutionAPI:", ConceptEvolutionAPI)
print("  PromotionEngine:", PromotionEngine)
print("  ResolutionStrategy values:", [s.value for s in ResolutionStrategy])
print("  ConflictSeverity values:", [s.value for s in ConflictSeverity])
print("  AIAdvisory:", AIAdvisory)
print("  SuggestionType.MERGE:", SuggestionType.MERGE)
