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
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Orchestrate document summarization with telemetry capture and 60.0s timeout."""
        if not text or not text.strip():
            raise ValueError("Document body text is required for summarization.")

        valid_types = {"executive", "key_takeaways", "action_items", "action_items_and_risks", "deep_dive"}
        effective_type = summary_type if summary_type in valid_types else "executive"
        effective_model = model_name or "gemini-2.5-flash"

        try:
            result = generate_document_summary(
                doc_text=text.strip(),
                summary_type=effective_type,
                model_provider=provider,
                model_name=effective_model,
                api_key=api_key,
                timeout=timeout,
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
        chat_history: Optional[list] = None,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Orchestrate contextual Ask-the-Document Q&A with multi-turn chat history and 60.0s timeout."""
        if not text or not text.strip():
            raise ValueError("Document text context is required for Q&A.")
        if not question or not question.strip():
            raise ValueError("Query question string is required.")

        effective_model = model_name or "gemini-2.5-flash"

        try:
            result = ask_document_question(
                doc_text=text.strip(),
                question=question.strip(),
                chat_history=chat_history or [],
                model_provider=provider,
                model_name=effective_model,
                api_key=api_key,
                timeout=timeout,
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

    @classmethod
    def stream_question(
        cls,
        text: str,
        question: str,
        chat_history: Optional[list] = None,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Stream contextual Ask-the-Document Q&A tokens via stream_llm."""
        if not text or not text.strip():
            raise ValueError("Document text context is required for Q&A.")
        if not question or not question.strip():
            raise ValueError("Query question string is required.")

        from core.llm_router import escape_boundary_tags, stream_llm
        from core.prompt_policy import build_document_qa_prompt

        max_chars = 30000
        truncated_text = text.strip()[:max_chars]
        escaped_doc = escape_boundary_tags(truncated_text)
        escaped_query = escape_boundary_tags(question.strip())

        prompt = build_document_qa_prompt(
            document_text=escaped_doc,
            user_query=escaped_query,
            chat_history=chat_history or [],
        )

        effective_model = model_name or "gemini-2.5-flash"
        return stream_llm(
            prompt=prompt,
            model_provider=provider or "Google Gemini",
            model_name=effective_model,
            api_key=api_key,
            max_output_tokens=1024,
        )

