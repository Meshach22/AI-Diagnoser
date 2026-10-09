"""core/backend_client.py

Client bridge connecting Streamlit Frontend to the authoritative FastAPI Backend.
Handles health checks, latency probes, automatic session token injection,
and strict backend-only authentication without local database fallbacks.
"""

import io
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import requests

logger = logging.getLogger("backend_client")

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class BackendClient:
    """Client for FastAPI Backend endpoints with automatic session forwarding."""

    def __init__(self, base_url: str = DEFAULT_BACKEND_URL, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = token

    def set_token(self, token: Optional[str]) -> None:
        """Update active session token used across authenticated API calls."""
        self.token = token

    def _headers(self, custom: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Inject active session Bearer token into outgoing HTTP requests."""
        headers: Dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if custom:
            headers.update(custom)
        return headers

    def check_health(self, timeout: float = 0.8) -> Tuple[bool, Optional[Dict[str, Any]], float]:
        """Check if FastAPI backend is online and probe latency in ms."""
        import time
        start = time.time()
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=timeout)
            latency_ms = round((time.time() - start) * 1000, 2)
            if resp.status_code == 200:
                return True, resp.json(), latency_ms
            return False, None, latency_ms
        except Exception:
            latency_ms = round((time.time() - start) * 1000, 2)
            return False, None, latency_ms

    def get_providers(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch provider catalog from FastAPI backend."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/router/providers",
                headers=self._headers(),
                timeout=2.0,
            )
            if resp.status_code == 200:
                return resp.json().get("providers", [])
        except Exception as e:
            logger.debug(f"FastAPI get_providers failed: {e}")
        return None

    def query_chat(
        self,
        prompt: str,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Call FastAPI LLM query endpoint."""
        payload = {
            "prompt": prompt,
            "provider": provider,
            "model_name": model_name,
            "api_key": api_key
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/router/query",
            json=payload,
            headers=self._headers(),
            timeout=45.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    # --- Document Intelligence ---
    def parse_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Call FastAPI document parse endpoint."""
        files = {"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
        resp = requests.post(
            f"{self.base_url}/api/v1/documents/parse",
            files=files,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def summarize_document(
        self,
        text: str,
        summary_type: str = "executive",
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Call FastAPI document summarization endpoint."""
        payload = {
            "text": text,
            "summary_type": summary_type,
            "provider": provider,
            "model_name": model_name,
            "api_key": api_key
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/documents/summarize",
            json=payload,
            headers=self._headers(),
            timeout=40.0,
        )
        if resp.status_code == 200:
            return resp.json().get("result", "")
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def ask_document(
        self,
        text: str,
        question: str,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Call FastAPI document Q&A endpoint."""
        payload = {
            "text": text,
            "question": question,
            "provider": provider,
            "model_name": model_name,
            "api_key": api_key
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/documents/ask",
            json=payload,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json().get("result", "")
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    # --- Vision Intelligence ---
    def analyze_vision(
        self,
        image_base64: str,
        task_type: str = "describe",
        custom_prompt: Optional[str] = None,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Call FastAPI vision analysis endpoint."""
        payload = {
            "image_base64": image_base64,
            "task_type": task_type,
            "custom_prompt": custom_prompt,
            "provider": provider,
            "model_name": model_name,
            "api_key": api_key
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/vision/analyze",
            json=payload,
            headers=self._headers(),
            timeout=45.0,
        )
        if resp.status_code == 200:
            return resp.json().get("result", "")
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def get_image_metadata(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Call FastAPI vision metadata extraction endpoint."""
        files = {"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
        resp = requests.post(
            f"{self.base_url}/api/v1/vision/metadata",
            files=files,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    # --- Data Analytics ---
    def profile_data(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Call FastAPI data profiling endpoint."""
        files = {"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
        resp = requests.post(
            f"{self.base_url}/api/v1/data/profile",
            files=files,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def compute_correlation(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Call FastAPI data correlation matrix endpoint."""
        files = {"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
        resp = requests.post(
            f"{self.base_url}/api/v1/data/correlation",
            files=files,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def get_data_insights(
        self,
        dataset_csv: str,
        user_query: Optional[str] = None,
        provider: str = "Google Gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Call FastAPI data insights endpoint."""
        payload = {
            "dataset_csv": dataset_csv,
            "user_query": user_query,
            "provider": provider,
            "model_name": model_name,
            "api_key": api_key
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/data/insights",
            json=payload,
            headers=self._headers(),
            timeout=40.0,
        )
        if resp.status_code == 200:
            return resp.json().get("result", "")
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    # --- n8n Automation Engine ---
    def trigger_webhook(
        self,
        event: str,
        content: Optional[str] = None,
        image_base64: Optional[str] = None,
        provider: str = "Google Gemini"
    ) -> Dict[str, Any]:
        """Trigger FastAPI n8n universal webhook."""
        payload = {
            "event": event,
            "content": content,
            "image_base64": image_base64,
            "provider": provider
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/n8n/webhook",
            json=payload,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def generate_report(
        self,
        title: str,
        content: str,
        report_type: str = "markdown",
        recipient_email: Optional[str] = None,
        slack_channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate and catalog report via FastAPI backend."""
        payload = {
            "title": title,
            "content": content,
            "report_type": report_type,
            "recipient_email": recipient_email,
            "slack_channel": slack_channel
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/n8n/reports/generate",
            json=payload,
            headers=self._headers(),
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cataloged report by ID with ownership verification."""
        resp = requests.get(
            f"{self.base_url}/api/v1/n8n/reports/{report_id}",
            headers=self._headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        return None

    def dispatch_email(
        self,
        to_email: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Dispatch email via FastAPI n8n email handler."""
        payload = {
            "to_email": to_email,
            "subject": subject,
            "body": body
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/n8n/dispatch/email",
            json=payload,
            headers=self._headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def dispatch_slack(
        self,
        channel: str,
        title: str,
        message: str,
        severity: str = "info",
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch Slack alert via FastAPI n8n Slack handler."""
        payload = {
            "channel": channel,
            "title": title,
            "message": message,
            "severity": severity,
            "metrics": metrics or {}
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/n8n/dispatch/slack",
            json=payload,
            headers=self._headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List scheduled jobs from backend."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/n8n/schedules",
                headers=self._headers(),
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"FastAPI list_schedules connection error: {e}")
        return []

    def trigger_schedule(self, job_id: str, provider: str = "Google Gemini") -> Dict[str, Any]:
        """Trigger scheduled job execution."""
        payload = {"job_id": job_id, "provider": provider}
        resp = requests.post(
            f"{self.base_url}/api/v1/n8n/schedules/trigger",
            json=payload,
            headers=self._headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Backend HTTP {resp.status_code}: {resp.text}")

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List n8n workflow blueprints."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/n8n/workflows",
                headers=self._headers(),
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"FastAPI list_workflows connection error: {e}")
        return []

    # --- Authentication (Authoritative Backend-Only Access) ---
    def login(self, email: str, password: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]], str]:
        """Call FastAPI auth login endpoint. Returns (success, token, user, message)."""
        payload = {"email": email, "password": password}
        try:
            resp = requests.post(f"{self.base_url}/api/v1/auth/login", json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                tok = data.get("token")
                self.token = tok
                return True, tok, data.get("user"), "Login successful."
            detail = "Invalid email or password."
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            return False, None, None, str(detail)
        except Exception as err:
            return False, None, None, f"Connection to backend failed: {str(err)}"

    def register(self, email: str, name: str, password: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]], str]:
        """Call FastAPI auth register endpoint. Returns (success, token, user, message)."""
        payload = {"email": email, "name": name, "password": password}
        try:
            resp = requests.post(f"{self.base_url}/api/v1/auth/register", json=payload, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                tok = data.get("token")
                self.token = tok
                return True, tok, data.get("user"), "Account created successfully."
            detail = "Registration failed."
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            return False, None, None, str(detail)
        except Exception as err:
            return False, None, None, f"Connection to backend failed: {str(err)}"

    def get_me(self, token: Optional[str] = None) -> tuple[bool, Optional[Dict[str, Any]], str]:
        """Call FastAPI auth /me endpoint to validate session. Returns (is_authenticated, user, message)."""
        tok = token or self.token
        if not tok:
            return False, None, "No session token."
        headers = {"Authorization": f"Bearer {tok}"}
        try:
            resp = requests.get(f"{self.base_url}/api/v1/auth/me", headers=headers, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return True, data.get("user"), "Session valid."
            return False, None, "Session expired or invalid."
        except Exception as err:
            return False, None, f"Backend session check error: {str(err)}"

    def logout(self, token: Optional[str] = None) -> bool:
        """Call FastAPI auth /logout endpoint to revoke session."""
        tok = token or self.token
        if not tok:
            self.token = None
            return True
        headers = {"Authorization": f"Bearer {tok}"}
        try:
            requests.post(f"{self.base_url}/api/v1/auth/logout", headers=headers, timeout=5.0)
        except Exception:
            pass
        self.token = None
        return True
