"""Tests for the SSRF guard and rate limiter."""

import httpx
import pytest
from fastapi import HTTPException

from safety import RateLimiter, assert_public_url, check_outbound_request


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost:8000/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://0.0.0.0/",
        "ftp://example.com/",
        "file:///etc/passwd",
    ],
)
async def test_rejects_non_public_urls(url: str) -> None:
    with pytest.raises(HTTPException) as exc:
        await assert_public_url(url)
    assert exc.value.status_code == 400


async def test_accepts_public_ip() -> None:
    await assert_public_url("https://1.1.1.1/")


async def test_redirect_hop_into_private_network_is_blocked() -> None:
    with pytest.raises(HTTPException):
        await check_outbound_request(httpx.Request("GET", "http://127.0.0.1/admin"))


def test_rate_limiter_blocks_after_limit_and_recovers() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("ip", now=0)
    assert limiter.allow("ip", now=1)
    assert not limiter.allow("ip", now=2)
    assert limiter.allow("other-ip", now=2)
    assert limiter.allow("ip", now=61)


def test_rate_limiter_forgets_expired_clients() -> None:
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.allow("old", now=0)
    limiter._prune(now=120)
    assert "old" not in limiter._hits
