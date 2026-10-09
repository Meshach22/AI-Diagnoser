"""tests/test_fastapi_backend.py

Automated integration tests for AI-Diagnoser FastAPI Backend.
Tests Core AI Services, LLM Router, and n8n Automation Engine with authenticated sessions.
"""

import io
import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import get_auth_service


class TestFastAPIBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        auth = get_auth_service()
        email = "backend_tester@enterprise.local"
        password = "BackendTesterPass1234!"
        try:
            auth.create_user(email, "Backend Tester", password, role="admin", is_admin=True)
        except Exception:
            pass
        token, _ = auth.authenticate(email, password)
        cls.headers = {"Authorization": f"Bearer {token}"}

    def test_health_check(self):
        """Verify backend health endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("version", data)

    def test_root_architecture_index(self):
        """Verify root index returns complete architecture catalog."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["app"], "AI-Diagnoser")
        self.assertIn("architecture", data)
        self.assertIn("core_ai_services", data["architecture"])
        self.assertIn("llm_router", data["architecture"])
        self.assertIn("n8n_automation", data["architecture"])

    def test_router_providers_catalog(self):
        """Verify LLM Router lists Google Gemini, OpenAI, Groq."""
        response = self.client.get("/api/v1/router/providers", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        provider_names = [p["name"] for p in data["providers"]]
        self.assertIn("Google Gemini", provider_names)
        self.assertIn("OpenAI", provider_names)
        self.assertIn("Groq", provider_names)

    def test_document_summarization(self):
        """Verify document summarization endpoint."""
        sample_text = (
            "Q3 Financial Performance Report: The company reported quarterly revenues of $12.4M, "
            "representing a 22% increase year-over-year. Operating expenses were reduced by 8% "
            "following automation across data pipelines. Net margins expanded to 18.5%."
        )
        response = self.client.post("/api/v1/documents/summarize", headers=self.headers, json={
            "text": sample_text,
            "summary_type": "executive",
            "provider": "Offline Heuristics"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertTrue(len(data["result"]) > 0)

    def test_data_profiling(self):
        """Verify tabular data health card endpoint."""
        csv_content = (
            "employee_id,department,salary,years_exp\n"
            "101,Engineering,125000,5\n"
            "102,Product,115000,4\n"
            "103,Marketing,95000,3\n"
            "104,Engineering,140000,7\n"
        )
        files = {"file": ("employees.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = self.client.post("/api/v1/data/profile", headers=self.headers, files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_rows"], 4)
        self.assertEqual(data["total_cols"], 4)
        self.assertIn("salary", data["numeric_columns"])

    def test_n8n_webhook_ingestion(self):
        """Verify n8n webhook receiver executes diagnostic event."""
        payload = {
            "event": "document.diagnose",
            "content": "Executive memo: Strategic cloud migration roadmap is 95% complete with zero security violations.",
            "provider": "Offline Heuristics"
        }
        response = self.client.post("/api/v1/n8n/webhook", headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("diagnosis", data)

    def test_n8n_report_generation(self):
        """Verify n8n diagnostic report cataloging."""
        payload = {
            "title": "Quarterly Quality Audit",
            "content": "All operational metrics satisfied service level agreements.",
            "report_type": "markdown"
        }
        response = self.client.post("/api/v1/n8n/reports/generate", headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["report_id"].startswith("REP-"))
        self.assertEqual(data["title"], "Quarterly Quality Audit")

    def test_n8n_slack_dispatch(self):
        """Verify Slack Block Kit alert formatting and dispatch."""
        payload = {
            "channel": "#alerts",
            "title": "Data Spill Warning",
            "message": "Elevated null rates detected in staging table.",
            "severity": "warning",
            "metrics": {"NullRate": "14.2%", "Threshold": "5%"}
        }
        response = self.client.post("/api/v1/n8n/dispatch/slack", headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["channel"], "#alerts")
        self.assertIn("delivered_via", data)

    def test_n8n_email_dispatch(self):
        """Verify Email notification dispatch."""
        payload = {
            "to_email": "ops-lead@enterprise.local",
            "subject": "System Health Clearance",
            "body": "Daily diagnostics cleared all validation benchmarks."
        }
        response = self.client.post("/api/v1/n8n/dispatch/email", headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recipient"], "ops-lead@enterprise.local")

    def test_n8n_schedules_list(self):
        """Verify scheduled jobs listing and trigger."""
        response = self.client.get("/api/v1/n8n/schedules", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        jobs = response.json()
        self.assertTrue(len(jobs) >= 3)
        job_ids = [j["job_id"] for j in jobs]
        self.assertIn("job_daily_data_audit", job_ids)

        # Trigger job (Admin required)
        trigger_resp = self.client.post("/api/v1/n8n/schedules/trigger", headers=self.headers, json={
            "job_id": "job_daily_data_audit",
            "provider": "Offline Heuristics"
        })
        self.assertEqual(trigger_resp.status_code, 200)
        self.assertEqual(trigger_resp.json()["status"], "success")

    def test_n8n_workflows_catalog(self):
        """Verify n8n downloadable workflow blueprints listing."""
        response = self.client.get("/api/v1/n8n/workflows", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        workflows = response.json()
        self.assertTrue(len(workflows) >= 3)
        filenames = [w["filename"] for w in workflows]
        self.assertIn("ai_diagnoser_webhook_pipeline.json", filenames)

    def test_n8n_vision_webhook_json_body(self):
        """Verify vision webhook accepts base64 payload in POST JSON body."""
        b64_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = self.client.post("/api/v1/n8n/webhook/vision", headers=self.headers, json={
            "image_base64": b64_pixel,
            "provider": "Offline Heuristics"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["event"], "vision.diagnose")

    def test_n8n_simulation_labeling(self):
        """Verify unconfigured Slack and Email dispatches are labeled as SIMULATION."""
        resp_slack = self.client.post("/api/v1/n8n/dispatch/slack", headers=self.headers, json={
            "channel": "#ops",
            "title": "Simulation Test",
            "message": "Testing labeling clarity",
            "severity": "info"
        })
        self.assertEqual(resp_slack.status_code, 200)
        self.assertTrue(
            "SIMULATION" in resp_slack.json()["delivered_via"] or "NOT CONFIGURED" in resp_slack.json()["delivered_via"]
        )

        resp_email = self.client.post("/api/v1/n8n/dispatch/email", headers=self.headers, json={
            "to_email": "test@enterprise.local",
            "subject": "Test",
            "body": "Body"
        })
        self.assertEqual(resp_email.status_code, 200)
        self.assertTrue(
            "SIMULATION" in resp_email.json()["delivered_via"] or "NOT CONFIGURED" in resp_email.json()["delivered_via"]
        )

    def test_correlation_matrix_authoritative(self):
        """Verify Pearson correlation endpoint computes authoritative matrix."""
        csv_content = (
            "feature_a,feature_b,feature_c\n"
            "10,20,30\n"
            "20,40,60\n"
            "30,60,90\n"
        )
        files = {"file": ("correlations.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = self.client.post("/api/v1/data/correlation", headers=self.headers, files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["columns"], ["feature_a", "feature_b", "feature_c"])
        self.assertEqual(len(data["matrix"]), 3)
        self.assertEqual(round(data["matrix"][0][1], 2), 1.0)

    def test_vision_analyze_data_uri(self):
        """Verify /api/v1/vision/analyze accepts data:image/... Data URIs."""
        b64_pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = self.client.post("/api/v1/vision/analyze", headers=self.headers, json={
            "image_base64": b64_pixel,
            "task_type": "describe",
            "provider": "Offline Heuristics"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["task_type"], "describe")

    def test_vision_analyze_raw_base64(self):
        """Verify /api/v1/vision/analyze accepts raw base64 strings without data:image prefix."""
        raw_b64_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = self.client.post("/api/v1/vision/analyze", headers=self.headers, json={
            "image_base64": raw_b64_pixel,
            "task_type": "describe",
            "provider": "Offline Heuristics"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        self.assertEqual(data["task_type"], "describe")

    def test_vision_analyze_invalid_payload(self):
        """Verify /api/v1/vision/analyze safely returns HTTP 400 on malformed payloads."""
        resp_malformed = self.client.post("/api/v1/vision/analyze", headers=self.headers, json={
            "image_base64": "invalid_base64_payload!!!",
            "task_type": "describe",
            "provider": "Offline Heuristics"
        })
        self.assertEqual(resp_malformed.status_code, 400)
        self.assertIn("detail", resp_malformed.json())

        import base64
        text_b64 = base64.b64encode(b"This is purely plain text, not image bytes.").decode("utf-8")
        resp_non_image = self.client.post("/api/v1/vision/analyze", headers=self.headers, json={
            "image_base64": text_b64,
            "task_type": "describe",
            "provider": "Offline Heuristics"
        })
        self.assertEqual(resp_non_image.status_code, 400)
        self.assertIn("detail", resp_non_image.json())


if __name__ == "__main__":
    unittest.main()
