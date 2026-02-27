import csv
import json
from collections import defaultdict, Counter
import sys

# --- CONFIGURATION ---

# 1. Topic Definitions & Keywords
TOPIC_KEYWORDS = {
    "trading-intelligence-core": {
        "trading": 3, "trade": 2, "market": 2, "regime": 3, "risk": 3,
        "symbol": 2, "entry": 2, "exit": 2, "trap": 3, "liquidity": 2,
        "chaos": 3, "rr": 2, "prop": 2, "position": 2, "strategy": 2,
        "pnl": 2, "equity": 2, "drawdown": 2, "volatility": 2
    },
    "genai-architecture-core": {
        "jarvis": 3, "ultron": 2, "prompt": 2, "claude": 2, "gemini": 2,
        "flash": 2, "confidence": 2, "escalation": 2, "cognition": 3,
        "agent": 2, "model": 1, "llm": 2, "ai": 1, "context": 1,
        "embedding": 2, "vector": 2, "token": 1
    },
    "infra-execution-layer": {
        "lambda": 3, "dynamodb": 3, "ecs": 3, "queue": 2, "pgworker": 3,
        "transaction": 2, "ttl": 2, "contract": 2, "eventbridge": 3,
        "schema": 2, "postgres": 2, "sql": 1, "api": 1, "websocket": 2,
        "docker": 2, "aws": 2, "infrastructure": 2, "deployment": 2
    },
    "governance-lifecycle-wall": {
        "frozen": 3, "supersede": 3, "lifecycle": 3, "audit": 3,
        "invariant": 3, "brick": 2, "wall": 2, "extraction": 2,
        "memory": 2, "loose": 2, "forming": 2, "killed": 2,
        "state": 1, "trace": 2, "policy": 2
    }
}

# 2. Scoring Thresholds
AMBIGUITY_THRESHOLD = 0.15  # If top 2 scores are within 15% of each other
MIN_CONFIDENCE_SCORE = 3    # Minimum keyword score to be considered "confident" without LLM

# --- LOGIC ---

def score_text(text):
    text = text.lower()
    scores = {topic: 0 for topic in TOPIC_KEYWORDS}
    
    # Simple keyword counting
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw, weight in keywords.items():
            if kw in text:
                # Basic occurrence check - could be improved with regex word boundaries
                # but valid for a quick simulation
                scores[topic] += weight
                
    return scores

def classify_brick(scores):
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_topic, primary_score = sorted_scores[0]
    secondary_topic, secondary_score = sorted_scores[1]
    
    total_score = sum(scores.values())
    
    # Avoid division by zero
    if total_score == 0:
        return {
            "primary_topic": "governance-lifecycle-wall", # Default fallback
            "confidence": 0.0,
            "is_ambiguous": True,
            "reason": "no_keywords"
        }

    # Calculate confidence margin
    if primary_score == 0:
         return {
            "primary_topic": "governance-lifecycle-wall",
            "confidence": 0.0,
            "is_ambiguous": True,
            "reason": "zero_score"
        }
        
    margin = (primary_score - secondary_score) / primary_score if primary_score > 0 else 0
    
    is_ambiguous = False
    reason = "clear"
    
    if margin < AMBIGUITY_THRESHOLD:
        is_ambiguous = True
        reason = "low_margin"
    elif primary_score < MIN_CONFIDENCE_SCORE:
        is_ambiguous = True
        reason = "low_score"
        
    return {
        "primary_topic": primary_topic,
        "secondary_topic": secondary_topic,
        "primary_score": primary_score,
        "secondary_score": secondary_score,
        "margin": margin,
        "is_ambiguous": is_ambiguous,
        "reason": reason
    }

def main():
    csv_path = "databaseinfo/data-1772004961200.csv"
    
    stats = {
        "total_bricks": 0,
        "topic_counts": Counter(),
        "ambiguous_count": 0,
        "reasons": Counter(),
        "zero_match_count": 0
    }
    
    print(f"Reading bricks from {csv_path}...")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                stats["total_bricks"] += 1
                content = row.get("content", "")
                
                if not content:
                    continue
                    
                scores = score_text(content)
                result = classify_brick(scores)
                
                stats["topic_counts"][result["primary_topic"]] += 1
                
                if result["is_ambiguous"]:
                    stats["ambiguous_count"] += 1
                    stats["reasons"][result["reason"]] += 1
                
                if result.get("reason") in ["no_keywords", "zero_score"]:
                     stats["zero_match_count"] += 1

    except FileNotFoundError:
        print(f"Error: File {csv_path} not found.")
        return

    # --- REPORT ---
    
    print("\n" + "="*40)
    print("TOPIC ROUTER SIMULATION REPORT")
    print("="*40)
    
    print(f"\nTotal Bricks Processed: {stats['total_bricks']}")
    
    print("\n--- Proposed Topic Distribution ---")
    for topic, count in stats["topic_counts"].most_common():
        percentage = (count / stats["total_bricks"]) * 100
        print(f"{topic:<30}: {count:>4} ({percentage:.1f}%)")
        
    print("\n--- Ambiguity & LLM Needs ---")
    ambiguous_pct = (stats["ambiguous_count"] / stats["total_bricks"]) * 100
    print(f"Ambiguous Bricks (Need LLM): {stats['ambiguous_count']} ({ambiguous_pct:.1f}%)")
    
    print("\nReasons for Ambiguity:")
    for reason, count in stats["reasons"].most_common():
        print(f"  - {reason:<15}: {count}")
        
    print(f"\nZero Keyword Matches (Fallback): {stats['zero_match_count']}")
    
    print("\n" + "="*40)
    print("CONCLUSION")
    
    dominant_topic = stats["topic_counts"].most_common(1)[0][0]
    print(f"Dominant Domain: {dominant_topic}")
    
    if ambiguous_pct > 20:
        print("WARNING: High ambiguity rate. Keyword lists may need tuning or LLM budget will be high.")
    else:
        print("SUCCESS: Keyword pre-filtering is effective. LLM usage will be efficient.")

if __name__ == "__main__":
    main()
