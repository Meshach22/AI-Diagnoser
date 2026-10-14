"""backend/services/auth_service.py

Authentication service for AI-Diagnoser.

Design:
- Persistent user storage in SQLite (stdlib, file path from AUTH_DB_PATH).
- Passwords hashed with Argon2id (argon2-cffi PasswordHasher defaults, RFC 9106);
  plaintext passwords are never stored or logged.
- Opaque, random session tokens (secrets.token_urlsafe, 256 bits). Only the
  SHA-256 digest of a token is stored, so a database leak does not yield usable
  sessions. Every successful login issues a brand-new token (prevents session
  fixation); logout deletes the server-side session.
- Sessions enforce both an absolute lifetime and an idle timeout, validated
  server-side on every request.
- Brute-force protection: per-account sliding-window lockout after N failures.
  Unknown accounts still incur a full hash verification to reduce timing-based
  account enumeration, and all credential errors use one generic message.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
NAME_MAX_LENGTH = 80
EMAIL_MAX_LENGTH = 254
_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

GENERIC_LOGIN_ERROR = "Invalid email or password."
LOCKED_ERROR = "Too many failed sign-in attempts. Please try again later."


class AuthError(Exception):
    """Authentication/validation failure with a user-safe message."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class SessionInfo:
    user_id: int
    email: str
    name: str
    role: str = "user"
    is_admin: bool = False
    created_at: float = 0.0
    expires_at: float = 0.0
    idle_expires_at: float = 0.0
    picture: Optional[str] = None

    def public_user(self) -> Dict[str, object]:
        return {
            "id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_admin": self.is_admin,
            "picture": self.picture,
        }


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_signed_token(
    user_id: int,
    email: str,
    name: str,
    role: str,
    is_admin: bool,
    created_at: float,
    expires_at: float,
    secret_key: str,
    picture: Optional[str] = None
) -> str:
    """Create an HMAC-SHA256 authenticated persistent session token."""
    payload_data = {
        "uid": user_id,
        "em": email,
        "nm": name,
        "ro": role,
        "adm": 1 if is_admin else 0,
        "ca": int(created_at),
        "exp": int(expires_at),
        "pic": picture or "",
        "rnd": secrets.token_hex(8),
    }
    raw_json = json.dumps(payload_data, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(raw_json.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"adt_{payload_b64}.{sig}"


def _verify_signed_token(token: str, secret_key: str, idle_timeout: float = 86400 * 30) -> Optional[SessionInfo]:
    """Verify HMAC signature and decode payload if token has signed format."""
    if not token or not token.startswith("adt_"):
        return None
    try:
        parts = token[4:].split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts[0], parts[1]
        expected_sig = hmac.new(secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(sig, expected_sig):
            return None

        pad_len = 4 - (len(payload_b64) % 4)
        if pad_len != 4:
            payload_b64 += "=" * pad_len
        payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        data = json.loads(payload_json)

        now = time.time()
        exp = float(data.get("exp", 0))
        if now >= exp:
            return None

        pic = str(data.get("pic", "")).strip() or None
        return SessionInfo(
            user_id=int(data.get("uid", 0)),
            email=str(data.get("em", "")),
            name=str(data.get("nm", "User")),
            role=str(data.get("ro", "user")),
            is_admin=bool(data.get("adm", 0)),
            created_at=float(data.get("ca", now)),
            expires_at=exp,
            idle_expires_at=min(exp, now + idle_timeout),
            picture=pic,
        )
    except Exception:
        return None


JWT_ISSUER = "ai-diagnoser"
MAX_TOKEN_LENGTH = 2048
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _create_jwt(
    email: str,
    name: str,
    role: str,
    is_admin: bool,
    issued_at: float,
    expires_at: float,
    secret_key: str,
) -> str:
    """Create a standard stateless HS256 JWT identifying the user strictly by email (`sub`).

    No server-side session row is required to validate it, so any number of workers /
    serverless instances can verify it independently without sharing state.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {
        "iss": JWT_ISSUER,
        "sub": email,
        "nm": name,
        "ro": role,
        "adm": 1 if is_admin else 0,
        "iat": round(float(issued_at), 3),
        "exp": int(expires_at),
        "jti": secrets.token_hex(8),
    }
    signing_input = (
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    )
    sig = hmac.new(secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def _verify_jwt(token: str, secret_key: str, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Verify an HS256 JWT signature, algorithm, issuer and expiry. Returns claims or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header = json.loads(_b64url_decode(parts[0]))
        if header.get("alg") != "HS256":  # reject 'none' / algorithm-confusion attempts
            return None
        expected = hmac.new(
            secret_key.encode("utf-8"), f"{parts[0]}.{parts[1]}".encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64url_decode(parts[2])):
            return None
        claims = json.loads(_b64url_decode(parts[1]))
        if claims.get("iss") != JWT_ISSUER or not claims.get("sub"):
            return None
        if (now if now is not None else time.time()) >= float(claims.get("exp", 0)):
            return None
        return claims
    except Exception:
        return None


def verify_google_id_token(credential: str, client_id: str) -> Dict[str, Any]:
    """Verify a Google Identity Services ID token and return trusted claims.

    Validates signature (Google public certs), expiry, issuer and audience (our OAuth client ID).
    Raises AuthError on any failure. Identity data is NEVER accepted from the client body.
    """
    if not client_id:
        raise AuthError("google_not_configured", "Google sign-in is not configured on the server.", 503)
    if not credential or not isinstance(credential, str) or len(credential) > 4096:
        raise AuthError("invalid_google_token", "Invalid Google credential.", 401)
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        info = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id, clock_skew_in_seconds=10
        )
    except Exception:
        raise AuthError("invalid_google_token", "Google sign-in could not be verified. Please try again.", 401)
    if info.get("iss") not in GOOGLE_ISSUERS:
        raise AuthError("invalid_google_token", "Google sign-in could not be verified.", 401)
    if not info.get("email") or not info.get("email_verified", False):
        raise AuthError("unverified_email", "Your Google account email is not verified.", 401)
    return {
        "email": str(info["email"]),
        "name": str(info.get("name") or ""),
        "picture": str(info.get("picture") or "") or None,
    }


def validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise AuthError("weak_password", f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise AuthError("weak_password", f"Password must be at most {PASSWORD_MAX_LENGTH} characters.")
    if password.strip() == "":
        raise AuthError("weak_password", "Password cannot be only whitespace.")


def validate_email(email: str) -> str:
    norm = normalize_email(email)
    if len(norm) > EMAIL_MAX_LENGTH or not _EMAIL_RE.match(norm):
        raise AuthError("invalid_email", "Enter a valid email address.")
    return norm


def validate_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean or len(clean) > NAME_MAX_LENGTH or _CONTROL_RE.search(clean):
        raise AuthError("invalid_name", f"Name must be 1-{NAME_MAX_LENGTH} printable characters.")
    return clean


ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days (43,200 minutes)


class AuthService:
    """SQLite-backed user, session and lockout store."""

    def __init__(
        self,
        db_path: str,
        session_ttl_minutes: int = 60 * 24 * 30,  # 30 days
        session_idle_minutes: int = 60 * 24 * 30,  # 30 days
        max_failed_attempts: int = 5,
        lockout_minutes: int = 15,
        clock: Optional[Callable[[], float]] = None,
        hasher: Optional[PasswordHasher] = None,
    ):
        self.db_path = db_path
        self.session_ttl = max(1, int(session_ttl_minutes)) * 60
        self.session_idle = max(1, int(session_idle_minutes)) * 60
        self.max_failed = max(1, int(max_failed_attempts))
        self.lockout_window = max(1, int(lockout_minutes)) * 60
        self._now = clock or time.time
        self._ph = hasher or PasswordHasher()  # Argon2id by default
        # Hash of a random value, used to equalise timing for unknown accounts.
        self._dummy_hash = self._ph.hash(secrets.token_urlsafe(32))
        self._init_lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------ db
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # WAL lets readers proceed during writes and serialises writers cleanly, which is
        # what allows many concurrent users to share one SQLite file without lock errors.
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _init_db(self) -> None:
        directory = os.path.dirname(os.path.abspath(self.db_path))
        os.makedirs(directory, exist_ok=True)
        with self._init_lock, closing(self._connect()) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    last_login_at REAL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    last_seen_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE TABLE IF NOT EXISTS login_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    ts REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_failures_email_ts ON login_failures(email, ts);
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    report_type TEXT NOT NULL DEFAULT 'markdown',
                    content TEXT NOT NULL,
                    recipient_email TEXT,
                    slack_channel TEXT,
                    status TEXT NOT NULL DEFAULT 'ready',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
                CREATE TABLE IF NOT EXISTS user_workspace_memory (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    memory_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS revoked_tokens (
                       token_hash TEXT PRIMARY KEY,
                       expires_at REAL NOT NULL
                   )"""
            )
            # Safe column migration for existing user tables
            user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "role" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            if "picture" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN picture TEXT")
            if "is_admin" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            if "tokens_valid_after" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN tokens_valid_after REAL NOT NULL DEFAULT 0")

    # --------------------------------------------------------------- users
    def create_user(
        self,
        email: str,
        name: str,
        password: str,
        role: str = "user",
        is_admin: bool = False,
    ) -> Dict[str, object]:
        norm_email = validate_email(email)
        clean_name = validate_name(name)
        validate_password(password)
        pw_hash = self._ph.hash(password)
        clean_role = "admin" if (is_admin or role == "admin") else "user"
        admin_int = 1 if (is_admin or role == "admin") else 0
        try:
            with closing(self._connect()) as conn, conn:
                cur = conn.execute(
                    "INSERT INTO users (email, name, password_hash, role, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (norm_email, clean_name, pw_hash, clean_role, admin_int, self._now()),
                )
                user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            raise AuthError("account_unavailable", "An account could not be created with these details.", 409)
        return {
            "id": user_id,
            "email": norm_email,
            "name": clean_name,
            "role": clean_role,
            "is_admin": bool(admin_int),
        }

    def list_users(self) -> List[Dict[str, object]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, email, name, role, is_admin, is_active, created_at, last_login_at FROM users ORDER BY id"
            ).fetchall()
        return [
            {
                "id": r["id"],
                "email": r["email"],
                "name": r["name"],
                "role": r["role"] if "role" in r.keys() else "user",
                "is_admin": bool(r["is_admin"]) if "is_admin" in r.keys() else False,
                "is_active": bool(r["is_active"]),
                "created_at": r["created_at"],
                "last_login_at": r["last_login_at"],
            }
            for r in rows
        ]

    def set_role(self, email: str, role: str, is_admin: Optional[bool] = None) -> bool:
        norm_email = normalize_email(email)
        clean_role = "admin" if (role == "admin" or is_admin) else "user"
        admin_val = 1 if clean_role == "admin" else 0
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "UPDATE users SET role = ?, is_admin = ? WHERE email = ?",
                (clean_role, admin_val, norm_email),
            )
            return cur.rowcount > 0

    def delete_user(self, email: str) -> bool:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM users WHERE email = ?", (normalize_email(email),))
            return cur.rowcount > 0

    def set_password(self, email: str, new_password: str) -> bool:
        validate_password(new_password)
        pw_hash = self._ph.hash(new_password)
        with closing(self._connect()) as conn, conn:
            row = conn.execute("SELECT id FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
            if not row:
                return False
            conn.execute("UPDATE users SET password_hash = ?, tokens_valid_after = ? WHERE id = ?", (pw_hash, self._now(), row["id"]))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))  # revoke all sessions
        return True

    # ------------------------------------------------------------- lockout
    def _recent_failures(self, conn: sqlite3.Connection, email: str, now: float) -> List[float]:
        rows = conn.execute(
            "SELECT ts FROM login_failures WHERE email = ? AND ts > ? ORDER BY ts",
            (email, now - self.lockout_window),
        ).fetchall()
        return [r["ts"] for r in rows]

    def is_locked(self, email: str) -> bool:
        now = self._now()
        with closing(self._connect()) as conn:
            return len(self._recent_failures(conn, normalize_email(email), now)) >= self.max_failed

    def _record_failure(self, email: str) -> None:
        now = self._now()
        with closing(self._connect()) as conn, conn:
            conn.execute("INSERT INTO login_failures (email, ts) VALUES (?, ?)", (email, now))
            conn.execute("DELETE FROM login_failures WHERE ts <= ?", (now - self.lockout_window,))

    # ---------------------------------------------------------- sign-in/out
    def authenticate(self, email: str, password: str) -> tuple[str, SessionInfo]:
        """Verify credentials and return (new_session_token, session_info)."""
        norm_email = normalize_email(email)
        if not norm_email or not isinstance(password, str) or not password or len(password) > PASSWORD_MAX_LENGTH:
            raise AuthError("invalid_credentials", GENERIC_LOGIN_ERROR, 401)

        if self.is_locked(norm_email):
            raise AuthError("locked", LOCKED_ERROR, 429)

        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, email, name, password_hash, role, is_admin, is_active FROM users WHERE email = ?",
                (norm_email,),
            ).fetchone()

        verified = False
        try:
            self._ph.verify(row["password_hash"] if row else self._dummy_hash, password)
            verified = row is not None
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            verified = False

        if not verified or not row["is_active"]:
            self._record_failure(norm_email)
            raise AuthError("invalid_credentials", GENERIC_LOGIN_ERROR, 401)

        now = self._now()
        expires_at = now + self.session_ttl
        user_role = row["role"] if "role" in row.keys() else "user"
        user_admin = bool(row["is_admin"]) if "is_admin" in row.keys() else False

        from backend.config import settings
        secret = settings.SECRET_KEY or "ai-diagnoser-production-super-secret-key-2026"
        token = _create_jwt(
            email=row["email"],
            name=row["name"],
            role=user_role,
            is_admin=user_admin,
            issued_at=now,
            expires_at=expires_at,
            secret_key=secret,
        )
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM login_failures WHERE email = ?", (norm_email,))
            if self._ph.check_needs_rehash(row["password_hash"]):
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (self._ph.hash(password), row["id"]))
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row["id"]))

        user_role = row["role"] if "role" in row.keys() else "user"
        user_admin = bool(row["is_admin"]) if "is_admin" in row.keys() else False

        info = SessionInfo(
            user_id=row["id"],
            email=row["email"],
            name=row["name"],
            role=user_role,
            is_admin=user_admin,
            created_at=now,
            expires_at=expires_at,
            idle_expires_at=min(expires_at, now + self.session_idle),
        )
        return token, info

    def validate_session(self, token: Optional[str]) -> Optional[SessionInfo]:
        """Validate a stateless signed JWT (or a legacy signed `adt_` token).

        The signature + expiry are verified in-process (no DB write, no shared session state).
        The user's identity is then resolved strictly by the token's email from SQLite, so the
        returned `user_id` always belongs to that email -- even if the database file was re-created
        since the token was issued -- which prevents cross-user data contamination.
        """
        if not token or not isinstance(token, str) or len(token) > MAX_TOKEN_LENGTH:
            return None
        now = self._now()

        from backend.config import settings
        secret = settings.SECRET_KEY or "ai-diagnoser-production-super-secret-key-2026"

        claims = _verify_jwt(token, secret, now=now)
        if claims is not None:
            email = normalize_email(str(claims["sub"]))
            token_name = str(claims.get("nm") or "User")
            created_at = float(claims.get("iat", now))
            expires_at = float(claims["exp"])
        else:
            legacy = _verify_signed_token(token, secret, idle_timeout=self.session_idle)
            if not legacy:
                return None
            email = normalize_email(legacy.email)
            token_name = legacy.name
            created_at = legacy.created_at
            expires_at = legacy.expires_at
        if not email:
            return None

        token_hash = _hash_token(token)
        with closing(self._connect()) as conn:
            if conn.execute("SELECT 1 FROM revoked_tokens WHERE token_hash = ?", (token_hash,)).fetchone():
                return None
            row = conn.execute(
                "SELECT id, email, name, role, is_admin, is_active, picture, tokens_valid_after FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        if row is None:
            # Database was re-created (e.g. ephemeral disk). Re-provision a plain, non-privileged
            # account for this verified email; privileges are never taken from the token here.
            try:
                with closing(self._connect()) as conn, conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO users (email, name, password_hash, role, is_admin, created_at) "
                        "VALUES (?, ?, ?, 'user', 0, ?)",
                        (email, token_name, self._dummy_hash, now),
                    )
                    row = conn.execute(
                        "SELECT id, email, name, role, is_admin, is_active, picture, tokens_valid_after FROM users WHERE email = ?",
                        (email,),
                    ).fetchone()
            except sqlite3.Error:
                return None
            if row is None:
                return None

        if not row["is_active"] or created_at < float(row["tokens_valid_after"] or 0):
            return None

        return SessionInfo(
            user_id=row["id"],
            email=row["email"],
            name=row["name"],
            role=row["role"] if "role" in row.keys() else "user",
            is_admin=bool(row["is_admin"]) if "is_admin" in row.keys() else False,
            created_at=created_at,
            expires_at=expires_at,
            idle_expires_at=min(expires_at, now + self.session_idle),
            picture=row["picture"] if "picture" in row.keys() else None,
        )

    def revoke_session(self, token: Optional[str]) -> None:
        """Revoke a stateless token on logout by recording its hash until it would have expired."""
        if not token or not isinstance(token, str) or len(token) > MAX_TOKEN_LENGTH:
            return
        now = self._now()
        expires_at = now + self.session_ttl
        from backend.config import settings
        secret = settings.SECRET_KEY or "ai-diagnoser-production-super-secret-key-2026"
        claims = _verify_jwt(token, secret, now=now)
        if claims is not None:
            expires_at = float(claims["exp"])
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO revoked_tokens (token_hash, expires_at) VALUES (?, ?)",
                (_hash_token(token), expires_at),
            )
            conn.execute("DELETE FROM revoked_tokens WHERE expires_at <= ?", (now,))
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))

    def revoke_user_sessions(self, user_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("UPDATE users SET tokens_valid_after = ? WHERE id = ?", (self._now(), user_id))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    # ------------------------------------------------------------- reports
    def save_report(
        self,
        user_id: int,
        title: str,
        content: str,
        report_type: str = "markdown",
        recipient_email: Optional[str] = None,
        slack_channel: Optional[str] = None,
        status: str = "ready",
        report_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist a generated diagnostic report associated with its authenticated owner."""
        rep_id = report_id or f"REP-{secrets.token_hex(4).upper()}"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(self._now()))
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """INSERT INTO reports (report_id, user_id, title, report_type, content, recipient_email, slack_channel, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rep_id, user_id, title, report_type, content, recipient_email, slack_channel, status, now_str),
            )
        return {
            "report_id": rep_id,
            "user_id": user_id,
            "title": title,
            "report_type": report_type,
            "content": content,
            "recipient_email": recipient_email,
            "slack_channel": slack_channel,
            "status": status,
            "created_at": now_str,
        }

    def get_report(
        self,
        report_id: str,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cataloged report by ID with strict user isolation."""
        with closing(self._connect()) as conn:
            if is_admin or user_id is None:
                row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM reports WHERE report_id = ? AND user_id = ?",
                    (report_id, user_id),
                ).fetchone()
        return dict(row) if row else None

    def list_reports(
        self,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> List[Dict[str, Any]]:
        """List reports belonging to a user (or all if admin)."""
        with closing(self._connect()) as conn:
            if is_admin and user_id is None:
                rows = conn.execute("SELECT * FROM reports ORDER BY rowid DESC").fetchall()
            elif user_id is not None:
                rows = conn.execute(
                    "SELECT * FROM reports WHERE user_id = ? ORDER BY rowid DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = []
        return [dict(r) for r in rows]

    def delete_report(
        self,
        report_id: str,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> bool:
        """Delete report with ownership enforcement."""
        with closing(self._connect()) as conn, conn:
            if is_admin or user_id is None:
                cur = conn.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
            else:
                cur = conn.execute(
                    "DELETE FROM reports WHERE report_id = ? AND user_id = ?",
                    (report_id, user_id),
                )
            return cur.rowcount > 0

    # --------------------------------------------------- workspace memory
    def get_user_memory(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve persistent workspace memory for a user."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT memory_json FROM user_workspace_memory WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row and row["memory_json"]:
                try:
                    return json.loads(row["memory_json"])
                except Exception:
                    return None
        return None

    def save_user_memory(self, user_id: int, memory_data: Dict[str, Any]) -> bool:
        """Upsert persistent workspace memory for a user."""
        now = self._now()
        mem_json = json.dumps(memory_data)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """INSERT INTO user_workspace_memory (user_id, memory_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET memory_json = excluded.memory_json, updated_at = excluded.updated_at""",
                (user_id, mem_json, now),
            )
        return True

    # ---------------------------------------------------- google auth
    def authenticate_or_create_google_user(
        self,
        email: str,
        name: Optional[str] = None,
        picture: Optional[str] = None,
    ) -> tuple[str, SessionInfo]:
        """Verify/create user via Google sign-in and issue active session."""
        norm_email = validate_email(email)
        try:
            clean_name = validate_name((name or "").strip()[:NAME_MAX_LENGTH]) if (name and name.strip()) else norm_email.split("@")[0].capitalize()
        except AuthError:
            clean_name = norm_email.split("@")[0].capitalize()
        with closing(self._connect()) as conn, conn:
            row = conn.execute("SELECT id, email, name, role, is_admin, is_active, picture FROM users WHERE email = ?", (norm_email,)).fetchone()
            if row is not None and not row["is_active"]:
                raise AuthError("account_disabled", "This account has been disabled.", 403)
            if not row:
                # Google accounts have no usable password: reuse the hash of an unguessable random secret.
                # INSERT OR IGNORE keeps simultaneous first sign-ins for the same email race-safe.
                conn.execute(
                    "INSERT OR IGNORE INTO users (email, name, password_hash, role, is_admin, created_at, picture) VALUES (?, ?, ?, 'user', 0, ?, ?)",
                    (norm_email, clean_name, self._dummy_hash, self._now(), picture),
                )
                row = conn.execute("SELECT id, email, name, role, is_admin, is_active, picture FROM users WHERE email = ?", (norm_email,)).fetchone()
            else:
                updates = []
                params = []
                if picture and picture != row["picture"]:
                    updates.append("picture = ?")
                    params.append(picture)
                if clean_name and clean_name != row["name"] and clean_name != "Workspace Analyst":
                    updates.append("name = ?")
                    params.append(clean_name)
                if updates:
                    params.append(row["id"])
                    conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
                    row = conn.execute("SELECT id, email, name, role, is_admin, is_active, picture FROM users WHERE id = ?", (row["id"],)).fetchone()

        now = self._now()
        expires_at = now + self.session_ttl
        user_role = row["role"] if "role" in row.keys() else "user"
        user_admin = bool(row["is_admin"]) if "is_admin" in row.keys() else False
        user_pic = row["picture"] if "picture" in row.keys() else picture

        from backend.config import settings
        secret = settings.SECRET_KEY or "ai-diagnoser-production-super-secret-key-2026"
        token = _create_jwt(
            email=row["email"],
            name=row["name"],
            role=user_role,
            is_admin=user_admin,
            issued_at=now,
            expires_at=expires_at,
            secret_key=secret,
        )
        with closing(self._connect()) as conn, conn:
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row["id"]))

        info = SessionInfo(
            user_id=row["id"],
            email=row["email"],
            name=row["name"],
            role=user_role,
            is_admin=user_admin,
            created_at=now,
            expires_at=expires_at,
            idle_expires_at=min(expires_at, now + self.session_idle),
            picture=user_pic,
        )
        return token, info



_service: Optional[AuthService] = None
_service_lock = threading.Lock()


def get_auth_service() -> AuthService:
    """FastAPI dependency / singleton accessor configured from BackendSettings."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                from backend.config import settings
                _service = AuthService(
                    db_path=settings.AUTH_DB_PATH,
                    session_ttl_minutes=settings.AUTH_SESSION_TTL_MINUTES,
                    session_idle_minutes=settings.AUTH_SESSION_IDLE_MINUTES,
                    max_failed_attempts=settings.AUTH_MAX_FAILED_ATTEMPTS,
                    lockout_minutes=settings.AUTH_LOCKOUT_MINUTES,
                )
    return _service
