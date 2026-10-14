"""backend/routers/router.py

LLM Router API (/api/v1/router)
Thin HTTP controller delegating to ChatService.
"""

import json
import logging
import time
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.routers.auth import get_chat_session, get_current_session, require_admin
from backend.schemas.router import (
    LLMQueryRequest,
    LLMQueryResponse,
    ProvidersCatalogResponse,
    TelemetryResponse,
)
from backend.services.auth_service import SessionInfo
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/router", tags=["LLM Router"])
logger = logging.getLogger("backend.router")


def _sse(event: str, payload: dict) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/providers", response_model=ProvidersCatalogResponse, summary="List LLM providers & status")
async def list_providers(session: SessionInfo = Depends(get_chat_session)):
    """Delegates provider catalog and configuration status queries to ChatService."""
    try:
        catalog = ChatService.list_providers()
        return ProvidersCatalogResponse(**catalog)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve provider catalog: {str(exc)}"
        )


@router.post("/query", response_model=LLMQueryResponse, summary="Direct unified LLM query")
async def execute_query(
    req: LLMQueryRequest,
    session: SessionInfo = Depends(get_chat_session),
):
    """Delegates prompt execution across providers to ChatService."""
    try:
        provider = req.provider
        model_name = req.model_name
        if provider in ("Google Gemini", "gemini", "gemini-3.8-flash"):
            provider = "Google Gemini"
            if not model_name:
                model_name = "gemini-3.8-flash"

        data = await run_in_threadpool(
            ChatService.execute_query,
            prompt=req.prompt,
            provider=provider,
            model_name=model_name,
            api_key=req.api_key,
            image_data=req.image_base64,
        )
        return LLMQueryResponse(**data)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM routing error: {str(exc)}"
        )


@router.post("/query/stream", summary="Streaming LLM query (Server-Sent Events)")
async def execute_query_stream(
    req: LLMQueryRequest,
    session: SessionInfo = Depends(get_chat_session),
):
    """Stream the model answer as SSE: `token` events, then a final `done` (or `error`) event.

    The first bytes are sent immediately and tokens are flushed as the model produces them, so the
    connection never sits idle long enough to hit proxy / serverless timeouts.
    """
    try:
        token_iter: Iterator[str] = ChatService.stream_query(
            prompt=req.prompt,
            provider=req.provider,
            model_name=req.model_name,
            api_key=req.api_key,
            image_data=req.image_base64,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    provider_label = req.provider

    def event_stream() -> Iterator[str]:
        started = time.perf_counter()
        chunk_count = 0
        yield ": stream-open\n\n"  # flush headers immediately
        try:
            for piece in token_iter:
                if not piece:
                    yield ": keep-alive\n\n"
                    continue
                chunk_count += 1
                yield _sse("token", {"token": piece})
            yield _sse(
                "done",
                {
                    "provider": provider_label,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "chunks": chunk_count,
                },
            )
        except Exception as exc:  # noqa: BLE001 - surface any provider failure to the client
            logger.error("LLM stream failed for provider '%s': %s", provider_label, exc, exc_info=True)
            yield _sse("error", {"message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx/Render proxy buffering
        },
    )


@router.get("/telemetry", response_model=TelemetryResponse, summary="Get live LLM router telemetry")
async def get_telemetry(session: SessionInfo = Depends(require_admin)):
    """Delegates latest telemetry snapshot retrieval to ChatService (Administrative role required)."""
    try:
        telemetry = ChatService.get_telemetry()
        return TelemetryResponse(**telemetry)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve telemetry: {str(exc)}"
        )
