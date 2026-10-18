"""
Report routes: scan-or-cache (/analyze, /compare), permalinks, badges and social previews.

Each fresh scan is saved to the reports store and returned with its `report_id`; a scan of
the same input within 24h returns the saved report instead (no crawl, no LLM call). Every
report carries a delta against the previous report for its domain.
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from delta import compute_delta
from models import (
    REPORT_META_FIELDS,
    AnalyzeRequest,
    AnalyzeResponse,
    Audit,
    CompareRequest,
    CompareResponse,
    ReportDelta,
)
from safety import enforce_compare_rate_limit, enforce_rate_limit
from share_images import badge_svg, og_image_png
from store import (
    NullReportStore,
    ReportStore,
    StoredReport,
    domain_of,
    is_report_id,
    normalize_domain,
    scan_key,
)

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=24)
BADGE_MAX_AGE = 3600
OG_MAX_AGE = 7 * 24 * 3600  # a report never changes once saved

Scanner = Callable[[Optional[str], Optional[str]], Awaitable[AnalyzeResponse]]

router = APIRouter()


async def _run_scan(website_url: Optional[str], github_url: Optional[str]) -> AnalyzeResponse:
    from scan import run_scan  # imported lazily: llm_analyzer builds its Groq client on import

    return await run_scan(website_url, github_url)


def get_scanner() -> Scanner:
    """Dependency: the function that runs one full analysis (overridden in tests)."""
    return _run_scan


def get_store(request: Request) -> ReportStore:
    """Dependency: the process-wide reports store (a NullReportStore if none was set up)."""
    return getattr(request.app.state, "store", None) or NullReportStore()


async def _quietly(lookup: Awaitable[Optional[StoredReport]]) -> Optional[StoredReport]:
    """Run a store read; a database error is logged and treated as a miss, never a 500."""
    try:
        return await lookup
    except Exception:
        logger.exception("Reports store lookup failed")
        return None


async def _delta_for(
    store: ReportStore, report: AnalyzeResponse, stored: StoredReport
) -> Optional[ReportDelta]:
    if not stored.domain:
        return None
    previous = await _quietly(store.previous_for_domain(stored.domain, stored.created_at))
    if previous is None:
        return None
    try:
        previous_audit = Audit.model_validate(previous.payload["audit"])
    except (KeyError, ValidationError):
        logger.warning("Skipping delta: report %s has an unreadable audit", previous.id)
        return None
    return compute_delta(report.audit, previous_audit, previous.id, previous.created_at)


def _parse_payload(stored: StoredReport) -> AnalyzeResponse:
    try:
        return AnalyzeResponse.model_validate(stored.payload)
    except ValidationError:
        logger.warning("Report %s was saved in a format this version can't read", stored.id)
        raise HTTPException(
            status_code=410, detail="This report was saved by an older version of AgentReady."
        )


async def hydrate(
    store: ReportStore,
    stored: StoredReport,
    cached: bool,
    report: Optional[AnalyzeResponse] = None,
) -> AnalyzeResponse:
    """A saved report as an API response: payload plus id, timestamp, cache flag and delta."""
    report = report or _parse_payload(stored)
    delta = await _delta_for(store, report, stored)
    return report.model_copy(
        update={
            "report_id": stored.id,
            "created_at": stored.created_at,
            "cached": cached,
            "delta": delta,
        }
    )


async def scan_or_cached(
    store: ReportStore,
    scanner: Scanner,
    website_url: Optional[str],
    github_url: Optional[str],
    refresh: bool = False,
) -> AnalyzeResponse:
    """
    The saved report for this input from the last 24h, or a fresh scan that gets saved.

    `refresh` (Re-scan) skips the cache. A failed save still returns the scan, just without
    a report_id.
    """
    key = scan_key(website_url, github_url)
    now = datetime.now(timezone.utc)

    if store.enabled and not refresh:
        hit = await _quietly(store.latest_for_url(key, now - CACHE_TTL))
        if hit is not None:
            try:
                logger.info("Serving cached report %s for %s", hit.id, key)
                return await hydrate(store, hit, cached=True)
            except HTTPException:
                pass  # unreadable old report: scan again

    report = await scanner(website_url, github_url)
    if not store.enabled:
        return report.model_copy(update={"created_at": now})

    domain = domain_of(website_url) if website_url else None
    payload: dict[str, Any] = report.model_dump(mode="json", exclude=REPORT_META_FIELDS)
    try:
        stored = await store.save(key, domain, report.audit.overall, payload)
    except Exception:
        logger.exception("Couldn't save report for %s", key)
        return report.model_copy(update={"created_at": now})
    return await hydrate(store, stored, cached=False, report=report)


@router.post(
    "/analyze", response_model=AnalyzeResponse, dependencies=[Depends(enforce_rate_limit)]
)
async def analyze(
    request: AnalyzeRequest,
    store: ReportStore = Depends(get_store),
    scanner: Scanner = Depends(get_scanner),
) -> AnalyzeResponse:
    """Scan a website and/or repo (or return the same input's report from the last 24h)."""
    website_url = str(request.website_url) if request.website_url else None
    github_url = str(request.github_url) if request.github_url else None
    return await scan_or_cached(store, scanner, website_url, github_url, request.refresh)


@router.post(
    "/compare",
    response_model=CompareResponse,
    dependencies=[Depends(enforce_compare_rate_limit)],
)
async def compare(
    request: CompareRequest,
    store: ReportStore = Depends(get_store),
    scanner: Scanner = Depends(get_scanner),
) -> CompareResponse:
    """Scan two websites in parallel (one LLM call each) and return both reports."""
    urls = [str(u) for u in request.website_urls]
    if scan_key(urls[0], None) == scan_key(urls[1], None):
        raise HTTPException(status_code=400, detail="Pick two different sites to compare.")

    results = await asyncio.gather(
        *(scan_or_cached(store, scanner, url, None) for url in urls), return_exceptions=True
    )
    for url, result in zip(urls, results):
        if isinstance(result, HTTPException):
            raise HTTPException(
                status_code=result.status_code, detail=f"{domain_of(url)}: {result.detail}"
            )
        if isinstance(result, BaseException):
            raise result
    return CompareResponse(reports=list(results))  # type: ignore[arg-type]


async def _saved_report(store: ReportStore, report_id: str) -> StoredReport:
    stored = await _quietly(store.get(report_id)) if is_report_id(report_id) else None
    if stored is None:
        raise HTTPException(status_code=404, detail="That report doesn't exist or has expired.")
    return stored


@router.get("/reports/{report_id}", response_model=AnalyzeResponse)
async def get_report(report_id: str, store: ReportStore = Depends(get_store)) -> AnalyzeResponse:
    """A saved report by id (the /r/:id permalink), with its delta against the one before."""
    return await hydrate(store, await _saved_report(store, report_id), cached=True)


@router.get("/badge/{domain}.svg")
async def badge(domain: str, store: ReportStore = Depends(get_store)) -> Response:
    """README badge with the latest score for a domain ("not scanned" if there's none)."""
    key = normalize_domain(domain)
    if key is None:
        raise HTTPException(status_code=400, detail="That doesn't look like a domain name.")
    latest = await _quietly(store.latest_for_domain(key))
    return Response(
        content=badge_svg(latest.overall if latest else None),
        media_type="image/svg+xml",
        headers={"Cache-Control": f"public, max-age={BADGE_MAX_AGE}"},
    )


def _display_domain(report: AnalyzeResponse) -> str:
    source = report.website_url or report.github_url or ""
    if report.website_url:
        return domain_of(source)
    return source.split("://", 1)[-1].rstrip("/")


@router.get("/og/{report_id}.png")
async def og_image(report_id: str, store: ReportStore = Depends(get_store)) -> Response:
    """1200×630 social preview card for a report."""
    stored = await _saved_report(store, report_id)
    report = _parse_payload(stored)
    png = await asyncio.to_thread(
        og_image_png, _display_domain(report), report.audit, stored.created_at
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": f"public, max-age={OG_MAX_AGE}, immutable"},
    )


@router.get("/share/{report_id}", response_class=HTMLResponse)
async def share_page(
    report_id: str, request: Request, store: ReportStore = Depends(get_store)
) -> HTMLResponse:
    """
    Open Graph / Twitter card HTML for a report, for link-preview bots (the frontend's
    middleware routes bot requests for /r/:id here). People are redirected to the permalink.
    """
    stored = await _saved_report(store, report_id)
    report = _parse_payload(stored)
    frontend = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    api_base = (os.getenv("PUBLIC_API_URL") or str(request.base_url)).rstrip("/")
    permalink = f"{frontend}/r/{stored.id}"
    image = f"{api_base}/og/{stored.id}.png"
    name = _display_domain(report)
    title = f"{name} scores {report.audit.overall}/100 for AI readiness"
    description = (
        f"Grade {report.audit.grade}. See how ChatGPT, Claude and Perplexity read {name} — "
        "measured checks with evidence and copy-paste fixes."
    )
    t, d, u, i = (html.escape(v, quote=True) for v in (title, description, permalink, image))
    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{t} · AgentReady</title>
<meta name="description" content="{d}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="AgentReady">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{u}">
<meta property="og:image" content="{i}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{i}">
<link rel="canonical" href="{u}">
<meta http-equiv="refresh" content="0; url={u}">
</head><body><a href="{u}">{t}</a></body></html>"""
    return HTMLResponse(page, headers={"Cache-Control": "public, max-age=3600"})
