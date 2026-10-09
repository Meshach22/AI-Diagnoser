"""backend/routers/data.py

Structured Data Analytics Router (/api/v1/data)
Thin HTTP controller delegating to DataService.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.routers.auth import get_current_session
from backend.schemas.data import (
    CorrelationResponse,
    DataHealthCardResponse,
    DataInsightsRequest,
    DataInsightsResponse,
)
from backend.services.auth_service import SessionInfo
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/data", tags=["Data Analytics"])


@router.post("/profile", response_model=DataHealthCardResponse, summary="Compute comprehensive Data Health Card")
async def profile_dataset(
    file: UploadFile = File(...),
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates tabular data profiling and Data Health Card generation to DataService."""
    try:
        content = await file.read()
        filename = file.filename or "data.csv"
        health = DataService.profile_data(content, filename)
        return DataHealthCardResponse(**health)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data profiling error: {str(exc)}"
        )


@router.post("/insights", response_model=DataInsightsResponse, summary="Generate AI dataset EDA or query answers")
async def get_data_insights(
    req: DataInsightsRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates AI-assisted dataset insight generation to DataService."""
    if not req.dataset_csv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dataset_csv string is required."
        )

    try:
        data = DataService.generate_insights(
            dataset_csv=req.dataset_csv,
            user_query=req.user_query,
            provider=req.provider or "Google Gemini",
            model_name=req.model_name,
            api_key=req.api_key,
        )
        return DataInsightsResponse(**data)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data insights error: {str(exc)}"
        )


@router.post("/correlation", response_model=CorrelationResponse, summary="Compute correlation matrix")
async def get_correlation_matrix(
    file: UploadFile = File(...),
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates Pearson correlation matrix calculation to DataService (consuming authoritative data_pipeline)."""
    try:
        content = await file.read()
        filename = file.filename or "data.csv"
        result = DataService.compute_correlation(content, filename)
        return CorrelationResponse(**result)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Correlation computation error: {str(exc)}"
        )
