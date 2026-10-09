"""backend/scripts/migrate_auth_db.py

Safe migration and backup utility for AI-Diagnoser Authentication and Report Storage.
- Creates timestamped backups before schema alterations
- Applies non-destructive column migrations (role, is_admin, reports table)
- Verifies SQLite database integrity
- Reports user accounts and persistent report counts
"""

import os
import shutil
import sqlite3
import sys
import time


def migrate(db_path: str = "data/auth.db", backup_dir: str = "data") -> None:
    abs_db = os.path.abspath(db_path)
    if not os.path.exists(abs_db):
        print(f"[INFO] Database does not exist yet at {abs_db}. Initializing directory.")
        os.makedirs(os.path.dirname(abs_db), exist_ok=True)
        return

    # 1. Create safe backup
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"auth_backup_{timestamp}.db")
    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
    shutil.copy2(abs_db, backup_file)
    print(f"[BACKUP] Created safe database snapshot at {backup_file}")

    # 2. Check integrity and apply migrations
    conn = sqlite3.connect(abs_db)
    conn.row_factory = sqlite3.Row
    with conn:
        # Integrity check
        check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            print(f"[ERROR] Database integrity check failed: {check}", file=sys.stderr)
            sys.exit(1)

        # Ensure base tables exist
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

        # Migrate user columns if missing
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            print("[MIGRATION] Added 'role' column to users table.")
        if "is_admin" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            print("[MIGRATION] Added 'is_admin' column to users table.")

        users = conn.execute("SELECT id, email, name, role, is_admin FROM users").fetchall()
        reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        print(f"[STATUS] Database verified: {len(users)} users, {reports} reports cataloged.")
        for u in users:
            print(f"  - [{u['id']}] {u['name']} <{u['email']}> role={u['role']} admin={bool(u['is_admin'])}")

    conn.close()
    print("[SUCCESS] Database migration & verification complete.")


if __name__ == "__main__":
    db_target = sys.argv[1] if len(sys.argv) > 1 else "data/auth.db"
    migrate(db_target)
