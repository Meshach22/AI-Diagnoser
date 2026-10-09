"""backend/routers/router.py

LLM Router API (/api/v1/router)
Thin HTTP controller delegating to ChatService.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.routers.auth import get_current_session, require_admin
from backend.schemas.router import (
    LLMQueryRequest,
    LLMQueryResponse,
    ProvidersCatalogResponse,
    TelemetryResponse,
)
from backend.services.auth_service import SessionInfo
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/router", tags=["LLM Router"])


@router.get("/providers", response_model=ProvidersCatalogResponse, summary="List LLM providers & status")
async def list_providers(session: SessionInfo = Depends(get_current_session)):
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
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates prompt execution across providers to ChatService."""
    try:
        data = ChatService.execute_query(
            prompt=req.prompt,
            provider=req.provider,
            model_name=req.model_name,
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
