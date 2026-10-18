"""
Reports store: saved scan results for permalinks, the 24h cache, badges and re-scan deltas.

One table (`reports`) on Postgres (Supabase) via asyncpg, configured by DATABASE_URL. No user
data and no accounts — just the public scan result. Without DATABASE_URL the app runs on a
`NullReportStore` that saves nothing. `MemoryReportStore` backs the tests and local dev
(DATABASE_URL=memory://).
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)

REPORT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$"
)
MEMORY_URL = "memory://"


@dataclass
class StoredReport:
    """One saved scan. `payload` is the AnalyzeResponse JSON without report metadata."""

    id: str
    url: str
    domain: Optional[str]
    created_at: datetime
    overall: int
    payload: dict[str, Any] = field(default_factory=dict)


def new_report_id() -> str:
    """Short, unguessable, URL-safe id (8 chars) for a report permalink."""
    return secrets.token_urlsafe(6)


def is_report_id(value: str) -> bool:
    """True if `value` looks like a report id (checked before any query)."""
    return bool(REPORT_ID_PATTERN.match(value))


def normalize_url(url: str) -> str:
    """Canonical form of a scanned URL: lowercase scheme/host, no fragment, no trailing slash."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def domain_of(url: str) -> str:
    """Hostname of `url`, lowercased, without a leading `www.` — the badge and delta key."""
    host = (urlsplit(url.strip()).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def normalize_domain(domain: str) -> Optional[str]:
    """Badge path segment → domain key, or None if it isn't a plausible hostname."""
    value = domain.strip().lower()
    value = value[4:] if value.startswith("www.") else value
    return value if DOMAIN_PATTERN.match(value) else None


def scan_key(website_url: Optional[str], github_url: Optional[str]) -> str:
    """The `url` column: what was scanned, so the same input hits the 24h cache."""
    return " ".join(normalize_url(u) for u in (website_url, github_url) if u)


class ReportStore(Protocol):
    """What the API needs from the reports store."""

    enabled: bool

    async def save(
        self, url: str, domain: Optional[str], overall: int, payload: dict[str, Any]
    ) -> StoredReport:
        """Insert a new report and return it with its id and created_at."""

    async def get(self, report_id: str) -> Optional[StoredReport]:
        """The report with this id, or None."""

    async def latest_for_url(self, url: str, since: datetime) -> Optional[StoredReport]:
        """The newest report for this scan key created at or after `since`."""

    async def latest_for_domain(self, domain: str) -> Optional[StoredReport]:
        """The newest report for this domain, without its payload (for badges)."""

    async def previous_for_domain(self, domain: str, before: datetime) -> Optional[StoredReport]:
        """The newest report for this domain created strictly before `before`."""

    async def close(self) -> None:
        """Release connections."""


class NullReportStore:
    """Used when DATABASE_URL is unset: nothing is saved and every lookup misses."""

    enabled = False

    async def save(
        self, url: str, domain: Optional[str], overall: int, payload: dict[str, Any]
    ) -> StoredReport:
        """Return an unsaved report (no id is ever resolvable)."""
        return StoredReport("", url, domain, datetime.now(timezone.utc), overall, payload)

    async def get(self, report_id: str) -> Optional[StoredReport]:
        """Always None."""
        return None

    async def latest_for_url(self, url: str, since: datetime) -> Optional[StoredReport]:
        """Always None."""
        return None

    async def latest_for_domain(self, domain: str) -> Optional[StoredReport]:
        """Always None."""
        return None

    async def previous_for_domain(self, domain: str, before: datetime) -> Optional[StoredReport]:
        """Always None."""
        return None

    async def close(self) -> None:
        """Nothing to close."""


class MemoryReportStore:
    """In-process store for tests and local development. Lost on restart."""

    enabled = True

    def __init__(self) -> None:
        self.reports: list[StoredReport] = []

    async def save(
        self, url: str, domain: Optional[str], overall: int, payload: dict[str, Any]
    ) -> StoredReport:
        """Append a report with a fresh id."""
        report = StoredReport(
            new_report_id(), url, domain, datetime.now(timezone.utc), overall, payload
        )
        self.reports.append(report)
        return report

    async def get(self, report_id: str) -> Optional[StoredReport]:
        """Look up by id."""
        return next((r for r in self.reports if r.id == report_id), None)

    async def latest_for_url(self, url: str, since: datetime) -> Optional[StoredReport]:
        """Newest matching report at or after `since`."""
        return self._newest(r for r in self.reports if r.url == url and r.created_at >= since)

    async def latest_for_domain(self, domain: str) -> Optional[StoredReport]:
        """Newest report for the domain."""
        return self._newest(r for r in self.reports if r.domain == domain)

    async def previous_for_domain(self, domain: str, before: datetime) -> Optional[StoredReport]:
        """Newest report for the domain strictly before `before`."""
        return self._newest(
            r for r in self.reports if r.domain == domain and r.created_at < before
        )

    async def close(self) -> None:
        """Nothing to close."""

    @staticmethod
    def _newest(reports: Any) -> Optional[StoredReport]:
        return max(reports, key=lambda r: r.created_at, default=None)


_COLUMNS = "id, url, domain, created_at, overall"


class PostgresReportStore:
    """
    The `reports` table on Postgres via an asyncpg pool.

    Payloads go over the wire as JSON text (`$n::jsonb` / `payload::text`), so no codec setup
    is needed, and the statement cache is off so Supabase's transaction pooler works.
    """

    enabled = True

    def __init__(self, pool: Any) -> None:
        self.pool = pool

    @classmethod
    async def connect(cls, dsn: str) -> "PostgresReportStore":
        """Open a small pool to `dsn`."""
        import asyncpg  # imported here so the app runs without it when no DB is configured

        pool = await asyncpg.create_pool(
            dsn, min_size=0, max_size=5, statement_cache_size=0, command_timeout=10
        )
        return cls(pool)

    async def save(
        self, url: str, domain: Optional[str], overall: int, payload: dict[str, Any]
    ) -> StoredReport:
        """Insert a report; the database assigns created_at."""
        report_id = new_report_id()
        row = await self.pool.fetchrow(
            "INSERT INTO reports (id, url, domain, overall, payload) "
            "VALUES ($1, $2, $3, $4, $5::jsonb) RETURNING created_at",
            report_id,
            url,
            domain,
            overall,
            json.dumps(payload),
        )
        return StoredReport(report_id, url, domain, row["created_at"], overall, payload)

    async def get(self, report_id: str) -> Optional[StoredReport]:
        """Look up by primary key."""
        row = await self.pool.fetchrow(
            f"SELECT {_COLUMNS}, payload::text AS payload FROM reports WHERE id = $1", report_id
        )
        return self._report(row)

    async def latest_for_url(self, url: str, since: datetime) -> Optional[StoredReport]:
        """Newest report for the scan key since `since` (index: url, created_at desc)."""
        row = await self.pool.fetchrow(
            f"SELECT {_COLUMNS}, payload::text AS payload FROM reports "
            "WHERE url = $1 AND created_at >= $2 ORDER BY created_at DESC LIMIT 1",
            url,
            since,
        )
        return self._report(row)

    async def latest_for_domain(self, domain: str) -> Optional[StoredReport]:
        """Newest report for the domain, payload omitted (index: domain, created_at desc)."""
        row = await self.pool.fetchrow(
            f"SELECT {_COLUMNS} FROM reports WHERE domain = $1 "
            "ORDER BY created_at DESC LIMIT 1",
            domain,
        )
        return self._report(row)

    async def previous_for_domain(self, domain: str, before: datetime) -> Optional[StoredReport]:
        """Newest report for the domain strictly before `before`."""
        row = await self.pool.fetchrow(
            f"SELECT {_COLUMNS}, payload::text AS payload FROM reports "
            "WHERE domain = $1 AND created_at < $2 ORDER BY created_at DESC LIMIT 1",
            domain,
            before,
        )
        return self._report(row)

    async def close(self) -> None:
        """Close the pool."""
        await self.pool.close()

    @staticmethod
    def _report(row: Any) -> Optional[StoredReport]:
        if row is None:
            return None
        payload = row["payload"] if "payload" in row.keys() else None
        return StoredReport(
            id=row["id"],
            url=row["url"],
            domain=row["domain"],
            created_at=row["created_at"],
            overall=row["overall"],
            payload=json.loads(payload) if payload else {},
        )


async def create_store(database_url: Optional[str]) -> ReportStore:
    """
    The store for this process: `NullReportStore` when DATABASE_URL is unset or invalid.

    The Postgres pool connects lazily, so a database that is down at boot (or later) doesn't
    stop the app: reads miss and saves fail softly until it's back (see reports.py).
    """
    if not database_url:
        logger.info("DATABASE_URL not set — reports won't be saved")
        return NullReportStore()
    if database_url == MEMORY_URL:
        logger.info("Using the in-memory reports store (lost on restart)")
        return MemoryReportStore()
    try:
        return await PostgresReportStore.connect(database_url)
    except Exception:
        logger.exception("Couldn't connect to the reports database — reports won't be saved")
        return NullReportStore()
