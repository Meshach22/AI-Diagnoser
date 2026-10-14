"""backend/schemas/documents.py

Schemas for Document Intelligence API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


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
    text: Optional[str] = Field(default=None, description="Document context to query against")
    document_text: Optional[str] = Field(default=None, description="Alias for text")
    question: Optional[str] = Field(default=None, description="Question to ask about the document")
    query: Optional[str] = Field(default=None, description="Alias for question")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider: Google Gemini, OpenAI, Groq, etc.")
    model_name: Optional[str] = Field(default=None, description="Model override")
    api_key: Optional[str] = Field(default=None, description="Optional per-request API key")
    chat_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Recent conversation turns for multi-turn grounding")
    history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Alias for chat_history")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("text") and data.get("document_text"):
                data["text"] = data["document_text"]
            if not data.get("question") and data.get("query"):
                data["question"] = data["query"]
            if not data.get("chat_history") and data.get("history"):
                data["chat_history"] = data["history"]
            if not data.get("text"):
                raise ValueError("text or document_text is required")
            if not data.get("question"):
                raise ValueError("question or query is required")
        return data


class DocumentIngestResponse(BaseModel):
    """Response containing parsed document structure."""
    id: Optional[str] = None
    filename: str
    file_type: str
    word_count: int
    char_count: int
    page_count: int
    reading_time_min: float
    full_text: str
    pages_or_chunks: List[str]
    character_count: Optional[int] = None
    preview: Optional[str] = None
    has_extractable_text: bool = True


class DocumentAnalysisResponse(BaseModel):
    """Response for summarization or Q&A."""
    result: str
    summary_type: Optional[str] = None
    provider_used: str
    latency_ms: Optional[float] = None
