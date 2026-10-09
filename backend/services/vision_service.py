"""backend/services/vision_service.py

Vision Intelligence Service layer.
Orchestrates image ingestion, technical metadata profiling, dominant color swatches,
and multimodal LLM inspection. Delegates to pipelines/image_pipeline.py.
"""

import logging
from typing import Any, Dict, List, Optional

from core.llm_router import get_last_telemetry
from pipelines.image_pipeline import (
    analyze_image_with_llm,
    extract_dominant_colors,
    extract_image_metadata,
    load_image,
)

logger = logging.getLogger("vision_service")


class VisionService:
    """Business orchestration service for Computer Vision and OCR."""

    @classmethod
    def extract_metadata(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate visual asset bytes, compute geometry, and extract dominant color swatches."""
        if not file_bytes:
            raise ValueError("Uploaded image file content is empty.")

        try:
            pil_img = load_image(file_bytes)
            meta = extract_image_metadata(pil_img, len(file_bytes), filename)
            swatches_raw = extract_dominant_colors(pil_img, num_colors=5)

            swatches = [
                {
                    "hex": s["hex"],
                    "rgb": list(s["rgb"]),
                    "percentage": s["percentage"],
                    "is_dark": s["is_dark"],
                }
                for s in swatches_raw
            ]

            width = meta.get("width", pil_img.size[0])
            height = meta.get("height", pil_img.size[1])
            ratio_float = round(width / height, 2) if height > 0 else 1.0
            aspect_desc_str = str(meta.get("aspect_ratio") or f"{ratio_float}:1")

            return {
                "filename": meta.get("filename", filename),
                "format": meta.get("format", "PNG"),
                "dimensions": meta.get("dimensions", f"{width} × {height} px"),
                "megapixels": float(meta.get("megapixels", round((width * height) / 1_000_000, 2))),
                "aspect_ratio": ratio_float,
                "aspect_desc": aspect_desc_str,
                "file_size_formatted": meta.get("file_size_formatted", "0 KB"),
                "mode": meta.get("mode", pil_img.mode),
                "dominant_colors": swatches,
            }
        except Exception as exc:
            logger.error(f"Image metadata extraction failed for {filename}: {exc}")
            raise ValueError(f"Failed to process visual asset '{filename}': {str(exc)}")

    @classmethod
    def analyze_image(
        cls,
        image_base64: str,
        task_type: str = "describe",
        custom_prompt: Optional[str] = None,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrate multimodal vision analysis across LLM providers."""
        if not image_base64 or not image_base64.strip():
            raise ValueError("image_base64 string is required for vision analysis.")

        valid_tasks = {"ocr", "describe", "chart_diagram", "document_audit", "custom"}
        effective_task = task_type if task_type in valid_tasks else "describe"

        try:
            result = analyze_image_with_llm(
                image=image_base64,
                task_type=effective_task,
                custom_prompt=custom_prompt,
                model_provider=provider,
                model_name=model_name,
                api_key=api_key,
            )
            telemetry = get_last_telemetry()
            return {
                "result": result,
                "task_type": effective_task,
                "provider_used": telemetry.get("active_provider", provider),
                "latency_ms": telemetry.get("latency_ms", 0.0),
            }
        except ValueError:
            raise
        except Exception as exc:
            logger.error(f"Multimodal vision analysis failed: {exc}")
            raise RuntimeError(f"Vision analysis processing error: {str(exc)}")
