"""backend/services/document_service.py

Document Intelligence Service layer.
Orchestrates document ingestion, multi-tier executive summarization, and contextual Q&A.
Delegates to pipelines/document_pipeline.py and core/llm_router.py.
"""

import logging
from typing import Any, Dict, Optional

from core.llm_router import get_last_telemetry
from pipelines.document_pipeline import (
    ask_document_question,
    generate_document_summary,
    load_document,
)

logger = logging.getLogger("document_service")


class DocumentService:
    """Business orchestration service for Document Intelligence."""

    @classmethod
    def ingest_document(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate input bytes and parse document structure via document_pipeline."""
        if not file_bytes:
            raise ValueError("Uploaded document file content is empty.")

        try:
            doc_data = load_document(file_bytes, filename)
            return doc_data
        except Exception as exc:
            logger.error(f"Document ingestion failed for {filename}: {exc}")
            raise ValueError(f"Failed to parse document '{filename}': {str(exc)}")

    @classmethod
    def summarize_document(
        cls,
        text: str,
        summary_type: str = "executive",
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrate document summarization with telemetry capture."""
        if not text or not text.strip():
            raise ValueError("Document body text is required for summarization.")

        valid_types = {"executive", "key_takeaways", "deep_dive"}
        effective_type = summary_type if summary_type in valid_types else "executive"

        try:
            result = generate_document_summary(
                doc_text=text.strip(),
                summary_type=effective_type,
                model_provider=provider,
                model_name=model_name,
                api_key=api_key,
            )
            telemetry = get_last_telemetry()
            return {
                "result": result,
                "summary_type": effective_type,
                "provider_used": telemetry.get("active_provider", provider),
                "latency_ms": telemetry.get("latency_ms", 0.0),
            }
        except Exception as exc:
            logger.error(f"Document summarization failed: {exc}")
            raise RuntimeError(f"Summarization processing error: {str(exc)}")

    @classmethod
    def ask_question(
        cls,
        text: str,
        question: str,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrate contextual Ask-the-Document Q&A."""
        if not text or not text.strip():
            raise ValueError("Document text context is required for Q&A.")
        if not question or not question.strip():
            raise ValueError("Query question string is required.")

        try:
            result = ask_document_question(
                doc_text=text.strip(),
                question=question.strip(),
                model_provider=provider,
                model_name=model_name,
                api_key=api_key,
            )
            telemetry = get_last_telemetry()
            return {
                "result": result,
                "summary_type": "qa",
                "provider_used": telemetry.get("active_provider", provider),
                "latency_ms": telemetry.get("latency_ms", 0.0),
            }
        except Exception as exc:
            logger.error(f"Document Q&A failed: {exc}")
            raise RuntimeError(f"Document Q&A processing error: {str(exc)}")
