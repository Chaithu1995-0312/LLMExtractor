from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END
import time

class AgentState(TypedDict):
    content: str
    is_valid: bool
    feedback: str
    extracted_facts: List[str]
    retry_count: int

def verifier_node(state: AgentState):
    """
    Verifies the extracted facts for consistency.
    In 2026, we use this node for agentic self-correction.
    """
    content = state["content"]
    facts = state["extracted_facts"]
    
    # Simulate an error detection (e.g., malformed LaTeX or empty extraction)
    if not facts:
        return {
            "is_valid": False, 
            "feedback": "No facts extracted. Extraction might have failed or input was ambiguous.",
            "retry_count": state.get("retry_count", 0) + 1
        }
    
    # Heuristic for "soft" failures
    for fact in facts:
        if "ERROR" in fact.upper() or "$$" in fact and fact.count("$") % 2 != 0:
            return {
                "is_valid": False,
                "feedback": f"Detected malformed syntax in fact: {fact}",
                "retry_count": state.get("retry_count", 0) + 1
            }
    
    return {"is_valid": True, "feedback": "Verification successful."}

def self_correction_node(state: AgentState):
    """
    Simulates an LLM self-correction step.
    In reality, this would call CognitiveExtractor again with feedback.
    """
    print(f"DEBUG: Self-correction triggered. Feedback: {state['feedback']}")
    # Simulate fix
    if "syntax" in state["feedback"]:
        fixed_facts = [f.replace("$$", "$") for f in state["extracted_facts"]]
        return {"extracted_facts": fixed_facts, "is_valid": True}
    return state

def retry_condition(state: AgentState):
    """Determines whether to retry or fail."""
    if state["is_valid"]:
        return "end"
    if state.get("retry_count", 0) > 3:
        return "end"
    return "retry"

def cleanup_crew_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("verify", verifier_node)
    workflow.add_node("correct", self_correction_node)
    
    workflow.set_entry_point("verify")
    
    workflow.add_conditional_edges(
        "verify",
        retry_condition,
        {
            "end": END,
            "retry": "correct"
        }
    )
    
    workflow.add_edge("correct", "verify")
    
    return workflow.compile()

# Simple exponential backoff retry utility (replaces tenacity for direct implementation)
def with_retries(func, max_retries=3):
    def wrapper(*args, **kwargs):
        last_exception = None
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                wait = (2 ** i)
                print(f"WARN: API Call failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
        raise last_exception
    return wrapper

# Usage in Cortex API
cleanup_crew = cleanup_crew_workflow()
