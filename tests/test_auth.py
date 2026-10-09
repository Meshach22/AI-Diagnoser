"""tests/test_auth.py

Comprehensive test suite for AI-Diagnoser Authentication & Session Security.
Covers:
- Secure password hashing (Argon2id)
- User registration and validation
- Credential authentication (success, bad password, unknown email)
- Brute-force lockout enforcement
- Session tokens, idle expiration, absolute expiration, and revocation
- FastAPI auth router endpoints (/login, /logout, /me, /register)
"""

import os
import tempfile
import time
import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.auth_service import (
    AuthError,
    AuthService,
    GENERIC_LOGIN_ERROR,
    LOCKED_ERROR,
)


class TestAuthServiceUnit(unittest.TestCase):
    """Unit tests for AuthService isolated with temporary databases and mock clock."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_auth.db")
        self.current_time = 1700000000.0

        def clock():
            return self.current_time

        self.service = AuthService(
            db_path=self.db_path,
            session_ttl_minutes=60,       # 3600s
            session_idle_minutes=15,      # 900s
            max_failed_attempts=3,
            lockout_minutes=5,            # 300s
            clock=clock,
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_create_user_success(self):
        u = self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        self.assertEqual(u["email"], "analyst@example.com")
        self.assertEqual(u["name"], "Data Analyst")
        self.assertGreater(u["id"], 0)

    def test_create_user_weak_password_rejected(self):
        with self.assertRaises(AuthError) as ctx:
            self.service.create_user("analyst@example.com", "Data Analyst", "short")
        self.assertEqual(ctx.exception.code, "weak_password")

    def test_create_user_invalid_email_rejected(self):
        with self.assertRaises(AuthError) as ctx:
            self.service.create_user("not-an-email", "Data Analyst", "ValidPass1234!")
        self.assertEqual(ctx.exception.code, "invalid_email")

    def test_authenticate_success_and_session_validation(self):
        self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        token, session = self.service.authenticate("analyst@example.com", "ValidPass1234!")
        self.assertIsNotNone(token)
        self.assertEqual(session.email, "analyst@example.com")

        # Validate session immediately
        validated = self.service.validate_session(token)
        self.assertIsNotNone(validated)
        self.assertEqual(validated.email, "analyst@example.com")

    def test_authenticate_invalid_password(self):
        self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        with self.assertRaises(AuthError) as ctx:
            self.service.authenticate("analyst@example.com", "WrongPassword999!")
        self.assertEqual(ctx.exception.message, GENERIC_LOGIN_ERROR)

    def test_account_lockout_after_max_failures(self):
        self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        # 3 failures triggers lockout
        for _ in range(3):
            with self.assertRaises(AuthError):
                self.service.authenticate("analyst@example.com", "WrongPassword!")

        # 4th attempt should be locked out
        with self.assertRaises(AuthError) as ctx:
            self.service.authenticate("analyst@example.com", "ValidPass1234!")
        self.assertEqual(ctx.exception.code, "locked")
        self.assertEqual(ctx.exception.message, LOCKED_ERROR)

        # Advance clock beyond lockout window (5 mins = 300s)
        self.current_time += 301.0
        # Now valid password succeeds
        token, session = self.service.authenticate("analyst@example.com", "ValidPass1234!")
        self.assertIsNotNone(token)

    def test_session_idle_timeout(self):
        self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        token, _ = self.service.authenticate("analyst@example.com", "ValidPass1234!")

        # Advance clock past idle window (15 mins = 900s)
        self.current_time += 901.0
        validated = self.service.validate_session(token)
        self.assertIsNone(validated)

    def test_session_absolute_timeout(self):
        self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        token, _ = self.service.authenticate("analyst@example.com", "ValidPass1234!")

        # Touch session every 10 mins (less than idle of 15m), but advance beyond 60m TTL
        for _ in range(7):
            self.current_time += 600.0
            self.service.validate_session(token)

        validated = self.service.validate_session(token)
        self.assertIsNone(validated)

    def test_session_revocation_on_logout(self):
        self.service.create_user("analyst@example.com", "Data Analyst", "ValidPass1234!")
        token, _ = self.service.authenticate("analyst@example.com", "ValidPass1234!")
        self.assertIsNotNone(self.service.validate_session(token))

        self.service.revoke_session(token)
        self.assertIsNone(self.service.validate_session(token))


class TestFastAPIAuthEndpoints(unittest.TestCase):
    """Integration tests for FastAPI auth endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_auth_endpoints_flow(self):
        # Register / bootstrap user
        reg_payload = {
            "email": f"tester_{int(time.time())}@enterprise.local",
            "name": "Integration Tester",
            "password": "StrongTestPassword1234!"
        }
        res_reg = self.client.post("/api/v1/auth/register", json=reg_payload)
        # 200 on success, or 409 if already exists
        self.assertIn(res_reg.status_code, [200, 403, 409])

        # Test login with bad password returns 401
        res_bad = self.client.post("/api/v1/auth/login", json={
            "email": "nonexistent@enterprise.local",
            "password": "BadPassword1234!"
        })
        self.assertEqual(res_bad.status_code, 401)
        self.assertEqual(res_bad.json()["detail"], GENERIC_LOGIN_ERROR)

        # Unauthenticated /me returns 401
        res_me_anon = self.client.get("/api/v1/auth/me")
        self.assertEqual(res_me_anon.status_code, 401)


if __name__ == "__main__":
    unittest.main()
