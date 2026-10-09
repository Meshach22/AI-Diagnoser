"""backend/routers/vision.py

Vision Intelligence Router (/api/v1/vision)
Thin HTTP controller delegating to VisionService.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.routers.auth import get_current_session
from backend.schemas.vision import (
    ImageMetadataResponse,
    VisionAnalysisRequest,
    VisionAnalysisResponse,
)
from backend.services.auth_service import SessionInfo
from backend.services.vision_service import VisionService

router = APIRouter(prefix="/api/v1/vision", tags=["Vision Intelligence"])


@router.post("/metadata", response_model=ImageMetadataResponse, summary="Extract image metadata & dominant colors")
async def get_image_metadata(
    file: UploadFile = File(...),
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates visual geometry profiling and dominant color extraction to VisionService."""
    try:
        content = await file.read()
        filename = file.filename or "image.png"
        meta = VisionService.extract_metadata(content, filename)
        return ImageMetadataResponse(**meta)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image processing error: {str(exc)}"
        )


@router.post("/analyze", response_model=VisionAnalysisResponse, summary="Execute multimodal vision analysis")
async def analyze_image(
    req: VisionAnalysisRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Delegates multimodal OCR, visual descriptions, and audits to VisionService."""
    if not req.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_base64 payload is required."
        )

    try:
        data = VisionService.analyze_image(
            image_base64=req.image_base64,
            task_type=req.task_type,
            custom_prompt=req.custom_prompt,
            provider=req.provider or "Google Gemini",
            model_name=req.model_name,
            api_key=req.api_key,
        )
        return VisionAnalysisResponse(**data)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision analysis error: {str(exc)}"
        )
