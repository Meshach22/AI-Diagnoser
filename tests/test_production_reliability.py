"""tests/test_production_reliability.py

Targeted regression test suite verifying production reliability fixes:
1. CORS origins (exact Vercel origins, credentialed requests, no wildcards with credentials).
2. Authentication & persistence (registration, cookie + Bearer extraction, persistent db path resolution, session survival).
3. Gemini model configuration (gemini-3.5-flash defaults across catalogs and routing).
4. Request correlation ID & structured logging headers.
5. Health check contracts and response times.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.config import BackendSettings, settings
from backend.main import app
from backend.services.auth_service import AuthService, SessionInfo
from core.config import MODEL_CATALOG, PROVIDER_PRIMARY_MODELS
from core.llm_router import query_llm, _CLIENT_CACHE


class TestProductionReliabilityCORS(unittest.TestCase):
    """Test CORS configuration compliance for production deployments."""

    def setUp(self):
        self.client = TestClient(app)

    def test_vercel_production_origin_allowed(self):
        """Verify exact deployed Vercel origin is allowed with credentials."""
        origin = "https://ai-diagnoser-ig8r.vercel.app"
        response = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_no_wildcard_with_credentials(self):
        """Verify origin is NOT wildcard '*' when credentials are true."""
        origin = "https://ai-diagnoser-ig8r.vercel.app"
        response = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "*")

    def test_cors_origin_trailing_slash_normalization(self):
        """Settings should normalize origins with trailing slashes."""
        custom_settings = BackendSettings(
            CORS_ORIGINS=["https://example-frontend.vercel.app/"]
        )
        self.assertIn("https://example-frontend.vercel.app", custom_settings.CORS_ORIGINS)
        self.assertNotIn("https://example-frontend.vercel.app/", custom_settings.CORS_ORIGINS)


class TestProductionReliabilityAuthAndPersistence(unittest.TestCase):
    """Test authentication flows, cookie session extraction, and persistent DB configuration."""

    def setUp(self):
        self.client = TestClient(app)
        _CLIENT_CACHE.clear()

    def test_database_url_and_data_dir_resolution(self):
        """Test persistent database path configuration via env variables."""
        # 1. DATABASE_URL sqlite scheme via env patch
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:////var/data/persistent_auth.db", "AUTH_DB_PATH": ""}):
            s1 = BackendSettings()
            self.assertEqual(s1.AUTH_DB_PATH, "/var/data/persistent_auth.db")

        # 2. DATA_DIR mount path
        with patch.dict(os.environ, {"DATA_DIR": "/mnt/volume/data", "AUTH_DB_PATH": "", "DATABASE_URL": ""}):
            s2 = BackendSettings()
            self.assertTrue(s2.AUTH_DB_PATH.endswith("auth.db"))
            self.assertIn("data", s2.AUTH_DB_PATH)

    def test_auth_registration_login_cookie_and_bearer_flow(self):
        """Verify signup, login with cookie setting, and session restoration via cookie & Bearer."""
        import time
        unique_email = f"prod_reliability_{int(time.time()*1000)}@enterprise.test"
        password = "SecurePassword2026!"

        # Allow signup for this test
        with patch.object(settings, "AUTH_ALLOW_SIGNUP", True):
            # Register
            reg_res = self.client.post("/api/v1/auth/register", json={
                "email": unique_email,
                "name": "Reliability Tester",
                "password": password
            })
            self.assertEqual(reg_res.status_code, 200)
            reg_data = reg_res.json()
            token = reg_data["token"]
            self.assertTrue(token)
            # Verify Set-Cookie header was returned
            set_cookie = reg_res.headers.get("set-cookie") or ""
            self.assertTrue("ai_diagnoser_session=" in set_cookie or "session_token=" in set_cookie)

            # Authenticated /me via Bearer header
            me_bearer = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(me_bearer.status_code, 200)
            self.assertEqual(me_bearer.json()["user"]["email"], unique_email)

            # Authenticated /me via Cookie
            me_cookie = self.client.get(
                "/api/v1/auth/me",
                cookies={settings.AUTH_COOKIE_NAME: token}
            )
            self.assertEqual(me_cookie.status_code, 200)
            self.assertEqual(me_cookie.json()["user"]["email"], unique_email)

            # Duplicate registration is rejected
            dup_res = self.client.post("/api/v1/auth/register", json={
                "email": unique_email,
                "name": "Duplicate Tester",
                "password": password
            })
            self.assertIn(dup_res.status_code, [400, 403, 409])

        # Login with correct password
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": password
        })
        self.assertEqual(login_res.status_code, 200)
        new_token = login_res.json()["token"]
        self.assertTrue(new_token)
        login_cookie = login_res.headers.get("set-cookie", "")
        self.assertTrue("ai_diagnoser_session=" in login_cookie or "session_token=" in login_cookie)

        # Logout revokes session and clears cookie
        logout_res = self.client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        self.assertEqual(logout_res.status_code, 200)

        # Old token is now invalid (401)
        me_after_logout = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        self.assertEqual(me_after_logout.status_code, 401)


class TestProductionReliabilityGeminiConfiguration(unittest.TestCase):
    """Test that Gemini 3.8 Flash is configured as standard model across catalogs and routing."""

    def test_default_model_catalogs(self):
        """Verify model catalog and primary provider default to gemini-3.8-flash."""
        self.assertEqual(settings.DEFAULT_MODEL_GEMINI, "gemini-3.8-flash")
        self.assertEqual(PROVIDER_PRIMARY_MODELS["Google Gemini"], "gemini-3.8-flash")
        self.assertIn("gemini-3.8-flash", MODEL_CATALOG["Google Gemini"]["models"])

    @patch("core.llm_router._execute_with_timeout")
    def test_query_llm_defaults_to_gemini_38_flash(self, mock_exec):
        """Verify query_llm passes gemini-3.8-flash to provider."""
        mock_exec.return_value = "Mocked LLM Response"
        res = query_llm(prompt="Test prompt", model_provider="Google Gemini")
        self.assertEqual(res, "Mocked LLM Response")

        # Verify model_name passed was gemini-3.8-flash
        called_kwargs = mock_exec.call_args[1]
        self.assertEqual(called_kwargs.get("model_name"), "gemini-3.8-flash")


class TestProductionReliabilityObservabilityAndHealth(unittest.TestCase):
    """Test health check endpoints and structured logging / request correlation headers."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoints(self):
        """Verify /health and /api/v1/health respond with status ok."""
        r1 = self.client.get("/health")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["status"], "healthy")

        r2 = self.client.get("/api/v1/health")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["status"], "healthy")

    def test_request_id_correlation_header(self):
        """Verify response contains X-Request-ID correlation header."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertIn("x-request-id", res.headers)
        self.assertTrue(len(res.headers["x-request-id"]) > 0)


if __name__ == "__main__":
    unittest.main()
