"""backend/services/data_service.py

Structured Data Analytics Service layer.
Orchestrates tabular ingestion, Data Health Card profiling, correlation computation,
and AI-assisted dataset insight generation.
Delegates to pipelines/data_pipeline.py.
"""

import io
import logging
from typing import Any, Dict, Optional
import pandas as pd

from core.llm_router import get_last_telemetry
from pipelines.data_pipeline import (
    compute_correlation_matrix,
    generate_data_health_card,
    generate_data_insights,
    load_structured_data,
)

logger = logging.getLogger("data_service")


class DataService:
    """Business orchestration service for Structured Data Analytics."""

    @classmethod
    def profile_data(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate dataset bytes and compute comprehensive Data Health Card."""
        if not file_bytes:
            raise ValueError("Uploaded dataset file content is empty.")

        try:
            df = load_structured_data(file_bytes, filename)
            health = generate_data_health_card(df, filename)
            cols_summary = health["columns_summary_df"].to_dict(orient="records")

            return {
                "filename": health["filename"],
                "total_rows": health["total_rows"],
                "total_cols": health["total_cols"],
                "total_cells": health["total_cells"],
                "missing_cells": health["missing_cells"],
                "missing_percentage": health["missing_percentage"],
                "duplicate_rows": health["duplicate_rows"],
                "duplicate_percentage": health["duplicate_percentage"],
                "memory_usage": health["memory_usage"],
                "numeric_columns": health["numeric_columns"],
                "categorical_columns": health["categorical_columns"],
                "datetime_columns": health["datetime_columns"],
                "columns_summary": cols_summary,
            }
        except Exception as exc:
            logger.error(f"Data profiling failed for {filename}: {exc}")
            raise ValueError(f"Failed to profile dataset '{filename}': {str(exc)}")

    @classmethod
    def generate_insights(
        cls,
        dataset_csv: str,
        user_query: Optional[str] = None,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrate automated EDA or natural language query against dataset."""
        if not dataset_csv or not dataset_csv.strip():
            raise ValueError("dataset_csv string is required for insight generation.")

        try:
            df = pd.read_csv(io.StringIO(dataset_csv))
            if df.empty:
                raise ValueError("Parsed dataset contains zero rows.")

            result = generate_data_insights(
                df=df,
                user_query=user_query,
                model_provider=provider,
                model_name=model_name,
                api_key=api_key,
            )
            telemetry = get_last_telemetry()
            return {
                "result": result,
                "query_type": "user_query" if user_query else "automated_eda",
                "provider_used": telemetry.get("active_provider", provider),
                "latency_ms": telemetry.get("latency_ms", 0.0),
            }
        except Exception as exc:
            logger.error(f"Data insight generation failed: {exc}")
            raise RuntimeError(f"Data insight processing error: {str(exc)}")

    @classmethod
    def compute_correlation(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Compute Pearson correlation values using authoritative data_pipeline implementation."""
        if not file_bytes:
            raise ValueError("Uploaded dataset file content is empty.")

        try:
            df = load_structured_data(file_bytes, filename)
            result = compute_correlation_matrix(df)
            return result
        except Exception as exc:
            logger.error(f"Correlation computation failed for {filename}: {exc}")
            raise ValueError(f"Failed to compute correlation for '{filename}': {str(exc)}")
