"""backend/schemas/vision.py

Schemas for Vision Intelligence API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VisionAnalysisRequest(BaseModel):
    """Request payload for visual inspection or multimodal OCR."""
    image_base64: Optional[str] = Field(default=None, description="Base64-encoded image string")
    task_type: str = Field(
        default="describe",
        description="Task: 'ocr', 'describe', 'chart_diagram', 'document_audit', or 'custom'"
    )
    custom_prompt: Optional[str] = Field(default=None, description="Prompt when task_type is 'custom'")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider: Google Gemini, OpenAI, Groq")
    model_name: Optional[str] = Field(default=None, description="Model override")
    api_key: Optional[str] = Field(default=None, description="Optional per-request API key")


class ColorSwatch(BaseModel):
    """Dominant color swatch entry."""
    hex: str
    rgb: List[int]
    percentage: float
    is_dark: bool


class ImageMetadataResponse(BaseModel):
    """Metadata response for image assets."""
    filename: str
    format: str
    dimensions: str
    megapixels: float
    aspect_ratio: float
    aspect_desc: str
    file_size_formatted: str
    mode: str
    dominant_colors: Optional[List[ColorSwatch]] = None


class VisionAnalysisResponse(BaseModel):
    """Response containing vision model analysis output."""
    result: str
    task_type: str
    provider_used: str
    latency_ms: Optional[float] = None
