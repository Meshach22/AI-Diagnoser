"""tests/test_gemini_live.py

Standalone and unittest verification script for live Gemini extraction,
semantic Q&A, and executive summarization without offline heuristics fallbacks.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest

from core.llm_router import get_last_telemetry
from pipelines.document_pipeline import ask_document_question, generate_document_summary


class TestGeminiLiveIntegration(unittest.TestCase):
    """Zero-guesswork verification for live Gemini LLM pipeline."""

    def test_live_document_qa_semantic_extraction(self):
        sample_doc = "EDUCATION B.Tech, Artificial Intelligence & Data Science"
        question = "what is his qualification"

        print(f"\n[TEST QA] Asking: '{question}' on document: '{sample_doc}'", flush=True)
        qa_response = ask_document_question(sample_doc, question)
        telemetry = get_last_telemetry()

        print(f"[TEST QA Telemetry] {telemetry}", flush=True)
        print(f"[TEST QA Response]\n{qa_response}\n", flush=True)

        # Assert live LLM provider was active (not offline heuristics)
        self.assertEqual(
            telemetry.get("active_provider"),
            "Google Gemini",
            f"Expected Google Gemini provider, but got: {telemetry.get('active_provider')}"
        )
        self.assertIsNone(
            telemetry.get("failover_badge"),
            f"Expected no failover badge, but got: {telemetry.get('failover_badge')}"
        )

        # Assert no offline fallback banners
        self.assertNotIn("No Direct Match Found", qa_response)
        self.assertNotIn("The provided document does not appear to discuss", qa_response)
        self.assertNotIn("Offline Heuristics Engine", qa_response)
        self.assertNotIn("> *Note: Summary extracted directly from document text.*", qa_response)

        # Assert response identifies the qualification
        self.assertIn("B.Tech", qa_response)
        self.assertIn("Artificial Intelligence", qa_response)
        self.assertTrue(
            "B.Tech, Artificial Intelligence & Data Science" in qa_response
            or ("B.Tech" in qa_response and "Data Science" in qa_response),
            "Expected qualification 'B.Tech, Artificial Intelligence & Data Science' to be identified"
        )

    def test_live_document_summary_synthesis(self):
        sample_doc = "EDUCATION B.Tech, Artificial Intelligence & Data Science"

        print(f"\n[TEST SUMMARY] Generating summary for: '{sample_doc}'", flush=True)
        summary_response = generate_document_summary(sample_doc)
        telemetry = get_last_telemetry()

        print(f"[TEST Summary Telemetry] {telemetry}", flush=True)
        print(f"[TEST Summary Response]\n{summary_response}\n", flush=True)

        # Assert live LLM was active
        self.assertEqual(
            telemetry.get("active_provider"),
            "Google Gemini",
            f"Expected Google Gemini provider, but got: {telemetry.get('active_provider')}"
        )

        # Assert not offline extractive fallback
        self.assertNotIn("> *Note: Summary extracted directly from document text.*", summary_response)
        self.assertNotIn("Offline Heuristics", summary_response)

        # Assert summary is synthesized
        self.assertIn("Executive Summary", summary_response)
        self.assertTrue("B.Tech" in summary_response or "Bachelor" in summary_response)


if __name__ == "__main__":
    unittest.main()
