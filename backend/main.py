"""backend/main.py

AI-Diagnoser FastAPI Core Backend Application.
Provides unified RESTful endpoints for:
- Core AI Services: Documents, Vision, Data Analytics
- LLM Router: Google Gemini, OpenAI, Groq
- n8n Automation Engine: Webhooks, Reports, Email, Slack, Scheduled Jobs
"""

import os
import sys
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import settings
from backend.routers import auth, data, documents, n8n, router as llm_router, vision

app = FastAPI(
    title="AI-Diagnoser Core API",
    description=(
        "Enterprise Multimodal Document Synthesis, Computer Vision OCR, "
        "Structured Data Analytics, LLM Router (Gemini / OpenAI / Groq), "
        "Authentication Engine, and n8n Automation Gateway."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers Middleware (SEC-006: Hardening response headers)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Register Sub-Routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(vision.router)
app.include_router(data.router)
app.include_router(llm_router.router)
app.include_router(n8n.router)


@app.get("/", summary="Root API Gateway Index")
async def root():
    """Returns gateway architecture and endpoint documentation links."""
    return {
        "app": "AI-Diagnoser",
        "version": settings.APP_VERSION,
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "architecture": {
            "frontend": "Streamlit (http://localhost:8501)",
            "backend": "FastAPI (http://localhost:8000)",
            "auth": [
                "/api/v1/auth/login",
                "/api/v1/auth/logout",
                "/api/v1/auth/me",
                "/api/v1/auth/register",
                "/api/v1/auth/status"
            ],
            "core_ai_services": [
                "/api/v1/documents",
                "/api/v1/vision",
                "/api/v1/data"
            ],
            "llm_router": [
                "/api/v1/router/providers",
                "/api/v1/router/query",
                "/api/v1/router/telemetry"
            ],
            "n8n_automation": [
                "/api/v1/n8n/webhook",
                "/api/v1/n8n/reports/generate",
                "/api/v1/n8n/dispatch/email",
                "/api/v1/n8n/dispatch/slack",
                "/api/v1/n8n/schedules",
                "/api/v1/n8n/workflows"
            ]
        },
        "documentation": "/docs"
    }


@app.get("/health", summary="Service Health Check")
async def health():
    """Health check endpoint used by Docker, Nginx, and Streamlit Frontend."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "default_provider": settings.DEFAULT_PROVIDER
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
