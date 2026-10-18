"""Abuse protection for a public scanner: SSRF guard for outbound fetches and per-IP rate limit."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = ("http", "https")
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "10"))
RATE_LIMIT_WINDOW_SECONDS = 3600.0
MAX_TRACKED_CLIENTS = 10_000


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


async def assert_public_url(url: str) -> None:
    """
    Reject URLs that would make the server fetch something on a private network.

    Blocks non-http(s) schemes and any host that resolves to a loopback, private,
    link-local (cloud metadata), reserved or otherwise non-global address.
    Raises HTTPException(400) on rejection.

    Known gap: httpx resolves the host again when connecting, so a DNS-rebinding host
    could still flip to a private IP between check and connect.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Only public http(s) URLs can be scanned.")

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=f"Could not resolve {host}. Check the URL.")

    addresses = {info[4][0] for info in infos}
    if not addresses or not all(_is_public_ip(ip) for ip in addresses):
        logger.warning("Blocked non-public URL %s (resolved to %s)", url, sorted(addresses))
        raise HTTPException(status_code=400, detail="That URL points to a private network address.")


async def check_outbound_request(request: httpx.Request) -> None:
    """httpx request event hook: re-validates every hop, including redirects."""
    await assert_public_url(str(request.url))


class RateLimiter:
    """In-memory sliding-window limiter keyed by client IP. Resets on process restart."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record a hit for `key` and return False if it exceeds the limit."""
        now = time.monotonic() if now is None else now
        if len(self._hits) > MAX_TRACKED_CLIENTS:
            self._prune(now)
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def _prune(self, now: float) -> None:
        """Forget clients whose hits have all expired, so memory stays bounded."""
        stale = [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window_seconds]
        for key in stale:
            del self._hits[key]


_limiter = RateLimiter(RATE_LIMIT_PER_HOUR, RATE_LIMIT_WINDOW_SECONDS)


def client_ip(request: Request) -> str:
    """
    Best-effort client IP.

    Behind Render's proxy the real client is the last X-Forwarded-For entry (the one the
    proxy appended); earlier entries are client-controlled and can be spoofed.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: 429 once a client exceeds RATE_LIMIT_PER_HOUR scans."""
    if not _limiter.allow(client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail=f"You've hit the limit of {RATE_LIMIT_PER_HOUR} scans per hour. "
            "Please try again later.",
        )
