"""tests/test_security_enforcement.py

Comprehensive security enforcement test suite for AI-Diagnoser:
1. Missing, invalid, expired, and revoked sessions
2. Authentication enforcement on every protected endpoint
3. Intentionally public endpoints (health, root, login, status)
4. Valid authenticated requests
5. Registration privilege escalation prevention
6. Administrative endpoint role checks (HTTP 403 vs 200)
7. Report ownership and strict cross-user data isolation
8. Explicit CORS allowlist enforcement
9. Database account and report persistence across service restarts
"""

import io
import os
import secrets
import tempfile
import time
import unittest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.services.auth_service import AuthService, get_auth_service


class TestSecurityEnforcement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_service = get_auth_service()

        # Seed two distinct users for isolation tests
        cls.user1_email = f"user1_{secrets.token_hex(4)}@enterprise.local"
        cls.user1_pwd = "SecurePassword1234!"
        cls.user1_data = cls.auth_service.create_user(cls.user1_email, "User One", cls.user1_pwd, role="user", is_admin=False)
        cls.user1_token, cls.user1_info = cls.auth_service.authenticate(cls.user1_email, cls.user1_pwd)
        cls.user1_headers = {"Authorization": f"Bearer {cls.user1_token}"}

        cls.user2_email = f"user2_{secrets.token_hex(4)}@enterprise.local"
        cls.user2_pwd = "SecurePassword1234!"
        cls.user2_data = cls.auth_service.create_user(cls.user2_email, "User Two", cls.user2_pwd, role="user", is_admin=False)
        cls.user2_token, cls.user2_info = cls.auth_service.authenticate(cls.user2_email, cls.user2_pwd)
        cls.user2_headers = {"Authorization": f"Bearer {cls.user2_token}"}

        # Seed an administrative user
        cls.admin_email = f"admin_{secrets.token_hex(4)}@enterprise.local"
        cls.admin_pwd = "AdminSecurePass1234!"
        cls.admin_data = cls.auth_service.create_user(cls.admin_email, "Admin User", cls.admin_pwd, role="admin", is_admin=True)
        cls.admin_token, cls.admin_info = cls.auth_service.authenticate(cls.admin_email, cls.admin_pwd)
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}

    # ---------------------------------------------------------------------------
    # 1. Protected Endpoints: Missing Session Must Return 401
    # ---------------------------------------------------------------------------
    def test_missing_session_rejected_on_all_core_endpoints(self):
        """Verify anonymous requests to all protected routes receive HTTP 401."""
        endpoints = [
            ("GET", "/api/v1/auth/me", None, None),
            ("GET", "/api/v1/router/providers", None, None),
            ("POST", "/api/v1/router/query", {"prompt": "test"}, None),
            ("GET", "/api/v1/router/telemetry", None, None),
            ("POST", "/api/v1/documents/upload", None, {"file": ("test.txt", io.BytesIO(b"data"), "text/plain")}),
            ("POST", "/api/v1/documents/parse", None, {"file": ("test.txt", io.BytesIO(b"data"), "text/plain")}),
            ("POST", "/api/v1/documents/summarize", {"text": "sample text"}, None),
            ("POST", "/api/v1/documents/ask", {"text": "sample text", "question": "what is this?"}, None),
            ("POST", "/api/v1/vision/metadata", None, {"file": ("test.png", io.BytesIO(b"data"), "image/png")}),
            ("POST", "/api/v1/vision/analyze", {"image_base64": "AAAA"}, None),
            ("POST", "/api/v1/data/profile", None, {"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")}),
            ("POST", "/api/v1/data/insights", {"dataset_csv": "a,b\n1,2"}, None),
            ("POST", "/api/v1/data/correlation", None, {"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")}),
            ("POST", "/api/v1/n8n/webhook", {"event": "test"}, None),
            ("POST", "/api/v1/n8n/webhook/document", {"content": "test"}, None),
            ("POST", "/api/v1/n8n/webhook/vision", {"image_base64": "AAAA"}, None),
            ("POST", "/api/v1/n8n/webhook/data", {"csv_content": "a,b\n1,2"}, None),
            ("POST", "/api/v1/n8n/reports/generate", {"title": "T", "content": "C"}, None),
            ("GET", "/api/v1/n8n/reports", None, None),
            ("GET", "/api/v1/n8n/reports/REP-UNKNOWN", None, None),
            ("DELETE", "/api/v1/n8n/reports/REP-UNKNOWN", None, None),
            ("POST", "/api/v1/n8n/dispatch/email", {"to_email": "a@b.com", "subject": "S", "body": "B"}, None),
            ("POST", "/api/v1/n8n/dispatch/slack", {"channel": "#general", "title": "T", "message": "M"}, None),
            ("GET", "/api/v1/n8n/schedules", None, None),
            ("POST", "/api/v1/n8n/schedules/trigger", {"job_id": "job_daily_data_audit"}, None),
            ("GET", "/api/v1/n8n/workflows", None, None),
            ("GET", "/api/v1/n8n/workflows/ai_diagnoser_webhook_pipeline.json", None, None),
        ]

        for method, url, json_body, files in endpoints:
            with self.subTest(endpoint=f"{method} {url}"):
                if method == "GET":
                    resp = self.client.get(url)
                elif method == "POST":
                    resp = self.client.post(url, json=json_body, files=files)
                elif method == "DELETE":
                    resp = self.client.delete(url)
                self.assertEqual(
                    resp.status_code,
                    401,
                    f"Expected 401 Unauthorized for anonymous {method} {url}, got {resp.status_code}: {resp.text}"
                )

    # ---------------------------------------------------------------------------
    # 2. Intentionally Public Endpoints Remain Accessible
    # ---------------------------------------------------------------------------
    def test_intentionally_public_endpoints(self):
        """Verify public endpoints respond correctly without auth headers."""
        public_endpoints = [
            ("GET", "/"),
            ("GET", "/health"),
            ("GET", "/docs"),
            ("GET", "/openapi.json"),
            ("GET", "/api/v1/auth/status"),
            ("POST", "/api/v1/auth/logout"),
        ]
        for method, url in public_endpoints:
            with self.subTest(public_endpoint=f"{method} {url}"):
                if method == "GET":
                    resp = self.client.get(url)
                else:
                    resp = self.client.post(url)
                self.assertIn(
                    resp.status_code,
                    [200, 307],
                    f"Public endpoint {method} {url} returned {resp.status_code}"
                )

        # Login endpoint responds with 401 when given invalid credentials (not missing token)
        login_resp = self.client.post("/api/v1/auth/login", json={"email": "nobody@nowhere.com", "password": "wrong"})
        self.assertEqual(login_resp.status_code, 401)
        self.assertEqual(login_resp.json()["detail"], "Invalid email or password.")

    # ---------------------------------------------------------------------------
    # 3. Invalid, Expired, and Revoked Session Handling
    # ---------------------------------------------------------------------------
    def test_invalid_token_rejected(self):
        """Verify malformed and non-existent tokens are rejected with 401."""
        bad_headers = {"Authorization": "Bearer invalid_secret_token_12345"}
        resp = self.client.get("/api/v1/auth/me", headers=bad_headers)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("expired or invalid", resp.json()["detail"].lower())

    def test_revoked_session_rejected_after_logout(self):
        """Verify session token is invalidated immediately upon logout."""
        # Create dedicated session
        temp_email = f"temp_{secrets.token_hex(4)}@enterprise.local"
        self.auth_service.create_user(temp_email, "Temp User", "TempPassword1234!")
        token, _ = self.auth_service.authenticate(temp_email, "TempPassword1234!")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Valid before logout
        resp1 = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(resp1.status_code, 200)

        # 2. Revoke session via logout
        logout_resp = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(logout_resp.status_code, 200)

        # 3. Reject with 401 after logout
        resp2 = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(resp2.status_code, 401)

    def test_expired_session_handling(self):
        """Verify sessions past idle or absolute expiration are rejected."""
        mock_now = [1000000.0]

        service = AuthService(
            db_path=settings.AUTH_DB_PATH,
            session_ttl_minutes=10,
            session_idle_minutes=2,
            clock=lambda: mock_now[0],
        )
        test_email = f"expire_{secrets.token_hex(4)}@enterprise.local"
        service.create_user(test_email, "Expire Test", "ExpirePassword1234!")
        token, _ = service.authenticate(test_email, "ExpirePassword1234!")

        # Valid initially
        self.assertIsNotNone(service.validate_session(token))

        # Advance past idle timeout (3 minutes > 2 minutes)
        mock_now[0] += 180.0
        self.assertIsNone(service.validate_session(token))

    # ---------------------------------------------------------------------------
    # 4. Valid Authenticated Requests
    # ---------------------------------------------------------------------------
    def test_valid_authenticated_requests_succeed(self):
        """Verify valid authenticated requests succeed on core services."""
        # /me
        me_resp = self.client.get("/api/v1/auth/me", headers=self.user1_headers)
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["user"]["email"], self.user1_email)

        # /router/providers
        prov_resp = self.client.get("/api/v1/router/providers", headers=self.user1_headers)
        self.assertEqual(prov_resp.status_code, 200)
        self.assertIn("providers", prov_resp.json())

        # /documents/summarize (offline heuristics)
        doc_resp = self.client.post(
            "/api/v1/documents/summarize",
            headers=self.user1_headers,
            json={"text": "Revenue increased by 15% in Q3. Operating expenses down 4%.", "provider": "Offline Heuristics"},
        )
        self.assertEqual(doc_resp.status_code, 200)
        self.assertIn("result", doc_resp.json())

    # ---------------------------------------------------------------------------
    # 5. Registration Privilege Escalation Prevention
    # ---------------------------------------------------------------------------
    def test_registration_privilege_escalation_impossible(self):
        """Verify attempting to inject role=admin or is_admin=true during registration is rejected or sanitized."""
        # Test 1: Extra fields rejected by schema validation
        payload_with_injection = {
            "email": f"hacker_{secrets.token_hex(4)}@enterprise.local",
            "name": "Hacker",
            "password": "HackerPassword1234!",
            "role": "admin",
            "is_admin": True,
        }
        resp = self.client.post("/api/v1/auth/register", json=payload_with_injection)
        self.assertEqual(resp.status_code, 422, "Extra administrative fields must be rejected with 422")

        # Test 2: Standard registration always creates regular non-admin user
        reg_payload = {
            "email": f"standard_{secrets.token_hex(4)}@enterprise.local",
            "name": "Standard User",
            "password": "StandardPassword1234!",
        }
        reg_resp = self.client.post("/api/v1/auth/register", json=reg_payload)
        if reg_resp.status_code == 200:
            user = reg_resp.json()["user"]
            self.assertEqual(user["role"], "user")
            self.assertFalse(user["is_admin"])

    # ---------------------------------------------------------------------------
    # 6. Administrative Role Authorization (HTTP 403 vs 200)
    # ---------------------------------------------------------------------------
    def test_administrative_endpoint_authorization(self):
        """Verify standard user receives 403 Forbidden on admin endpoints, while admin succeeds."""
        # 1. Standard user calling /telemetry -> 403 Forbidden
        user_telemetry = self.client.get("/api/v1/router/telemetry", headers=self.user1_headers)
        self.assertEqual(user_telemetry.status_code, 403)
        self.assertIn("administrative privileges required", user_telemetry.json()["detail"].lower())

        # 2. Standard user calling /schedules/trigger -> 403 Forbidden
        user_trigger = self.client.post(
            "/api/v1/n8n/schedules/trigger",
            headers=self.user1_headers,
            json={"job_id": "job_daily_data_audit"},
        )
        self.assertEqual(user_trigger.status_code, 403)

        # 3. Admin user calling /telemetry -> 200 OK
        admin_telemetry = self.client.get("/api/v1/router/telemetry", headers=self.admin_headers)
        self.assertEqual(admin_telemetry.status_code, 200)

        # 4. Admin user calling /schedules/trigger -> 200 OK
        admin_trigger = self.client.post(
            "/api/v1/n8n/schedules/trigger",
            headers=self.admin_headers,
            json={"job_id": "job_daily_data_audit", "provider": "Offline Heuristics"},
        )
        self.assertEqual(admin_trigger.status_code, 200)

    # ---------------------------------------------------------------------------
    # 7. Report Ownership and Cross-User Data Isolation
    # ---------------------------------------------------------------------------
    def test_report_ownership_and_cross_user_isolation(self):
        """Verify reports are strictly isolated by owner and cannot be accessed across accounts."""
        # User 1 generates a report
        gen_resp = self.client.post(
            "/api/v1/n8n/reports/generate",
            headers=self.user1_headers,
            json={"title": "Confidential User 1 Audit", "content": "Sensitive financial report data."},
        )
        self.assertEqual(gen_resp.status_code, 200)
        report_id = gen_resp.json()["report_id"]

        # User 1 can retrieve own report
        u1_get = self.client.get(f"/api/v1/n8n/reports/{report_id}", headers=self.user1_headers)
        self.assertEqual(u1_get.status_code, 200)
        self.assertEqual(u1_get.json()["title"], "Confidential User 1 Audit")

        # User 1 can see report in list
        u1_list = self.client.get("/api/v1/n8n/reports", headers=self.user1_headers)
        self.assertEqual(u1_list.status_code, 200)
        u1_ids = [r["report_id"] for r in u1_list.json()]
        self.assertIn(report_id, u1_ids)

        # User 2 attempts to retrieve User 1's report -> 404 (non-disclosing)
        u2_get = self.client.get(f"/api/v1/n8n/reports/{report_id}", headers=self.user2_headers)
        self.assertEqual(u2_get.status_code, 404, "Cross-user report access must return 404")

        # User 2 cannot see User 1's report in their list
        u2_list = self.client.get("/api/v1/n8n/reports", headers=self.user2_headers)
        self.assertEqual(u2_list.status_code, 200)
        u2_ids = [r["report_id"] for r in u2_list.json()]
        self.assertNotIn(report_id, u2_ids)

        # User 2 attempts to delete User 1's report -> 404
        u2_del = self.client.delete(f"/api/v1/n8n/reports/{report_id}", headers=self.user2_headers)
        self.assertEqual(u2_del.status_code, 404)

        # User 1 deletes own report -> 200
        u1_del = self.client.delete(f"/api/v1/n8n/reports/{report_id}", headers=self.user1_headers)
        self.assertEqual(u1_del.status_code, 200)

        # Report is now gone
        u1_get_after = self.client.get(f"/api/v1/n8n/reports/{report_id}", headers=self.user1_headers)
        self.assertEqual(u1_get_after.status_code, 404)

    # ---------------------------------------------------------------------------
    # 8. CORS Allowlist Verification
    # ---------------------------------------------------------------------------
    def test_cors_allowed_and_disallowed_origins(self):
        """Verify allowed origins receive CORS headers and untrusted origins do not."""
        # 1. Allowed origin: Streamlit frontend (http://localhost:8501)
        resp_allowed = self.client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(resp_allowed.headers.get("access-control-allow-origin"), "http://localhost:8501")
        self.assertEqual(resp_allowed.headers.get("access-control-allow-credentials"), "true")

        # 2. Disallowed origin: untrusted site
        resp_disallowed = self.client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "http://malicious-attacker-domain.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(resp_disallowed.headers.get("access-control-allow-origin"), "http://malicious-attacker-domain.com")

    # ---------------------------------------------------------------------------
    # 9. Persistent Storage Across Service / Container Restarts
    # ---------------------------------------------------------------------------
    def test_database_persistence_across_service_recreation(self):
        """Verify user records and persistent reports survive service re-initialization."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db_path = tf.name

        try:
            # Phase 1: First container/service instance writes data
            service_v1 = AuthService(db_path=temp_db_path)
            persist_email = f"persist_{secrets.token_hex(4)}@enterprise.local"
            service_v1.create_user(persist_email, "Persistent User", "PersistPass1234!", role="user")
            user_rec = [u for u in service_v1.list_users() if u["email"] == persist_email][0]

            report_entry = service_v1.save_report(
                user_id=user_rec["id"],
                title="Preserved Audit Report",
                content="This content must survive restarts.",
            )
            report_id = report_entry["report_id"]

            # Phase 2: Terminate instance v1, instantiate fresh instance v2 pointing to same DB
            del service_v1
            service_v2 = AuthService(db_path=temp_db_path)

            # Phase 3: Verify user authenticates on fresh instance
            token, info = service_v2.authenticate(persist_email, "PersistPass1234!")
            self.assertEqual(info.email, persist_email)

            # Phase 4: Verify report persists on fresh instance
            recovered_rep = service_v2.get_report(report_id, user_id=user_rec["id"])
            self.assertIsNotNone(recovered_rep)
            self.assertEqual(recovered_rep["title"], "Preserved Audit Report")
            self.assertEqual(recovered_rep["content"], "This content must survive restarts.")

        finally:
            if os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
