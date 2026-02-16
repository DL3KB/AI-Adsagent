"""
SQLite Cache & Audit Log Service

- Caches Google Ads API responses for 15 minutes to reduce API calls
- Logs all proposal executions for audit trail
"""

import sqlite3
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.models.schemas import AuditLogEntry

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "adsagent.db"
CACHE_TTL_MINUTES = 15


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                proposal_id TEXT,
                campaign_id TEXT,
                campaign_name TEXT,
                ad_group_id TEXT,
                keyword_id TEXT,
                keyword_text TEXT,
                old_value TEXT,
                new_value TEXT,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
        """)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# CACHE
# ============================================================

def _cache_key(prefix: str, **kwargs) -> str:
    """Generate a deterministic cache key."""
    raw = f"{prefix}:" + json.dumps(kwargs, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def cache_get(prefix: str, **kwargs) -> Optional[str]:
    """Get cached data if not expired. Returns JSON string or None."""
    key = _cache_key(prefix, **kwargs)
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data, expires_at FROM cache WHERE cache_key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.now() > expires:
            conn.execute("DELETE FROM cache WHERE cache_key = ?", (key,))
            conn.commit()
            return None
        logger.debug(f"Cache HIT: {prefix}")
        return row["data"]
    finally:
        conn.close()


def cache_set(prefix: str, data: str, ttl_minutes: int = CACHE_TTL_MINUTES, **kwargs):
    """Store data in cache with TTL."""
    key = _cache_key(prefix, **kwargs)
    now = datetime.now()
    expires = now + timedelta(minutes=ttl_minutes)
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO cache (cache_key, data, created_at, expires_at)
               VALUES (?, ?, ?, ?)""",
            (key, data, now.isoformat(), expires.isoformat()),
        )
        conn.commit()
        logger.debug(f"Cache SET: {prefix} (TTL={ttl_minutes}min)")
    finally:
        conn.close()


def cache_clear():
    """Clear all cached data."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM cache")
        conn.commit()
        logger.info("Cache cleared")
    finally:
        conn.close()


def cache_cleanup():
    """Remove expired cache entries."""
    conn = _get_conn()
    try:
        now = datetime.now().isoformat()
        result = conn.execute("DELETE FROM cache WHERE expires_at < ?", (now,))
        conn.commit()
        if result.rowcount > 0:
            logger.debug(f"Cleaned up {result.rowcount} expired cache entries")
    finally:
        conn.close()


# ============================================================
# AUDIT LOG
# ============================================================

def log_action(
    action: str,
    success: bool = True,
    proposal_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    campaign_name: Optional[str] = None,
    ad_group_id: Optional[str] = None,
    keyword_id: Optional[str] = None,
    keyword_text: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Log an action to the audit trail."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO audit_log
               (timestamp, action, proposal_id, campaign_id, campaign_name,
                ad_group_id, keyword_id, keyword_text, old_value, new_value,
                success, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                action,
                proposal_id,
                campaign_id,
                campaign_name,
                ad_group_id,
                keyword_id,
                keyword_text,
                old_value,
                new_value,
                1 if success else 0,
                error_message,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    finally:
        conn.close()


def get_audit_log(limit: int = 100, offset: int = 0) -> list[AuditLogEntry]:
    """Get audit log entries, newest first."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        entries = []
        for row in rows:
            entries.append(AuditLogEntry(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                action=row["action"],
                proposal_id=row["proposal_id"],
                campaign_id=row["campaign_id"],
                campaign_name=row["campaign_name"],
                ad_group_id=row["ad_group_id"],
                keyword_id=row["keyword_id"],
                keyword_text=row["keyword_text"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                success=bool(row["success"]),
                error_message=row["error_message"],
            ))
        return entries
    finally:
        conn.close()


def get_audit_log_count() -> int:
    """Get total number of audit log entries."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM audit_log").fetchone()
        return row["cnt"]
    finally:
        conn.close()


# Initialize DB on import
init_db()
