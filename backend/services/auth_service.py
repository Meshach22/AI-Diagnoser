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

import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

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

    def public_user(self) -> Dict[str, object]:
        return {
            "id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_admin": self.is_admin,
        }


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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


class AuthService:
    """SQLite-backed user, session and lockout store."""

    def __init__(
        self,
        db_path: str,
        session_ttl_minutes: int = 480,
        session_idle_minutes: int = 60,
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
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
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
                """
            )
            # Safe column migration for existing user tables
            user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "role" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            if "is_admin" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

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
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, row["id"]))
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
        token = secrets.token_urlsafe(32)
        expires_at = now + self.session_ttl
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM login_failures WHERE email = ?", (norm_email,))
            if self._ph.check_needs_rehash(row["password_hash"]):
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (self._ph.hash(password), row["id"]))
            conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, row["id"]))
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at, last_seen_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (_hash_token(token), row["id"], now, now, expires_at),
            )
            conn.execute("DELETE FROM sessions WHERE expires_at <= ? OR last_seen_at <= ?", (now, now - self.session_idle))

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
        """Return the session if valid; refresh idle timer. Expired sessions are deleted."""
        if not token or not isinstance(token, str) or len(token) > 256:
            return None
        token_hash = _hash_token(token)
        now = self._now()
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                """SELECT s.user_id, s.created_at, s.last_seen_at, s.expires_at,
                          u.email, u.name, u.role, u.is_admin, u.is_active
                   FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?""",
                (token_hash,),
            ).fetchone()
            if not row:
                return None
            if now >= row["expires_at"] or now - row["last_seen_at"] >= self.session_idle or not row["is_active"]:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
                return None
            conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?", (now, token_hash))

        user_role = row["role"] if "role" in row.keys() else "user"
        user_admin = bool(row["is_admin"]) if "is_admin" in row.keys() else False

        return SessionInfo(
            user_id=row["user_id"],
            email=row["email"],
            name=row["name"],
            role=user_role,
            is_admin=user_admin,
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            idle_expires_at=min(row["expires_at"], now + self.session_idle),
        )

    def revoke_session(self, token: Optional[str]) -> None:
        if not token:
            return
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))

    def revoke_user_sessions(self, user_id: int) -> None:
        with closing(self._connect()) as conn, conn:
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
