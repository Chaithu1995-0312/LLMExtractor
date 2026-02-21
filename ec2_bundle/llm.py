import os
import json
from typing import Optional, Literal, Dict, Any, Union, List
import traceback
from dataclasses import dataclass, field
from pydantic import BaseModel
from llama_index.llms.ollama import Ollama
import urllib.request
import urllib.error

# --- TYPES ---

LLMIntentClass = Literal[
    "TEST",
    "INGEST_EXTRACT",
    "INGEST_REWRITE",
    "COVERAGE_ANALYSIS",
    "SYSTEM_ALERT",
    "USER_EXPLAIN",
    "DEEP_SYNTHESIS"
]

CostTolerance = Literal["zero", "low", "high"]

LLMTier = Literal["L0", "L1", "L2", "L3"]
LLMProvider = Literal["mock", "ollama", "api"]

@dataclass
class LLMRequest:
    intent_class: LLMIntentClass
    cost_tolerance: CostTolerance
    user_visible: bool
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMRoute:
    tier: LLMTier
    model: str
    provider: LLMProvider

class LLMRoutingError(Exception):
    pass

# --- ROUTER ---

class LLMRouter:
    def __init__(self):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        self.local_enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
        self.local_provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama")
        self.local_model = os.getenv("LOCAL_LLM_MODEL", "phi3:latest")
        self.api_key = os.getenv("OPENAI_API_KEY")

    def route(self, req: LLMRequest) -> LLMRoute:
        if req.intent_class == "TEST":
            return LLMRoute(tier="L0", model="mock", provider="mock")

        if req.cost_tolerance == "zero":
            return LLMRoute(tier="L1", model=self.local_model, provider="ollama")

        if req.cost_tolerance == "low":
            if self.local_enabled:
                return LLMRoute(tier="L1", model=self.local_model, provider="ollama")
            elif self.api_key:
                return LLMRoute(tier="L2", model="gpt-4o-mini", provider="api")
            else:
                raise LLMRoutingError("Routing failed: Low cost requested, but neither Local LLM nor API Key available.")

        if req.cost_tolerance == "high":
            if self.api_key:
                return LLMRoute(tier="L3", model="gpt-4o", provider="api")
            else:
                raise LLMRoutingError("High cost tolerance requested but no API Key available.")

        raise LLMRoutingError(f"Unhandled routing case: {req}")

# --- CLIENT ---

class LLMClient:
    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.provider = provider
        self.router = LLMRouter()
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.strict_mode = os.getenv("LLM_STRICT_MODE", "false").lower() == "true"

    def generate(self, system_prompt: str, user_prompt: str, 
                 intent_class: LLMIntentClass = "INGEST_EXTRACT", 
                 cost_tolerance: CostTolerance = "zero",
                 user_visible: bool = False) -> str:
        if intent_class == "INGEST_EXTRACT":
            raise RuntimeError("INGEST_EXTRACT is forbidden via LLMClient.generate. Use StructuredIngestLLM instead.")
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        request = LLMRequest(
            intent_class=intent_class,
            cost_tolerance=cost_tolerance,
            user_visible=user_visible,
            prompt=full_prompt,
            context={"system_prompt": system_prompt, "user_prompt": user_prompt}
        )

        try:
            route = self.router.route(request)
        except LLMRoutingError as e:
            print(f"[LLMClient] Routing Error: {e}")
            return json.dumps({"error": "ROUTING_FAILED", "details": str(e), "status": "HARD_FAIL"})

        if route.provider == "ollama":
            return self._call_ollama(route.model, system_prompt, user_prompt)
        elif route.provider == "api":
            return self._call_genai_api(route.model, system_prompt, user_prompt)
        return json.dumps({"error": "UNSUPPORTED_PROVIDER", "status": "HARD_FAIL"})

    def _call_ollama(self, model: str, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.ollama_host}/api/chat"
        timeout = int(os.getenv("LLM_TIMEOUT", "600"))
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_ctx": 1024,
                "num_thread": 2,
                "num_predict": 512
            }
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode("utf-8"))
                    return resp_data["message"]["content"]
                return json.dumps({"error": "HTTP_ERROR", "code": response.status})
        except Exception as e:
            return json.dumps({"error": "EXCEPTION", "details": str(e)})

# --- STRUCTURED INGESTION ---

class PointerObject(BaseModel):
    topic_id: str
    json_path: str
    verbatim_quote: str

class ExtractionResponse(BaseModel):
    extracted_pointers: List[PointerObject]

class StructuredIngestLLM:
    def __init__(self):
        model = os.getenv("LOCAL_LLM_MODEL", "phi3:latest")
        self._llm = Ollama(
            model=model,
            temperature=0.0,
            request_timeout=600.0,
            base_url="http://127.0.0.1:11434",
            additional_kwargs={
                "num_ctx": 1024,
                "num_thread": 2,
                "num_predict": 256
            }
        )

    async def extract(self, prompt: str) -> ExtractionResponse:
        enhanced_prompt = "Return ONLY valid JSON. No markdown. No explanation.\n\n" + prompt
        try:
            response = await self._llm.acomplete(enhanced_prompt)
            raw = response.text.strip()
            if raw.startswith("```json"): raw = raw[7:]
            if raw.endswith("```"): raw = raw[:-3]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                parsed = {"extracted_pointers": parsed}
            return ExtractionResponse.model_validate(parsed)
        except Exception as e:
            print(f"[LLM] Extraction failed: {e}")
            return ExtractionResponse(extracted_pointers=[])
