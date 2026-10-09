"""backend/schemas/router.py

Schemas for LLM Router queries, providers, and telemetry.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMQueryRequest(BaseModel):
    """Direct query payload for the LLM Router."""
    prompt: str = Field(..., description="Prompt or query instructions")
    provider: str = Field(default="Google Gemini", description="Provider: Google Gemini, OpenAI, Groq, Ollama, Offline Heuristics")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    api_key: Optional[str] = Field(default=None, description="Optional API key override")
    image_base64: Optional[str] = Field(default=None, description="Optional base64 encoded image for multimodal inference")


class LLMQueryResponse(BaseModel):
    """Unified LLM query output."""
    response: str
    primary_provider: str
    active_provider: str
    latency_ms: float
    fallback_depth: int
    failover_badge: Optional[str] = None


class ProviderInfo(BaseModel):
    """Catalog info for an individual provider."""
    name: str
    primary_model: str
    models: List[str]
    description: str
    requires_api_key: bool
    supports_vision: bool
    is_configured: bool


class ProvidersCatalogResponse(BaseModel):
    """Listing of all available providers and their current readiness."""
    providers: List[ProviderInfo]
    default_provider: str


class TelemetryResponse(BaseModel):
    """Live telemetry state."""
    active_provider: str
    primary_provider: str
    latency_ms: float
    fallback_depth: int
    failover_badge: Optional[str] = None
