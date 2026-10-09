"""backend/schemas/documents.py

Schemas for Document Intelligence API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentSummaryRequest(BaseModel):
    """Request payload for document summarization."""
    text: str = Field(..., description="Document body text to summarize")
    summary_type: str = Field(
        default="executive",
        description="Type of summary: 'executive', 'key_takeaways', or 'deep_dive'"
    )
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider: Google Gemini, OpenAI, Groq, etc.")
    model_name: Optional[str] = Field(default=None, description="Model override")
    api_key: Optional[str] = Field(default=None, description="Optional per-request API key")


class DocumentAskRequest(BaseModel):
    """Request payload for Ask-the-Document Q&A."""
    text: str = Field(..., description="Document context to query against")
    question: str = Field(..., description="Question to ask about the document")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider: Google Gemini, OpenAI, Groq, etc.")
    model_name: Optional[str] = Field(default=None, description="Model override")
    api_key: Optional[str] = Field(default=None, description="Optional per-request API key")


class DocumentIngestResponse(BaseModel):
    """Response containing parsed document structure."""
    filename: str
    file_type: str
    word_count: int
    char_count: int
    page_count: int
    reading_time_min: float
    full_text: str
    pages_or_chunks: List[str]


class DocumentAnalysisResponse(BaseModel):
    """Response for summarization or Q&A."""
    result: str
    summary_type: Optional[str] = None
    provider_used: str
    latency_ms: Optional[float] = None
