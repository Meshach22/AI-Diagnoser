"""backend/routers/auth.py

Authentication Router (/api/v1/auth)
Provides endpoints for:
- User login with Argon2id verification and session token generation
- Session validation (/me)
- Session revocation / logout
- User registration (self-service signup)
"""

import secrets
import time
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import settings
from backend.schemas.auth import (
    AuthStatusResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserPublic,
    UserResponse,
)
from backend.services.auth_service import (
    AuthError,
    AuthService,
    SessionInfo,
    get_auth_service,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


def extract_token(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_n8n_secret: Optional[str] = Header(None, alias="X-N8N-Webhook-Secret"),
) -> Optional[str]:
    """Extract session token from Bearer Authorization, X-Session-Token, or X-N8N-Webhook-Secret header."""
    if auth_header and auth_header.credentials:
        return auth_header.credentials
    if x_session_token:
        return x_session_token
    if x_n8n_secret:
        return x_n8n_secret
    return None


def get_current_session(
    token: Optional[str] = Depends(extract_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionInfo:
    """FastAPI dependency to require an active authenticated session."""
    # SEC-004: Fail-closed fallback strictly restricted to local DEBUG mode; NEVER grant admin privileges
    if not settings.AUTH_ENFORCE_API and not token:
        if settings.DEBUG:
            return SessionInfo(
                user_id=0,
                email="developer@local",
                name="Developer Mode (Unprivileged)",
                role="user",
                is_admin=False,
                created_at=time.time(),
                expires_at=time.time() + 86400,
                idle_expires_at=time.time() + 86400,
            )
        # Production or non-debug environments must fail closed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # SEC-003: Support n8n service-to-service integration with constant-time secret comparison
    expected_secret = (settings.N8N_WEBHOOK_SECRET or "").strip()
    if (
        token
        and len(expected_secret) >= 8
        and secrets.compare_digest(token.strip(), expected_secret)
    ):
        return SessionInfo(
            user_id=1,
            email="service:n8n@internal",
            name="n8n Automation Engine",
            role="admin",
            is_admin=True,
            created_at=time.time(),
            expires_at=time.time() + 86400,
            idle_expires_at=time.time() + 86400,
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = auth_service.validate_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


def require_admin(session: SessionInfo = Depends(get_current_session)) -> SessionInfo:
    """FastAPI dependency to require administrative privileges."""
    if not (session.is_admin or session.role == "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )
    return session


@router.get("/status", response_model=AuthStatusResponse, summary="Public registration & auth status")
async def get_auth_status(auth_service: AuthService = Depends(get_auth_service)):
    """Public endpoint providing self-service registration and API enforcement status."""
    users = auth_service.list_users()
    signup_allowed = settings.AUTH_ALLOW_SIGNUP or len(users) == 0
    return AuthStatusResponse(
        signup_allowed=signup_allowed,
        enforce_api=settings.AUTH_ENFORCE_API,
    )


@router.post("/login", response_model=LoginResponse, summary="Sign in with email and password")
async def login(
    req: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user credentials and issue a new secure session token."""
    try:
        token, info = auth_service.authenticate(req.email, req.password)
        return LoginResponse(
            token=token,
            user=UserPublic(
                id=info.user_id,
                email=info.email,
                name=info.name,
                role=info.role,
                is_admin=info.is_admin,
            ),
            expires_at=info.expires_at,
            idle_expires_at=info.idle_expires_at,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/register", response_model=LoginResponse, summary="Create a new user account")
async def register(
    req: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account (strictly non-admin) and automatically sign in."""
    users = auth_service.list_users()
    if not settings.AUTH_ALLOW_SIGNUP and len(users) > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-service registration is disabled. Contact your administrator.",
        )
    try:
        # Crucial security guarantee: self-service registration CANNOT grant administrative privileges
        user_dict = auth_service.create_user(req.email, req.name, req.password, role="user", is_admin=False)
        token, info = auth_service.authenticate(req.email, req.password)
        return LoginResponse(
            token=token,
            user=UserPublic(
                id=info.user_id,
                email=info.email,
                name=info.name,
                role=info.role,
                is_admin=info.is_admin,
            ),
            expires_at=info.expires_at,
            idle_expires_at=info.idle_expires_at,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
async def get_me(session: SessionInfo = Depends(get_current_session)):
    """Retrieve details of the active authenticated session."""
    return UserResponse(
        user=UserPublic(
            id=session.user_id,
            email=session.email,
            name=session.name,
            role=session.role,
            is_admin=session.is_admin,
        ),
        is_authenticated=True,
    )


@router.post("/logout", summary="Sign out and revoke active session")
async def logout(
    token: Optional[str] = Depends(extract_token),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke and invalidate the active session token."""
    if token:
        auth_service.revoke_session(token)
    return {"status": "success", "message": "Signed out successfully."}
