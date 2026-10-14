"""backend/routers/documents.py

Document Intelligence Router (/api/v1/documents)
Thin HTTP controller delegating to DocumentService.
"""

import json
import logging
import time
from typing import Iterator

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.config import settings
from backend.routers.auth import get_current_session
from backend.schemas.documents import (
    DocumentAnalysisResponse,
    DocumentAskRequest,
    DocumentIngestResponse,
    DocumentSummaryRequest,
)
from backend.services.auth_service import SessionInfo
from backend.services.document_service import DocumentService
from backend.upload_utils import read_bounded_file, sanitize_filename

router = APIRouter(prefix="/api/v1/documents", tags=["Documents Intelligence"])
logger = logging.getLogger("backend.documents")


@router.post("/upload", response_model=DocumentIngestResponse, summary="Ingest and parse a document")
@router.post("/parse", response_model=DocumentIngestResponse, summary="Ingest and parse a document (alias)")
async def upload_document(
    file: UploadFile = File(...),
    session: SessionInfo = Depends(get_current_session),
):
    """Accepts PDF, DOCX, TXT, or MD files, delegates to DocumentService for parsing."""
    try:
        content = await read_bounded_file(file, max_bytes=settings.MAX_UPLOAD_SIZE_BYTES)
        filename = sanitize_filename(file.filename, default_name="document.txt")
        doc_data = await run_in_threadpool(DocumentService.ingest_document, content, filename)
        return DocumentIngestResponse(**doc_data)
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(exc)}"
        )


@router.post("/summarize", response_model=DocumentAnalysisResponse, summary="Generate document summary")
async def summarize_document(
    req: DocumentSummaryRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates executive document summarization to DocumentService."""
    try:
        data = await run_in_threadpool(
            DocumentService.summarize_document,
            text=req.text,
            summary_type=req.summary_type,
            provider=req.provider or "Google Gemini",
            model_name=req.model_name,
            api_key=req.api_key,
        )
        return DocumentAnalysisResponse(**data)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization error: {str(exc)}"
        )


def _sse_event(event: str, payload: dict) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/ask/stream", summary="Streaming Ask-the-Document Q&A (Server-Sent Events)")
@router.post("/qa/stream", summary="Streaming Ask-the-Document Q&A (Server-Sent Events) (alias)")
async def ask_document_stream(
    req: DocumentAskRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Stream contextual document Q&A as Server-Sent Events to keep connection alive."""
    if not req.text or not req.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text context is required.",
        )
    if not req.question or not req.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string is required.",
        )

    provider_label = req.provider or "Google Gemini"
    model_name = req.model_name or "gemini-2.5-flash"

    try:
        token_iter: Iterator[str] = DocumentService.stream_question(
            text=req.text,
            question=req.question,
            chat_history=req.chat_history or [],
            provider=provider_label,
            model_name=model_name,
            api_key=req.api_key,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to initialize document Q&A stream: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    def event_stream() -> Iterator[str]:
        started = time.perf_counter()
        chunk_count = 0
        yield ": stream-open\n\n"  # Flush headers immediately to prevent Vercel/proxy timeouts
        try:
            for piece in token_iter:
                if not piece:
                    yield ": keep-alive\n\n"
                    continue
                chunk_count += 1
                yield _sse_event("token", {"token": piece})
            yield _sse_event(
                "done",
                {
                    "provider": provider_label,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "chunks": chunk_count,
                },
            )
        except Exception as exc:
            logger.error("Document stream error: %s", exc, exc_info=True)
            yield _sse_event("error", {"message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ask", summary="Ask the document contextual questions")
@router.post("/qa", summary="Ask the document contextual questions (alias)")
async def ask_document(
    req: DocumentAskRequest,
    request: Request,
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates Ask-the-Document Q&A query to DocumentService, or streams if Accept: text/event-stream."""
    if "text/event-stream" in request.headers.get("accept", "").lower():
        return await ask_document_stream(req, session)

    try:
        data = await run_in_threadpool(
            DocumentService.ask_question,
            text=req.text,
            question=req.question,
            chat_history=req.chat_history or [],
            provider=req.provider or "Google Gemini",
            model_name=req.model_name or "gemini-2.5-flash",
            api_key=req.api_key,
        )
        return DocumentAnalysisResponse(**data)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document Q&A error: {str(exc)}"
        )


@router.post("/{doc_id}/qa/stream", summary="Streaming Document Q&A by ID")
@router.post("/{doc_id}/qa", summary="Document Q&A by ID")
async def ask_document_by_id(
    doc_id: str,
    req: DocumentAskRequest,
    request: Request,
    session: SessionInfo = Depends(get_current_session),
):
    """Ask contextual questions for a document identified by doc_id (stream or unary)."""
    if "text/event-stream" in request.headers.get("accept", "").lower() or request.url.path.endswith("/stream"):
        return await ask_document_stream(req, session)
    return await ask_document(req, request, session)

