"""tests/test_services.py

Unit tests for backend Service Layer:
- DocumentService
- VisionService
- DataService
- ChatService
Verifies pipeline invocation, normalized response schemas, and error handling.
"""

import io
from unittest.mock import patch
from PIL import Image

from backend.services.chat_service import ChatService
from backend.services.data_service import DataService
from backend.services.document_service import DocumentService
from backend.services.vision_service import VisionService


# ---------------------------------------------------------------------------
# 1. DocumentService Tests
# ---------------------------------------------------------------------------
def test_document_service_ingest():
    """Verify DocumentService ingests and parses raw document bytes."""
    sample_text = "Executive Briefing: Revenue increased by 15% across all regions in Q3."
    raw_bytes = sample_text.encode("utf-8")

    result = DocumentService.ingest_document(raw_bytes, "briefing.txt")

    assert result["file_type"] == "TXT"
    assert "Revenue increased by 15%" in result["full_text"]
    assert result["word_count"] > 0
    assert result["page_count"] == 1


def test_document_service_empty_input_raises_error():
    """Verify DocumentService raises ValueError on empty file bytes."""
    try:
        DocumentService.ingest_document(b"", "empty.txt")
        assert False, "Expected ValueError on empty bytes"
    except ValueError as exc:
        assert "empty" in str(exc).lower()


@patch("backend.services.document_service.generate_document_summary")
def test_document_service_summarize(mock_summary):
    """Verify DocumentService orchestrates summarization and normalizes response."""
    mock_summary.return_value = "- Highlight 1: Revenue up 15%\n- Highlight 2: Margins healthy"

    res = DocumentService.summarize_document(
        text="Sample document body for summarization.",
        summary_type="executive",
        provider="Google Gemini"
    )

    mock_summary.assert_called_once()
    assert res["result"] == "- Highlight 1: Revenue up 15%\n- Highlight 2: Margins healthy"
    assert res["summary_type"] == "executive"
    assert "provider_used" in res
    assert "latency_ms" in res


@patch("backend.services.document_service.ask_document_question")
def test_document_service_ask(mock_ask):
    """Verify DocumentService orchestrates Ask-the-Document Q&A."""
    mock_ask.return_value = "The research expenditure was $3.4M."

    res = DocumentService.ask_question(
        text="Financial context with $3.4M R&D.",
        question="What was R&D spend?",
        provider="Google Gemini"
    )

    mock_ask.assert_called_once()
    assert res["result"] == "The research expenditure was $3.4M."
    assert res["summary_type"] == "qa"


# ---------------------------------------------------------------------------
# 2. VisionService Tests
# ---------------------------------------------------------------------------
def test_vision_service_extract_metadata():
    """Verify VisionService extracts image dimensions and dominant colors."""
    # Create small in-memory 100x100 RGB image
    img = Image.new("RGB", (100, 100), color=(198, 93, 59))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    meta = VisionService.extract_metadata(raw_bytes, "test_chart.png")

    assert meta["filename"] == "test_chart.png"
    assert meta["format"] in ["PNG", "JPEG"]
    assert "100" in meta["dimensions"] and "px" in meta["dimensions"]
    assert meta["mode"] == "RGB"
    assert len(meta["dominant_colors"]) > 0
    assert meta["dominant_colors"][0]["hex"].startswith("#")


@patch("backend.services.vision_service.analyze_image_with_llm")
def test_vision_service_analyze_data_uri(mock_analyze):
    """Verify VisionService accepts data:image/... Data URIs."""
    mock_analyze.return_value = "Chart indicates steady growth from Q1 to Q4."

    res = VisionService.analyze_image(
        image_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        task_type="ocr",
        provider="Google Gemini"
    )

    mock_analyze.assert_called_once()
    assert res["result"] == "Chart indicates steady growth from Q1 to Q4."
    assert res["task_type"] == "ocr"


@patch("backend.services.vision_service.analyze_image_with_llm")
def test_vision_service_analyze_raw_base64(mock_analyze):
    """Verify VisionService accepts raw base64 strings without data:image prefix."""
    mock_analyze.return_value = "Visual description of raw base64 image."

    res = VisionService.analyze_image(
        image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        task_type="describe",
        provider="Google Gemini"
    )

    mock_analyze.assert_called_once()
    assert res["result"] == "Visual description of raw base64 image."
    assert res["task_type"] == "describe"


def test_vision_service_analyze_invalid_payload_raises_value_error():
    """Verify VisionService raises ValueError on malformed or non-image payloads without unhandled crashes."""
    for bad_input in ["malformed_base64!!!", "bm90IGFuIGltYWdl"]:
        try:
            VisionService.analyze_image(
                image_base64=bad_input,
                task_type="ocr",
                provider="Offline Heuristics"
            )
            assert False, f"Expected ValueError for bad input: {bad_input}"
        except ValueError as exc:
            assert "image" in str(exc).lower()


# ---------------------------------------------------------------------------
# 3. DataService Tests
# ---------------------------------------------------------------------------
def test_data_service_profile():
    """Verify DataService profiles CSV and computes Data Health Card."""
    csv_bytes = b"id,name,amount,active\n1,Alpha,100.5,True\n2,Beta,200.0,False\n3,Gamma,300.2,True\n"

    health = DataService.profile_data(csv_bytes, "sales.csv")

    assert health["filename"] == "sales.csv"
    assert health["total_rows"] == 3
    assert health["total_cols"] == 4
    assert "amount" in health["numeric_columns"]
    assert len(health["columns_summary"]) == 4


def test_data_service_correlation():
    """Verify DataService computes Pearson correlation using authoritative pipeline."""
    csv_bytes = b"x,y,z\n1,2,10\n2,4,20\n3,6,30\n4,8,40\n"

    corr = DataService.compute_correlation(csv_bytes, "metrics.csv")

    assert corr["columns"] == ["x", "y", "z"]
    assert len(corr["matrix"]) == 3
    assert corr["matrix"][0][1] == 1.0  # Perfect linear correlation between x and y


@patch("backend.services.data_service.generate_data_insights")
def test_data_service_insights(mock_insights):
    """Verify DataService orchestrates automated EDA or query insights."""
    mock_insights.return_value = "### Key Patterns\nPositive linear trend detected between x and y."

    res = DataService.generate_insights(
        dataset_csv="x,y\n1,2\n2,4\n3,6\n",
        user_query="Describe trends",
        provider="Google Gemini"
    )

    mock_insights.assert_called_once()
    assert "Positive linear trend" in res["result"]
    assert res["query_type"] == "user_query"


# ---------------------------------------------------------------------------
# 4. ChatService Tests
# ---------------------------------------------------------------------------
def test_chat_service_list_providers():
    """Verify ChatService returns provider catalog."""
    catalog = ChatService.list_providers()

    assert "providers" in catalog
    provider_names = [p["name"] for p in catalog["providers"]]
    assert "Google Gemini" in provider_names
    assert "OpenAI" in provider_names
    assert "Groq" in provider_names


@patch("backend.services.chat_service.query_llm")
def test_chat_service_execute_query(mock_query):
    """Verify ChatService delegates to LLM Router."""
    mock_query.return_value = "Synthesized diagnostic response."

    res = ChatService.execute_query(
        prompt="Synthesize quarterly telemetry",
        provider="Google Gemini"
    )

    mock_query.assert_called_once()
    assert res["response"] == "Synthesized diagnostic response."
    assert "latency_ms" in res
    assert "primary_provider" in res
