"""tests/test_services.py

Unit tests for backend Service Layer:
- DocumentService
- VisionService
- DataService
- ChatService
Verifies pipeline invocation, normalized response schemas, and error handling.
Structured as a standard unittest.TestCase harness to ensure automated test discovery (TEST-001).
"""

import io
import unittest
from unittest.mock import patch
from PIL import Image

from backend.services.chat_service import ChatService
from backend.services.data_service import DataService
from backend.services.document_service import DocumentService
from backend.services.vision_service import VisionService


class TestBackendServices(unittest.TestCase):
    """Test suite covering the backend service orchestration layer."""

    # ---------------------------------------------------------------------------
    # 1. DocumentService Tests
    # ---------------------------------------------------------------------------
    def test_document_service_ingest(self):
        """Verify DocumentService ingests and parses raw document bytes."""
        sample_text = "Executive Briefing: Revenue increased by 15% across all regions in Q3."
        raw_bytes = sample_text.encode("utf-8")

        result = DocumentService.ingest_document(raw_bytes, "briefing.txt")

        self.assertEqual(result["file_type"], "TXT")
        self.assertIn("Revenue increased by 15%", result["full_text"])
        self.assertGreater(result["word_count"], 0)
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(result["character_count"], len(sample_text))
        self.assertEqual(result["preview"], result["full_text"])
        self.assertTrue(result["has_extractable_text"])

    def test_document_service_scanned_or_blank_detection(self):
        """Verify DocumentService flags documents with no extractable text."""
        blank_bytes = b"   \n\n   "
        result = DocumentService.ingest_document(blank_bytes, "blank_scanned.txt")
        self.assertFalse(result["has_extractable_text"])

    def test_document_service_empty_input_raises_error(self):
        """Verify DocumentService raises ValueError on empty file bytes."""
        with self.assertRaises(ValueError) as ctx:
            DocumentService.ingest_document(b"", "empty.txt")
        self.assertIn("empty", str(ctx.exception).lower())

    @patch("backend.services.document_service.generate_document_summary")
    def test_document_service_summarize(self, mock_summary):
        """Verify DocumentService orchestrates summarization and normalizes response."""
        mock_summary.return_value = "- Highlight 1: Revenue up 15%\n- Highlight 2: Margins healthy"

        res = DocumentService.summarize_document(
            text="Sample document body for summarization.",
            summary_type="executive",
            provider="Google Gemini"
        )

        mock_summary.assert_called_once()
        self.assertEqual(res["result"], "- Highlight 1: Revenue up 15%\n- Highlight 2: Margins healthy")
        self.assertEqual(res["summary_type"], "executive")
        self.assertIn("provider_used", res)
        self.assertIn("latency_ms", res)

    @patch("backend.services.document_service.ask_document_question")
    def test_document_service_ask(self, mock_ask):
        """Verify DocumentService orchestrates Ask-the-Document Q&A."""
        mock_ask.return_value = "The research expenditure was $3.4M."

        res = DocumentService.ask_question(
            text="Financial context with $3.4M R&D.",
            question="What was R&D spend?",
            provider="Google Gemini"
        )

        mock_ask.assert_called_once()
        self.assertEqual(res["result"], "The research expenditure was $3.4M.")
        self.assertEqual(res["summary_type"], "qa")

    # ---------------------------------------------------------------------------
    # 2. VisionService Tests
    # ---------------------------------------------------------------------------
    def test_vision_service_extract_metadata(self):
        """Verify VisionService extracts image dimensions and dominant colors."""
        # Create small in-memory 100x100 RGB image
        img = Image.new("RGB", (100, 100), color=(198, 93, 59))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        meta = VisionService.extract_metadata(raw_bytes, "test_chart.png")

        self.assertEqual(meta["filename"], "test_chart.png")
        self.assertIn(meta["format"], ["PNG", "JPEG"])
        self.assertIn("100", meta["dimensions"])
        self.assertEqual(meta["mode"], "RGB")
        self.assertGreater(len(meta["dominant_colors"]), 0)
        self.assertTrue(meta["dominant_colors"][0]["hex"].startswith("#"))

    @patch("backend.services.vision_service.analyze_image_with_llm")
    def test_vision_service_analyze_data_uri(self, mock_analyze):
        """Verify VisionService accepts data:image/... Data URIs."""
        mock_analyze.return_value = "Chart indicates steady growth from Q1 to Q4."

        res = VisionService.analyze_image(
            image_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            task_type="ocr",
            provider="Google Gemini"
        )

        mock_analyze.assert_called_once()
        self.assertEqual(res["result"], "Chart indicates steady growth from Q1 to Q4.")
        self.assertEqual(res["task_type"], "ocr")

    @patch("backend.services.vision_service.analyze_image_with_llm")
    def test_vision_service_analyze_raw_base64(self, mock_analyze):
        """Verify VisionService accepts raw base64 strings without data:image prefix."""
        mock_analyze.return_value = "Visual description of raw base64 image."

        res = VisionService.analyze_image(
            image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            task_type="describe",
            provider="Google Gemini"
        )

        mock_analyze.assert_called_once()
        self.assertEqual(res["result"], "Visual description of raw base64 image.")
        self.assertEqual(res["task_type"], "describe")

    def test_vision_service_analyze_invalid_payload_raises_value_error(self):
        """Verify VisionService raises ValueError on malformed or non-image payloads without unhandled crashes."""
        for bad_input in ["malformed_base64!!!", "bm90IGFuIGltYWdl"]:
            with self.subTest(bad_input=bad_input):
                with self.assertRaises(ValueError) as ctx:
                    VisionService.analyze_image(
                        image_base64=bad_input,
                        task_type="ocr",
                        provider="Offline Heuristics"
                    )
                self.assertIn("image", str(ctx.exception).lower())

    # ---------------------------------------------------------------------------
    # 3. DataService Tests
    # ---------------------------------------------------------------------------
    def test_data_service_profile(self):
        """Verify DataService profiles CSV and computes Data Health Card."""
        csv_bytes = b"id,name,amount,active\n1,Alpha,100.5,True\n2,Beta,200.0,False\n3,Gamma,300.2,True\n"

        health = DataService.profile_data(csv_bytes, "sales.csv")

        self.assertEqual(health["filename"], "sales.csv")
        self.assertEqual(health["total_rows"], 3)
        self.assertEqual(health["total_cols"], 4)
        self.assertIn("amount", health["numeric_columns"])
        self.assertEqual(len(health["columns_summary"]), 4)

    def test_data_service_correlation(self):
        """Verify DataService computes Pearson correlation using authoritative pipeline."""
        csv_bytes = b"x,y,z\n1,2,10\n2,4,20\n3,6,30\n4,8,40\n"

        corr = DataService.compute_correlation(csv_bytes, "metrics.csv")

        self.assertEqual(corr["columns"], ["x", "y", "z"])
        self.assertEqual(len(corr["matrix"]), 3)
        self.assertEqual(corr["matrix"][0][1], 1.0)  # Perfect linear correlation between x and y

    @patch("backend.services.data_service.generate_data_insights")
    def test_data_service_insights(self, mock_insights):
        """Verify DataService orchestrates automated EDA or query insights."""
        mock_insights.return_value = "### Key Patterns\nPositive linear trend detected between x and y."

        res = DataService.generate_insights(
            dataset_csv="x,y\n1,2\n2,4\n3,6\n",
            user_query="Describe trends",
            provider="Google Gemini"
        )

        mock_insights.assert_called_once()
        self.assertIn("Positive linear trend", res["result"])
        self.assertEqual(res["query_type"], "user_query")

    # ---------------------------------------------------------------------------
    # 4. ChatService Tests
    # ---------------------------------------------------------------------------
    def test_chat_service_list_providers(self):
        """Verify ChatService returns provider catalog."""
        catalog = ChatService.list_providers()

        self.assertIn("providers", catalog)
        provider_names = [p["name"] for p in catalog["providers"]]
        self.assertIn("Google Gemini", provider_names)
        self.assertIn("OpenAI", provider_names)
        self.assertIn("Groq", provider_names)

    @patch("backend.services.chat_service.query_llm")
    def test_chat_service_execute_query(self, mock_query):
        """Verify ChatService delegates to LLM Router."""
        mock_query.return_value = "Synthesized diagnostic response."

        res = ChatService.execute_query(
            prompt="Synthesize quarterly telemetry",
            provider="Google Gemini"
        )

        mock_query.assert_called_once()
        self.assertEqual(res["response"], "Synthesized diagnostic response.")
        self.assertIn("latency_ms", res)
        self.assertIn("primary_provider", res)


if __name__ == "__main__":
    unittest.main()
