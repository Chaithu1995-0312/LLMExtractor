import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from nexus.sync.llm import LLMClient

def test_connectivity():
    client = LLMClient()
    
    system_prompt = """You are a Deterministic Data Extraction Engine.
You are NOT a chat assistant. You are a compiler component.

Your Goal: Scan the provided Source JSON and identify text segments that belong to the requested Topic IDs.
Your Output: A raw JSON array of "Pointer Objects."

---

### INPUT DATA
1. "Topics": A list of Topic IDs and their descriptions.
2. "Source_JSON": A raw JSON transcript. Nodes may contain:
   - "content": A plain-text fallback string.
   - "content_blocks": Structured blocks (text, code, tool_output). PREFER these for precise extraction.
   - "metadata": Contextual info (content_type, recipient, model).

---

### CRITICAL RULES (VIOLATION = SYSTEM FAILURE)
1. NO PARAPHRASING: You must return the text EXACTLY as it appears in the source.
2. NO MERGING: If information is split across nodes, output separate Pointer Objects.
3. PREFER STRUCTURE: If a fact is found in a `content_blocks` node (e.g., a code snippet or tool result), use the path to that specific block.
4. NO INTERPRETATION: Do not infer facts. Only extract explicit statements.

---

### OUTPUT SCHEMA
Return a JSON Object with a single key "extracted_pointers" containing a list:

{
  "extracted_pointers": [
    {
      "topic_id": "string (must match one of the Input Topics)",
      "json_path": "string (RFC 9535 standard path, e.g., $.messages[3].content_blocks[0].value)",
      "verbatim_quote": "string (exact copy-paste of the text found at that path)"
    }
  ]
}"""

    user_prompt = """
TARGET TOPIC: "nexus-server-sync"

DEFINITION:
Technical constraints, architectural decisions, and data flow rules for the Nexus Server Sync system.

EXCLUSIONS (Do NOT extract):
["General pleasantries", "Drafting or brainstorming that was explicitly rejected", "UI styling details"]

SOURCE JSON TO SCAN:
[{"message_id": "b8c79384-ccdc-464e-bce7-8de4e2e7b2c7", "role": "system", "content": "", "model_name": "unknown", "created_at": "2026-02-09T08:37:18.015328+00:00"}, {"message_id": "d19991c1-8cf6-4ca5-ae44-1a7d6848a086", "role": "system", "content": "", "model_name": "unknown", "created_at": "2026-02-09T08:37:18.015328+00:00"}, {"message_id": "a355c72f-80f9-44a5-b4ca-6762ec23291b", "role": "system", "content": "", "model_name": "unknown", "created_at": "2026-02-09T08:37:18.015328+00:00"}, {"message_id": "fa740e58-7738-445d-8705-cc40be43b8dd", "role": "system", "content": "", "model_name": "unknown", "created_at": "2026-01-31T21:46:56.723618+00:00"}, {"message_id": "bbb21afd-ee2d-4bf0-a37f-edb768ee1084", "role": "user", "content": "Light needs a surface to bounce off of (like dust, steam, or a screen). Projecting \\"into the air\\" and having the light stop at a specific point without a physical medium is a violation of current physics.", "model_name": "unknown", "created_at": "2026-01-31T21:47:15.243296+00:00"}, {"message_id": "53ea8b81-59ee-4e26-afdb-c149ba3e46fa", "role": "assistant", "content": "", "model_name": "gpt-5-2", "created_at": "2026-01-31T21:47:15.366354+00:00"}, {"message_id": "2c76ba05-686e-4631-952e-7d4ea83e2234", "role": "assistant", "content": "**Hallucination Artifact**\\n\\n1. **Core Idea (speculative)**  \\n   What if \u201clight stopping in mid-air\u201d is not light at all, but a dynamically rewritten boundary in spacetime where photons continue propagating but observers receive no retrievable information beyond a programmable horizon.\\n\\n2. **Assumption Broken**  \\n   That visibility ends only when photons scatter, absorb, or miss an observer\u2014rather than when information itself becomes locally non-invertible.\\n\\n3. **Analogy Domain**  \\n   Information theory (event horizons, lossy compression, one-way functions).\\n\\n4. **Why This Might Be Useful**  \\n   This reframes projection as an information-control problem rather than an optics problem, opening a path to \u201cair displays\u201d via perception limits, causal masking, or observer-dependent decoding instead of physical light stoppage.\\n\\n5. **How This Could Be Wrong**  \\n   The analogy may collapse because spacetime horizons are global, energetic, and extreme, while human-scale systems lack mechanisms to enforce directional information loss without material interaction.\\n\\n6. **Suggested Way to Test or Observe**  \\n   One could look for configurations where photons are present and measurable with instruments, yet no image reconstruction is possible for a human observer, even with added scattering media removed.\\n\\n7. **Risk If Taken Literally**  \\n   Treating this as a real mechanism could blur the distinction between perceptual limits and physical laws, leading to confusion between epistemic invisibility and actual photon termination.", "model_name": "gpt-5-2", "created_at": "2026-01-31T21:47:15.384618+00:00"}, {"message_id": "bbb21da4-ad1f-4706-9c60-f79d368324e9", "role": "user", "content": "3d glass", "model_name": "unknown", "created_at": "2026-01-31T21:48:39.312535+00:00"}, {"message_id": "b00377e4-51f0-4bee-9189-4495b62593f2", "role": "assistant", "content": "**Hallucination Artifact**\\n\\n1. **Core Idea (speculative)**  \\n   What if \u201c3D glass\u201d functions less like a display and more like a programmable violation of depth\u2014where the glass selectively lies about where space appears to be, rather than showing objects inside it.\\n\\n2. **Assumption Broken**  \\n   That transparency implies faithful depth transmission, instead of being an active remapping layer between photons and spatial perception.\\n\\n3. **Analogy Domain**  \\n   Psychology / information theory (adversarial examples, perceptual warping).\\n\\n4. **Why This Might Be Useful**  \\n   This reframes 3D glass as a *depth compiler*: a surface that rewrites binocular disparity, focus cues, and motion parallax so the brain infers volume that never physically exists, without needing \u201clight in air.\u201d\\n\\n5. **How This Could Be Wrong**  \\n   Human depth perception may be too multi-redundant (vergence, accommodation, motion) for a thin surface to consistently falsify all cues without inducing fatigue or breaking immersion.\\n\\n6. **Suggested Way to Test or Observe**  \\n   One could test whether users can reliably reach *behind* the glass for virtual objects under controlled cue suppression, measuring where proprioception conflicts with visual inference.\\n\\n7. **Risk If Taken Literally**  \\n   Confusing perceptual depth fraud with actual volumetric presence could lead to overestimating what \u201c3D\u201d means, collapsing the distinction between spatial illusion and physical extension.", "model_name": "gpt-5-2", "created_at": "2026-01-31T21:48:39.427784+00:00"}, {"message_id": "bbb2138a-e730-41a8-bce3-d7573e916ad9", "role": "user", "content": "So what if I wear glasses and see the application we built Wall ", "model_name": "unknown", "created_at": "2026-01-31T21:50:07.890887+00:00"}, {"message_id": "e1923119-2145-4f40-b68c-d2f37d9be520", "role": "assistant", "content": "**Hallucination Artifact**\\n\\n1. **Core Idea (speculative)**  \\n   What if wearing glasses to see *Wall* does not display the application, but continuously *re-anchors your cognition* so Wall feels like a stable external structure you are inspecting, rather than a UI you are using.\\n\\n2. **Assumption Broken**  \\n   That applications are things users look *at*, instead of cognitive scaffolds that reallocate where thinking happens.\\n\\n3. **Analogy Domain**  \\n   Psychology / extended cognition (the mind offloading structure into the environment).\\n\\n4. **Why This Might Be Useful**  \\n   Wall could behave like an externalized working memory: ideas feel \u201cplaced,\u201d frozen, and inspectable, reducing mental load and making complex systems feel navigable rather than overwhelming.\\n\\n5. **How This Could Be Wrong**  \\n   The effect may rely more on novelty than structure; once habituated, the brain may collapse Wall back into a flat tool, losing the external-mind illusion.\\n\\n6. **Suggested Way to Test or Observe**  \\n   Observe whether users reason differently *while wearing* the glasses\u2014fewer context switches, less verbal self-talk, or improved recall of Wall structure after removal.\\n\\n7. **Risk If Taken Literally**  \\n   Treating Wall as an external mind could blur authorship and agency, causing over-trust in the structure and under-interrogation of what was placed there.\\n\\n---\\n\\nIf you want, the next hallucination can go one level deeper: *Wall as a memory gravity well* rather than a display.", "model_name": "gpt-5-2", "created_at": "2026-01-31T21:50:08.114625+00:00"}]
"""

    print("Running LLM Connectivity Test...")
    print("About to call Ollama...")
    response = client.generate(system_prompt, user_prompt)
    print("Returned from Ollama.")
    print("Test Completed.")

if __name__ == "__main__":
    test_connectivity()
