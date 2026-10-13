"""backend/config.py

Configuration manager for the AI-Diagnoser FastAPI Backend.
Handles environment variables, default providers, CORS origins, and n8n webhook settings.
"""

import json
import os
from typing import Any, List, Optional, Union
from pydantic import field_validator, model_validator
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
        "https://ai-diagnoser-ig8r.vercel.app",
        "https://ai-diagnoser.vercel.app",
    ]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        """Parse list, JSON string, or comma-separated environment variables cleanly, stripping trailing slashes."""
        origins: List[str] = []
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        origins = [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            if not origins:
                origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple, set)):
            origins = [str(item).strip() for item in v if str(item).strip()]
        else:
            origins = [str(v).strip()]

        # Also include any dynamically configured FRONTEND_URL or VERCEL_URL from environment
        env_frontend = os.getenv("FRONTEND_URL") or os.getenv("VERCEL_URL")
        if env_frontend:
            for item in env_frontend.split(","):
                cand = item.strip()
                if cand:
                    if not cand.startswith("http"):
                        cand = f"https://{cand}"
                    origins.append(cand)

        cleaned: List[str] = []
        for o in origins:
            clean = o.rstrip("/")
            if clean and clean not in cleaned:
                cleaned.append(clean)
        return cleaned

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

    # Persistent Secret Key & Token Lifespan (survives backend reloads and prevents invalidation)
    SECRET_KEY: str = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "ai-diagnoser-production-super-secret-key-2026"
    JWT_SECRET: str = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "ai-diagnoser-production-super-secret-key-2026"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days (43,200 minutes)

    # n8n Automation Engine Settings
    N8N_BASE_URL: Optional[str] = os.getenv("N8N_BASE_URL")
    N8N_WEBHOOK_URL: Optional[str] = os.getenv("N8N_WEBHOOK_URL")
    N8N_EMAIL_WEBHOOK_URL: Optional[str] = os.getenv("N8N_EMAIL_WEBHOOK_URL")
    N8N_SLACK_WEBHOOK_URL: Optional[str] = os.getenv("N8N_SLACK_WEBHOOK_URL")
    SLACK_INCOMING_WEBHOOK: Optional[str] = os.getenv("SLACK_INCOMING_WEBHOOK")
    N8N_WEBHOOK_SECRET: Optional[str] = os.getenv("N8N_WEBHOOK_SECRET")

    # Authentication & Persistence
    # Supports AUTH_DB_PATH, DATA_DIR, or DATABASE_URL (e.g. sqlite:////var/data/auth.db for Render Persistent Disk)
    DATABASE_URL: Optional[str] = None
    DATA_DIR: Optional[str] = None
    AUTH_DB_PATH: str = ""

    @model_validator(mode="after")
    def resolve_auth_db_path(self) -> "BackendSettings":
        env_auth_path = os.getenv("AUTH_DB_PATH")
        if self.AUTH_DB_PATH:
            return self
        if env_auth_path:
            self.AUTH_DB_PATH = env_auth_path
            return self

        dir_path = self.DATA_DIR or os.getenv("DATA_DIR")
        if dir_path:
            self.AUTH_DB_PATH = os.path.join(dir_path, "auth.db")
            return self

        db_url = self.DATABASE_URL or os.getenv("DATABASE_URL")
        if db_url and db_url.startswith("sqlite"):
            self.AUTH_DB_PATH = db_url.replace("sqlite:///", "").replace("sqlite://", "")
            return self

        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        self.AUTH_DB_PATH = os.path.join(default_dir, "auth.db")
        return self

    AUTH_SESSION_TTL_MINUTES: int = 43200   # 30-day absolute session lifetime (survives restarts)
    AUTH_SESSION_IDLE_MINUTES: int = 43200  # 30-day idle timeout
    AUTH_MAX_FAILED_ATTEMPTS: int = 5          # per-account failures before lockout
    AUTH_LOCKOUT_MINUTES: int = 15             # lockout window / duration
    AUTH_ALLOW_SIGNUP: bool = False            # self-service registration (off by default)
    AUTH_ENFORCE_API: bool = True              # require a session on user-facing API routes

    # Cookie settings for cross-domain / same-site browser session persistence
    AUTH_COOKIE_NAME: str = "ai_diagnoser_session"
    AUTH_COOKIE_SECURE: bool = True
    AUTH_COOKIE_SAMESITE: str = "none"         # 'none' enables cross-origin credentialed requests (Vercel -> Render)
    AUTH_COOKIE_DOMAIN: Optional[str] = None

    # Upload Limits (SEC-002: Bounded upload size to protect container memory)
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024

    class Config:
        env_file = ".env"
        extra = "allow"


settings = BackendSettings()
