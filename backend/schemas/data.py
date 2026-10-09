"""backend/schemas/data.py

Schemas for Structured Data Analytics API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnDiagnostic(BaseModel):
    """Diagnostic profile for a single column."""
    column: str
    type: str
    missing: str
    unique: int
    sample: str


class DataHealthCardResponse(BaseModel):
    """Comprehensive statistical and data health response."""
    filename: str
    total_rows: int
    total_cols: int
    total_cells: int
    missing_cells: int
    missing_percentage: float
    duplicate_rows: int
    duplicate_percentage: float
    memory_usage: str
    numeric_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str]
    columns_summary: List[Dict[str, Any]]


class DataInsightsRequest(BaseModel):
    """Request payload for AI Dataset Intelligence or Natural Language querying."""
    dataset_csv: Optional[str] = Field(default=None, description="CSV dataset raw text string")
    user_query: Optional[str] = Field(default=None, description="Natural language analytical query")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider: Google Gemini, OpenAI, Groq")
    model_name: Optional[str] = Field(default=None, description="Model override")
    api_key: Optional[str] = Field(default=None, description="Optional per-request API key")


class DataInsightsResponse(BaseModel):
    """Response containing AI-generated EDA or analytical insights."""
    result: str
    query_type: str
    provider_used: str
    latency_ms: Optional[float] = None


class CorrelationResponse(BaseModel):
    """Pearson correlation matrix response model."""
    columns: List[str]
    matrix: List[List[float]]
    shape: List[int]
    message: Optional[str] = None
