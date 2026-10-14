"""backend/services/chat_service.py

Chat & LLM Routing Service layer.
Orchestrates application-level LLM queries across Google Gemini, OpenAI, Groq, and fallbacks.
Delegates to core/llm_router.py without duplicating provider algorithms.
"""

import logging
import os
from typing import Any, Dict, Iterator, List, Optional

from core.config import MODEL_CATALOG
from core.llm_router import get_last_telemetry, query_llm, stream_llm

logger = logging.getLogger("chat_service")


class ChatService:
    """Business orchestration service for LLM queries and Provider discovery."""

    @classmethod
    def list_providers(cls) -> Dict[str, Any]:
        """Inspect provider catalog and configuration status."""
        providers_list = []

        key_checks = {
            "Google Gemini": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
            "Groq": bool(os.getenv("GROQ_API_KEY")),
            "DeepSeek": bool(os.getenv("DEEPSEEK_API_KEY")),
            "Ollama": True,
            "Offline Heuristics": True,
        }

        for name, cat in MODEL_CATALOG.items():
            is_conf = key_checks.get(name, False) if cat.get("requires_api_key", True) else True
            providers_list.append({
                "name": name,
                "primary_model": cat["primary_model"],
                "models": cat["models"],
                "description": cat["description"],
                "requires_api_key": cat["requires_api_key"],
                "supports_vision": cat["supports_vision"],
                "is_configured": is_conf,
            })

        return {
            "providers": providers_list,
            "default_provider": "Google Gemini",
        }

    @classmethod
    def execute_query(
        cls,
        prompt: str,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        image_data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute a unified multimodal or text query through the authoritative LLM Router."""
        if not prompt or not prompt.strip():
            raise ValueError("Query prompt string is required.")

        # Ensure provider 'Google Gemini' routes directly to gemini-3.8-flash as active primary model
        if provider in ("Google Gemini", "gemini", "gemini-3.8-flash"):
            provider = "Google Gemini"
            if not model_name:
                model_name = "gemini-3.8-flash"

        try:
            result = query_llm(
                prompt=prompt.strip(),
                model_provider=provider,
                model_name=model_name,
                api_key=api_key,
                image_data=image_data,
            )
            telemetry = get_last_telemetry()
            output_text = result or f"[{provider} Engine Error: No content returned from model cascade. Please check API keys in .env]"
            return {
                "response": output_text,
                "result": output_text,
                "primary_provider": telemetry.get("primary_provider", provider),
                "active_provider": telemetry.get("active_provider", provider),
                "latency_ms": telemetry.get("latency_ms", 0.0),
                "fallback_depth": telemetry.get("fallback_depth", 0),
                "failover_badge": telemetry.get("failover_badge"),
            }
        except Exception as exc:
            logger.error(f"Chat service query execution failed: {exc}")
            err_diag = f"[{provider} Engine Error: {type(exc).__name__}: {str(exc)} - please check API keys in .env]"
            return {
                "response": err_diag,
                "result": err_diag,
                "primary_provider": provider,
                "active_provider": provider,
                "latency_ms": 0.0,
                "fallback_depth": 1,
                "failover_badge": f"Failed: {type(exc).__name__}",
            }

    @classmethod
    def stream_query(
        cls,
        prompt: str,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        image_data: Optional[Any] = None,
    ) -> Iterator[str]:
        """Validate the request and return a token iterator (empty string == keep-alive heartbeat)."""
        if not prompt or not prompt.strip():
            raise ValueError("Query prompt string is required.")

        if provider in ("Google Gemini", "gemini", "gemini-3.8-flash"):
            provider = "Google Gemini"
            if not model_name:
                model_name = "gemini-3.8-flash"

        return stream_llm(
            prompt=prompt.strip(),
            model_provider=provider,
            model_name=model_name,
            api_key=api_key,
            image_data=image_data,
        )

    @classmethod
    def get_telemetry(cls) -> Dict[str, Any]:
        """Retrieve latest telemetry snapshot from core router."""
        telemetry = get_last_telemetry()
        return {
            "active_provider": telemetry.get("active_provider", "Google Gemini"),
            "primary_provider": telemetry.get("primary_provider", "Google Gemini"),
            "latency_ms": telemetry.get("latency_ms", 0.0),
            "fallback_depth": telemetry.get("fallback_depth", 0),
            "failover_badge": telemetry.get("failover_badge"),
        }
