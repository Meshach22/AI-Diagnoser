"""backend/config.py

Configuration manager for the AI-Diagnoser FastAPI Backend.
Handles environment variables, default providers, CORS origins, and n8n webhook settings.
"""

import json
import os
from typing import Any, List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class BackendSettings(BaseSettings):
    """FastAPI Backend Settings."""
    APP_NAME: str = "AI-Diagnoser Backend"
    APP_VERSION: str = "2.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # CORS: Explicit allowlist replacing insecure wildcard for authenticated SaaS deployment.
    # Accepts list or comma-separated string from Render/deployment environment variables.
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://127.0.0.1",
        "https://localhost",
    ]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        """Parse list, JSON string, or comma-separated environment variables cleanly."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(item).strip() for item in v if str(item).strip()]
        return [str(v)]

    # LLM Router Defaults (Gemini, OpenAI, Groq)
    DEFAULT_PROVIDER: str = "Google Gemini"
    DEFAULT_MODEL_GEMINI: str = "gemini-3.8-flash"
    DEFAULT_MODEL_OPENAI: str = "gpt-4o-mini"
    DEFAULT_MODEL_GROQ: str = "llama-3.3-70b-versatile"

    # API Keys (Resolved from environment or .env)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")

    # n8n Automation Engine Settings
    N8N_BASE_URL: Optional[str] = os.getenv("N8N_BASE_URL")
    N8N_WEBHOOK_URL: Optional[str] = os.getenv("N8N_WEBHOOK_URL")
    N8N_EMAIL_WEBHOOK_URL: Optional[str] = os.getenv("N8N_EMAIL_WEBHOOK_URL")
    N8N_SLACK_WEBHOOK_URL: Optional[str] = os.getenv("N8N_SLACK_WEBHOOK_URL")
    SLACK_INCOMING_WEBHOOK: Optional[str] = os.getenv("SLACK_INCOMING_WEBHOOK")
    N8N_WEBHOOK_SECRET: Optional[str] = os.getenv("N8N_WEBHOOK_SECRET")

    # Authentication (no credentials are defined here; users are created via
    # `python -m backend.auth_cli create-user` or optional self-service signup)
    AUTH_DB_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "auth.db"
    )
    AUTH_SESSION_TTL_MINUTES: int = 480        # absolute session lifetime
    AUTH_SESSION_IDLE_MINUTES: int = 60        # idle timeout
    AUTH_MAX_FAILED_ATTEMPTS: int = 5          # per-account failures before lockout
    AUTH_LOCKOUT_MINUTES: int = 15             # lockout window / duration
    AUTH_ALLOW_SIGNUP: bool = False            # self-service registration (off by default)
    AUTH_ENFORCE_API: bool = True              # require a session on user-facing API routes

    class Config:
        env_file = ".env"
        extra = "allow"


settings = BackendSettings()
