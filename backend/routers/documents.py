"""backend/routers/documents.py

Document Intelligence Router (/api/v1/documents)
Thin HTTP controller delegating to DocumentService.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

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
        doc_data = DocumentService.ingest_document(content, filename)
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
        data = DocumentService.summarize_document(
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


@router.post("/ask", response_model=DocumentAnalysisResponse, summary="Ask the document contextual questions")
async def ask_document(
    req: DocumentAskRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates Ask-the-Document Q&A query to DocumentService."""
    try:
        data = DocumentService.ask_question(
            text=req.text,
            question=req.question,
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
            detail=f"Document Q&A error: {str(exc)}"
        )
