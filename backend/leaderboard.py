"""
Public leaderboard: measured AI-readiness scores for a fixed list of well-known sites.

Scores come from the deterministic audit only (fetch + checks) — no LLM call, so building
the leaderboard costs nothing in Groq usage. The snapshot is a JSON file built offline:

    python leaderboard.py                    # scan every site, write data/leaderboard.json
    python leaderboard.py --only stripe.com  # rescan one site and merge it into the file

Only the curated LEADERBOARD_SITES appear on the board, never sites users scanned.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import statistics
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_SNAPSHOT_PATH = Path(__file__).parent / "data" / "leaderboard.json"
SCAN_CONCURRENCY = 3

# (domain, category). Homepages of well-known products, spread across industries.
LEADERBOARD_SITES: tuple[tuple[str, str], ...] = (
    ("openai.com", "AI"),
    ("anthropic.com", "AI"),
    ("perplexity.ai", "AI"),
    ("huggingface.co", "AI"),
    ("mistral.ai", "AI"),
    ("cohere.com", "AI"),
    ("stripe.com", "Developer tools"),
    ("github.com", "Developer tools"),
    ("vercel.com", "Developer tools"),
    ("supabase.com", "Developer tools"),
    ("cloudflare.com", "Developer tools"),
    ("twilio.com", "Developer tools"),
    ("postman.com", "Developer tools"),
    ("netlify.com", "Developer tools"),
    ("python.org", "Developer tools"),
    ("notion.com", "SaaS"),
    ("slack.com", "SaaS"),
    ("figma.com", "SaaS"),
    ("linear.app", "SaaS"),
    ("atlassian.com", "SaaS"),
    ("hubspot.com", "SaaS"),
    ("zoom.com", "SaaS"),
    ("dropbox.com", "SaaS"),
    ("canva.com", "SaaS"),
    ("shopify.com", "E-commerce"),
    ("amazon.com", "E-commerce"),
    ("etsy.com", "E-commerce"),
    ("ebay.com", "E-commerce"),
    ("ikea.com", "E-commerce"),
    ("bestbuy.com", "E-commerce"),
    ("nike.com", "E-commerce"),
    ("squarespace.com", "Website builders"),
    ("wix.com", "Website builders"),
    ("webflow.com", "Website builders"),
    ("wordpress.com", "Website builders"),
    ("framer.com", "Website builders"),
    ("nytimes.com", "News & media"),
    ("theguardian.com", "News & media"),
    ("bbc.com", "News & media"),
    ("reuters.com", "News & media"),
    ("theverge.com", "News & media"),
    ("wikipedia.org", "News & media"),
    ("paypal.com", "Finance"),
    ("wise.com", "Finance"),
    ("revolut.com", "Finance"),
    ("coinbase.com", "Finance"),
    ("robinhood.com", "Finance"),
    ("airbnb.com", "Travel"),
    ("booking.com", "Travel"),
    ("expedia.com", "Travel"),
    ("tripadvisor.com", "Travel"),
    ("duolingo.com", "Education & nonprofit"),
    ("khanacademy.org", "Education & nonprofit"),
    ("coursera.org", "Education & nonprofit"),
    ("mozilla.org", "Education & nonprofit"),
    ("redcross.org", "Education & nonprofit"),
)


class LeaderboardEntry(BaseModel):
    """One site's measured score at snapshot time."""

    domain: str
    url: str
    category: str
    overall: int
    grade: str
    categories: dict[str, Optional[int]]  # category id → sub-score (None when n/a)
    has_llms_txt: bool
    blocked_answer_bots: list[str]  # search/user-facing AI bots robots.txt blocks
    critical_failures: list[str]
    scanned_at: str


class LeaderboardFailure(BaseModel):
    """A site that couldn't be scanned for this snapshot (blocked us, timed out, …)."""

    domain: str
    error: str


class LeaderboardSnapshot(BaseModel):
    """The file written by `python leaderboard.py`."""

    generated_at: str
    entries: list[LeaderboardEntry]
    failed: list[LeaderboardFailure] = []


class LeaderboardStats(BaseModel):
    """Headline numbers for the "state of AI readiness" summary."""

    sites: int
    average: int
    median: int
    with_llms_txt_pct: int
    blocking_answer_bots_pct: int


class LeaderboardResponse(BaseModel):
    """Response body for GET /leaderboard. Entries are ranked best first."""

    generated_at: Optional[str]
    stats: Optional[LeaderboardStats]
    categories: list[str]
    entries: list[LeaderboardEntry]
    failed: list[LeaderboardFailure] = []


def failure_reason(detail: str) -> str:
    """Turn a scan error into a short public reason (a firewall block is itself a finding)."""
    status = re.search(r"returned (\d{3})", detail)
    if status and status.group(1) in ("401", "403", "429", "503"):
        return f"Blocks automated visitors (HTTP {status.group(1)})"
    if status:
        return f"Homepage returned HTTP {status.group(1)}"
    if "Timed out" in detail:
        return "Timed out"
    return "Couldn't be scanned"


async def measure_site(domain: str, category: str) -> LeaderboardEntry:
    """Fetch a site and run the deterministic audit. No LLM call. Raises on fetch failure."""
    from checks import run_audit  # imported lazily so the API process stays light at startup
    from site_fetcher import fetch_site

    ctx = await fetch_site(f"https://{domain}/")
    audit = run_audit(ctx)
    llms = next((c for c in audit.checks if c.id == "llms_txt"), None)
    return LeaderboardEntry(
        domain=domain,
        url=ctx.url,
        category=category,
        overall=audit.overall,
        grade=audit.grade,
        categories={c.id: c.score for c in audit.categories},
        has_llms_txt=bool(llms and llms.status == "pass"),
        blocked_answer_bots=[
            a.bot for a in audit.crawler_access if a.purpose != "training" and a.status == "blocked"
        ],
        critical_failures=audit.critical_failures,
        scanned_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


async def build_snapshot(
    sites: tuple[tuple[str, str], ...], concurrency: int = SCAN_CONCURRENCY
) -> LeaderboardSnapshot:
    """Scan `sites` a few at a time and collect entries and failures."""
    semaphore = asyncio.Semaphore(concurrency)

    async def scan(domain: str, category: str) -> LeaderboardEntry | LeaderboardFailure:
        async with semaphore:
            try:
                entry = await measure_site(domain, category)
                logger.info("%-20s %3d %s", domain, entry.overall, entry.grade)
                return entry
            except HTTPException as e:
                logger.warning("%-20s failed: %s", domain, e.detail)
                return LeaderboardFailure(domain=domain, error=failure_reason(str(e.detail)))
            except Exception:  # one bad site must not abort the whole batch
                logger.exception("%-20s crashed", domain)
                return LeaderboardFailure(domain=domain, error=failure_reason(""))

    results = await asyncio.gather(*(scan(d, c) for d, c in sites))
    return LeaderboardSnapshot(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        entries=[r for r in results if isinstance(r, LeaderboardEntry)],
        failed=[r for r in results if isinstance(r, LeaderboardFailure)],
    )


def merge_snapshots(old: LeaderboardSnapshot, new: LeaderboardSnapshot) -> LeaderboardSnapshot:
    """Replace the rescanned domains in `old`; a failed rescan keeps the old score."""
    rescanned = {e.domain for e in new.entries}
    newly_failed = {f.domain for f in new.failed}
    entries = [e for e in old.entries if e.domain not in rescanned] + new.entries
    kept = {e.domain for e in entries}
    failed = [f for f in old.failed if f.domain not in rescanned | newly_failed]
    failed += [f for f in new.failed if f.domain not in kept]
    return LeaderboardSnapshot(generated_at=new.generated_at, entries=entries, failed=failed)


def compute_stats(entries: list[LeaderboardEntry]) -> Optional[LeaderboardStats]:
    """Headline numbers across all entries, or None for an empty board."""
    if not entries:
        return None
    scores = [e.overall for e in entries]

    def pct(count: int) -> int:
        return round(100 * count / len(entries))

    return LeaderboardStats(
        sites=len(entries),
        average=round(statistics.mean(scores)),
        median=round(statistics.median(scores)),
        with_llms_txt_pct=pct(sum(e.has_llms_txt for e in entries)),
        blocking_answer_bots_pct=pct(sum(bool(e.blocked_answer_bots) for e in entries)),
    )


def snapshot_path() -> Path:
    """Where the snapshot lives (LEADERBOARD_PATH overrides the bundled file)."""
    return Path(os.getenv("LEADERBOARD_PATH", str(DEFAULT_SNAPSHOT_PATH)))


@lru_cache(maxsize=1)
def load_snapshot(path: Path) -> Optional[LeaderboardSnapshot]:
    """Read the snapshot once per process. None if the file is missing or invalid."""
    try:
        return LeaderboardSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("No leaderboard snapshot at %s", path)
    except (ValidationError, ValueError):
        logger.exception("Leaderboard snapshot at %s is invalid", path)
    return None


def leaderboard_response(snapshot: Optional[LeaderboardSnapshot]) -> LeaderboardResponse:
    """Rank entries (score desc, then domain) and attach headline stats."""
    if snapshot is None:
        return LeaderboardResponse(
            generated_at=None, stats=None, categories=[], entries=[], failed=[]
        )
    entries = sorted(snapshot.entries, key=lambda e: (-e.overall, e.domain))
    order = list(dict.fromkeys(category for _, category in LEADERBOARD_SITES))
    present = {e.category for e in entries}
    return LeaderboardResponse(
        generated_at=snapshot.generated_at,
        stats=compute_stats(entries),
        categories=[c for c in order if c in present],
        entries=entries,
        failed=sorted(snapshot.failed, key=lambda f: f.domain),
    )


router = APIRouter()


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard() -> LeaderboardResponse:
    """The public leaderboard, from the bundled snapshot (no scanning at request time)."""
    return leaderboard_response(load_snapshot(snapshot_path()))


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Build the AgentReady leaderboard snapshot.")
    parser.add_argument("--out", type=Path, default=snapshot_path())
    parser.add_argument("--only", nargs="+", metavar="DOMAIN", help="Rescan just these domains")
    parser.add_argument("--concurrency", type=int, default=SCAN_CONCURRENCY)
    args = parser.parse_args()

    sites = LEADERBOARD_SITES
    if args.only:
        known = dict(LEADERBOARD_SITES)
        unknown = [d for d in args.only if d not in known]
        if unknown:
            parser.error(f"Not in LEADERBOARD_SITES: {', '.join(unknown)}")
        sites = tuple((d, known[d]) for d in args.only)

    logger.info("Scanning %d sites (no LLM calls, $0 Groq cost)", len(sites))
    snapshot = await build_snapshot(sites, args.concurrency)
    if args.only and args.out.exists():
        old = LeaderboardSnapshot.model_validate_json(args.out.read_text(encoding="utf-8"))
        snapshot = merge_snapshots(old, snapshot)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    logger.info(
        "Wrote %s: %d sites scored, %d failed",
        args.out, len(snapshot.entries), len(snapshot.failed),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main())
