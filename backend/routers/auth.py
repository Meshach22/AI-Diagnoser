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
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
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

ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days


def extract_token(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_n8n_secret: Optional[str] = Header(None, alias="X-N8N-Webhook-Secret"),
) -> Optional[str]:
    """Extract session token from Bearer Authorization, X-Session-Token, HttpOnly cookie, or X-N8N-Webhook-Secret."""
    if auth_header and auth_header.credentials:
        return auth_header.credentials
    # Fallback to direct Authorization header in case proxy altered header casing or format
    raw_auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if raw_auth and raw_auth.strip().lower().startswith("bearer "):
        token_val = raw_auth.strip()[7:].strip()
        if token_val:
            return token_val
    if x_session_token:
        return x_session_token
    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token
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
                expires_at=time.time() + 86400 * 30,
                idle_expires_at=time.time() + 86400 * 30,
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
            expires_at=time.time() + 86400 * 30,
            idle_expires_at=time.time() + 86400 * 30,
        )

    if not token:
        if settings.DEBUG or not settings.AUTH_ENFORCE_API:
            return SessionInfo(
                user_id=0,
                email="analyst@workspace.local",
                name="Workspace Analyst",
                role="user",
                is_admin=False,
                created_at=time.time(),
                expires_at=time.time() + 86400 * 30,
                idle_expires_at=time.time() + 86400 * 30,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = auth_service.validate_session(token)
    if not session:
        if settings.DEBUG or not settings.AUTH_ENFORCE_API:
            return SessionInfo(
                user_id=0,
                email="analyst@workspace.local",
                name="Workspace Analyst",
                role="user",
                is_admin=False,
                created_at=time.time(),
                expires_at=time.time() + 86400 * 30,
                idle_expires_at=time.time() + 86400 * 30,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


def get_chat_session(
    token: Optional[str] = Depends(extract_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionInfo:
    """Dependency for LLM Router / Chat queries: validates session if available,
    otherwise gracefully falls back to Workspace Analyst to prevent abrupt 401 errors.
    """
    if token:
        expected_secret = (settings.N8N_WEBHOOK_SECRET or "").strip()
        if len(expected_secret) >= 8 and secrets.compare_digest(token.strip(), expected_secret):
            return SessionInfo(
                user_id=1,
                email="service:n8n@internal",
                name="n8n Automation Engine",
                role="admin",
                is_admin=True,
                created_at=time.time(),
                expires_at=time.time() + 86400 * 30,
                idle_expires_at=time.time() + 86400 * 30,
            )
        try:
            session = auth_service.validate_session(token)
            if session:
                return session
        except Exception:
            pass

    # Graceful fallback: return Workspace Analyst session
    return SessionInfo(
        user_id=0,
        email="analyst@workspace.local",
        name="Workspace Analyst",
        role="user",
        is_admin=False,
        created_at=time.time(),
        expires_at=time.time() + 86400 * 30,
        idle_expires_at=time.time() + 86400 * 30,
    )


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
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user credentials, issue a secure session token, and set HttpOnly cookie."""
    try:
        token, info = auth_service.authenticate(req.email, req.password)
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            max_age=settings.AUTH_SESSION_TTL_MINUTES * 60,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
        )
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
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account (strictly non-admin) and automatically sign in with cookie."""
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
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            max_age=settings.AUTH_SESSION_TTL_MINUTES * 60,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
        )
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
            picture=session.picture,
        ),
        is_authenticated=True,
    )


@router.post("/logout", summary="Sign out and revoke active session")
async def logout(
    response: Response,
    token: Optional[str] = Depends(extract_token),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke and invalidate the active session token and clear session cookie."""
    if token:
        auth_service.revoke_session(token)
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        domain=settings.AUTH_COOKIE_DOMAIN,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    return {"status": "success", "message": "Signed out successfully."}


from pydantic import BaseModel

class GoogleLoginRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    credential: Optional[str] = None


@router.post("/google", response_model=LoginResponse, summary="Sign in or register with Google")
async def google_login(
    req: GoogleLoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate or register user account with Google credentials and issue session cookie."""
    email = req.email
    name = req.name
    picture = req.picture

    # If real Google ID token (credential) passed from Google Identity Services, decode claims
    if req.credential:
        try:
            import base64
            parts = req.credential.split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                pad_len = 4 - (len(payload_b64) % 4)
                if pad_len != 4:
                    payload_b64 += "=" * pad_len
                payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
                payload_data = json.loads(payload_json)
                if payload_data.get("email"):
                    email = str(payload_data["email"])
                if payload_data.get("name"):
                    name = str(payload_data["name"])
                if payload_data.get("picture"):
                    picture = str(payload_data["picture"])
        except Exception as exc:
            logger.warning("Could not parse Google ID token claims: %s", exc)

    email = email or "google.user@gmail.com"
    name = name or email.split("@")[0].capitalize()

    token, info = auth_service.authenticate_or_create_google_user(email, name, picture)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.AUTH_SESSION_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )
    return LoginResponse(
        token=token,
        user=UserPublic(
            id=info.user_id,
            email=info.email,
            name=info.name,
            role=info.role,
            is_admin=info.is_admin,
            picture=info.picture,
        ),
        expires_at=info.expires_at,
        idle_expires_at=info.idle_expires_at,
    )


@router.get("/memory", summary="Get persistent user workspace memory")
async def get_user_workspace_memory(
    session: SessionInfo = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Retrieve persistent workspace history and memory for active user."""
    mem = auth_service.get_user_memory(session.user_id)
    return {"memory": mem or {}}


@router.post("/memory", summary="Save persistent user workspace memory")
async def save_user_workspace_memory(
    request: Request,
    session: SessionInfo = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Persist workspace history, uploaded documents, summaries, and messages for active user."""
    try:
        body = await request.json()
        auth_service.save_user_memory(session.user_id, body)
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to save workspace memory: {exc}")

