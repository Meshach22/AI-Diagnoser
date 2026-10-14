import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import closing
from typing import Any, Dict, List, Optional

from backend.config import settings
from core.llm_router import get_last_telemetry
from pipelines.document_pipeline import (
    ask_document_question,
    generate_document_summary,
    load_document,
)

logger = logging.getLogger("document_service")


class DocumentService:
    """Business orchestration service for Document Intelligence & Library Persistence."""

    @classmethod
    def _connect_db(cls) -> sqlite3.Connection:
        db_path = settings.AUTH_DB_PATH
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_documents (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 0,
                user_email TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL DEFAULT 'document',
                format TEXT NOT NULL DEFAULT 'text',
                character_count INTEGER NOT NULL DEFAULT 0,
                word_count INTEGER NOT NULL DEFAULT 0,
                page_count INTEGER NOT NULL DEFAULT 1,
                preview TEXT,
                full_text TEXT NOT NULL,
                chunks_json TEXT,
                created_at REAL NOT NULL
            );
            """
        )
        try:
            conn.execute("ALTER TABLE user_documents ADD COLUMN user_email TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_documents_user ON user_documents(user_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_docs_email ON user_documents(user_email);")
        return conn

    @classmethod
    def save_user_document(
        cls,
        user_identifier: Any,
        doc_data: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Persist ingested document metadata, raw text, and chunks in SQLite bound to user."""
        if not user_identifier:
            return doc_data
        doc_id = str(doc_data.get("id") or f"doc_{uuid.uuid4().hex[:12]}")
        doc_data["id"] = doc_id
        now = time.time()
        chunks = doc_data.get("chunks", [])
        chunks_json = json.dumps(chunks) if chunks else "[]"
        user_email = str(user_identifier).strip().lower() if (isinstance(user_identifier, str) and "@" in user_identifier) else ""
        resolved_user_id = user_id or (user_identifier if isinstance(user_identifier, int) else 0)

        with closing(cls._connect_db()) as conn, conn:
            conn.execute(
                """
                INSERT INTO user_documents (
                    id, user_id, user_email, filename, file_type, format,
                    character_count, word_count, page_count,
                    preview, full_text, chunks_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_email = excluded.user_email,
                    filename = excluded.filename,
                    character_count = excluded.character_count,
                    word_count = excluded.word_count,
                    page_count = excluded.page_count,
                    preview = excluded.preview,
                    full_text = excluded.full_text,
                    chunks_json = excluded.chunks_json,
                    created_at = excluded.created_at
                """,
                (
                    doc_id,
                    resolved_user_id,
                    user_email,
                    doc_data.get("filename", "document.txt"),
                    doc_data.get("file_type", "document"),
                    doc_data.get("format", "text"),
                    int(doc_data.get("character_count", 0)),
                    int(doc_data.get("word_count", 0)),
                    int(doc_data.get("page_count", 1)),
                    doc_data.get("preview", ""),
                    doc_data.get("full_text", ""),
                    chunks_json,
                    now,
                ),
            )
        return doc_data

    @classmethod
    def get_documents_by_user(cls, user_email: str) -> List[Dict[str, Any]]:
        """Queries and returns all documents uploaded by that email ordered by creation time descending."""
        if not user_email:
            return []
        clean_email = str(user_email).strip().lower()
        with closing(cls._connect_db()) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, user_email, filename, file_type, format,
                       character_count, word_count, page_count,
                       preview, full_text, chunks_json, created_at
                FROM user_documents
                WHERE user_email = ?
                ORDER BY created_at DESC
                """,
                (clean_email,),
            ).fetchall()
        result = []
        for r in rows:
            chunks = []
            if r["chunks_json"]:
                try:
                    chunks = json.loads(r["chunks_json"])
                except Exception:
                    chunks = []
            result.append({
                "id": r["id"],
                "filename": r["filename"],
                "file_type": r["file_type"],
                "format": r["format"],
                "character_count": r["character_count"],
                "word_count": r["word_count"],
                "page_count": r["page_count"],
                "preview": r["preview"],
                "full_text": r["full_text"],
                "chunks": chunks,
                "created_at": r["created_at"],
            })
        return result

    @classmethod
    def list_user_documents(cls, user_identifier: Any) -> List[Dict[str, Any]]:
        """Retrieve all historical documents uploaded by the authenticated user (by email or id)."""
        if not user_identifier:
            return []
        if isinstance(user_identifier, str) and "@" in user_identifier:
            return cls.get_documents_by_user(user_identifier)
        with closing(cls._connect_db()) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, user_email, filename, file_type, format,
                       character_count, word_count, page_count,
                       preview, full_text, chunks_json, created_at
                FROM user_documents
                WHERE user_id = ? OR user_email = ?
                ORDER BY created_at DESC
                """,
                (user_identifier, str(user_identifier).strip().lower()),
            ).fetchall()
        result = []
        for r in rows:
            chunks = []
            if r["chunks_json"]:
                try:
                    chunks = json.loads(r["chunks_json"])
                except Exception:
                    chunks = []
            result.append({
                "id": r["id"],
                "filename": r["filename"],
                "file_type": r["file_type"],
                "format": r["format"],
                "character_count": r["character_count"],
                "word_count": r["word_count"],
                "page_count": r["page_count"],
                "preview": r["preview"],
                "full_text": r["full_text"],
                "chunks": chunks,
                "created_at": r["created_at"],
            })
        return result

    @classmethod
    def delete_user_document(cls, user_identifier: Any, doc_id: str) -> bool:
        """Delete an uploaded document belonging to the user."""
        if not user_identifier or not doc_id:
            return False
        with closing(cls._connect_db()) as conn, conn:
            if isinstance(user_identifier, str) and "@" in user_identifier:
                cur = conn.execute("DELETE FROM user_documents WHERE id = ? AND user_email = ?", (doc_id, user_identifier.strip().lower()))
            else:
                cur = conn.execute("DELETE FROM user_documents WHERE id = ? AND (user_id = ? OR user_email = ?)", (doc_id, user_identifier, str(user_identifier)))
            return cur.rowcount > 0

    @classmethod
    def ingest_document(
        cls,
        file_bytes: bytes,
        filename: str,
        user_identifier: Optional[Any] = None,
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate input bytes, parse document structure, and persist to SQLite if user is provided."""
        if not file_bytes:
            raise ValueError("Uploaded document file content is empty.")

        try:
            doc_data = load_document(file_bytes, filename)
            target_user = user_email or user_identifier
            if target_user:
                doc_data = cls.save_user_document(target_user, doc_data)
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
        effective_model = model_name or "gemini-3.8-flash"

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

