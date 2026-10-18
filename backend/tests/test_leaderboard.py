"""Tests for the public leaderboard: measuring, merging, stats and the API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import checks
import leaderboard
import site_fetcher
from leaderboard import (
    LEADERBOARD_SITES,
    LeaderboardEntry,
    LeaderboardFailure,
    LeaderboardSnapshot,
    build_snapshot,
    compute_stats,
    leaderboard_response,
    load_snapshot,
    measure_site,
    merge_snapshots,
)
from main import app
from models import Audit, CategoryScore, CheckResult, CrawlerAccess


def entry(domain: str, overall: int, llms: bool = False, blocked: tuple = ()) -> LeaderboardEntry:
    return LeaderboardEntry(
        domain=domain,
        url=f"https://{domain}/",
        category="SaaS",
        overall=overall,
        grade="B",
        categories={"crawler": overall},
        has_llms_txt=llms,
        blocked_answer_bots=list(blocked),
        critical_failures=[],
        scanned_at="2026-10-18T00:00:00+00:00",
    )


def snapshot(*entries: LeaderboardEntry, failed: tuple = ()) -> LeaderboardSnapshot:
    return LeaderboardSnapshot(
        generated_at="2026-10-18T00:00:00+00:00", entries=list(entries), failed=list(failed)
    )


def test_site_list_has_no_duplicates() -> None:
    domains = [d for d, _ in LEADERBOARD_SITES]
    assert len(domains) == len(set(domains))


async def test_measure_site_uses_only_the_deterministic_audit(monkeypatch) -> None:
    fetched: list[str] = []

    async def fake_fetch(url: str) -> site_fetcher.SiteContext:
        fetched.append(url)
        return site_fetcher.SiteContext(url="https://www.acme.test/")

    fake_audit = Audit(
        overall=72,
        grade="C",
        categories=[
            CategoryScore(id="crawler", label="", description="", score=90,
                          passed=1, warned=0, failed=0),
            CategoryScore(id="developer", label="", description="", score=None,
                          passed=0, warned=0, failed=0),
        ],
        checks=[CheckResult(id="llms_txt", category="agent", title="", status="pass",
                            weight=1, evidence="", why="")],
        crawler_access=[
            CrawlerAccess(bot="GPTBot", owner="OpenAI", purpose="training",
                          status="blocked", detail=""),
            CrawlerAccess(bot="PerplexityBot", owner="Perplexity", purpose="search",
                          status="blocked", detail=""),
            CrawlerAccess(bot="ChatGPT-User", owner="OpenAI", purpose="user",
                          status="allowed", detail=""),
        ],
        pages_scanned=[],
    )
    monkeypatch.setattr(site_fetcher, "fetch_site", fake_fetch)
    monkeypatch.setattr(checks, "run_audit", lambda ctx: fake_audit)

    result = await measure_site("acme.test", "SaaS")

    assert fetched == ["https://acme.test/"]
    assert result.url == "https://www.acme.test/"
    assert (result.overall, result.grade) == (72, "C")
    assert result.categories == {"crawler": 90, "developer": None}
    assert result.has_llms_txt
    assert result.blocked_answer_bots == ["PerplexityBot"]  # training bots don't count


async def test_build_snapshot_keeps_going_when_a_site_fails(monkeypatch) -> None:
    async def fake_measure(domain: str, category: str) -> LeaderboardEntry:
        if domain == "down.test":
            raise HTTPException(status_code=400, detail="The site returned 403.")
        if domain == "boom.test":
            raise RuntimeError("unexpected")
        return entry(domain, 50)

    monkeypatch.setattr(leaderboard, "measure_site", fake_measure)
    result = await build_snapshot(
        (("ok.test", "SaaS"), ("down.test", "SaaS"), ("boom.test", "SaaS")), concurrency=2
    )

    assert [e.domain for e in result.entries] == ["ok.test"]
    assert {f.domain: f.error for f in result.failed} == {
        "down.test": "Blocks automated visitors (HTTP 403)",
        "boom.test": "Couldn't be scanned",
    }


def test_merge_replaces_rescanned_sites_and_keeps_old_score_on_failure() -> None:
    old = snapshot(entry("a.test", 40), entry("b.test", 50),
                   failed=(LeaderboardFailure(domain="c.test", error="timeout"),))
    new = snapshot(entry("a.test", 80), entry("c.test", 60),
                   failed=(LeaderboardFailure(domain="b.test", error="403"),))

    merged = merge_snapshots(old, new)

    scores = {e.domain: e.overall for e in merged.entries}
    assert scores == {"a.test": 80, "b.test": 50, "c.test": 60}
    assert merged.failed == []  # b kept its old score; c now succeeded


def test_stats_and_ranking() -> None:
    board = leaderboard_response(snapshot(
        entry("low.test", 30, blocked=("PerplexityBot",)),
        entry("high.test", 90, llms=True),
        entry("mid.test", 60),
        entry("also-high.test", 90),
    ))

    assert [e.domain for e in board.entries] == ["also-high.test", "high.test", "mid.test",
                                                 "low.test"]
    assert board.stats.model_dump() == {
        "sites": 4, "average": 68, "median": 75,
        "with_llms_txt_pct": 25, "blocking_answer_bots_pct": 25,
    }
    assert board.categories == ["SaaS"]
    assert compute_stats([]) is None


def test_endpoint_serves_the_snapshot_file(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "leaderboard.json"
    path.write_text(snapshot(entry("a.test", 70)).model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("LEADERBOARD_PATH", str(path))
    load_snapshot.cache_clear()

    body = TestClient(app).get("/leaderboard").json()

    assert body["entries"][0]["domain"] == "a.test"
    assert body["stats"]["sites"] == 1
    load_snapshot.cache_clear()


@pytest.mark.parametrize("content", [None, "not json"])
def test_endpoint_is_empty_without_a_valid_snapshot(tmp_path: Path, monkeypatch,
                                                    content: str) -> None:
    path = tmp_path / "leaderboard.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("LEADERBOARD_PATH", str(path))
    load_snapshot.cache_clear()

    response = TestClient(app).get("/leaderboard")

    assert response.status_code == 200
    assert response.json() == {"generated_at": None, "stats": None, "categories": [],
                               "entries": [], "failed": []}
    load_snapshot.cache_clear()


@pytest.mark.parametrize("detail,reason", [
    ("The site returned 403: it turns away automated visitors.",
     "Blocks automated visitors (HTTP 403)"),
    ("The site returned 404. Check the address and try again.", "Homepage returned HTTP 404"),
    ("Timed out connecting to https://x.test/.", "Timed out"),
    ("Could not reach https://x.test/.", "Couldn't be scanned"),
])
def test_failure_reason(detail: str, reason: str) -> None:
    assert leaderboard.failure_reason(detail) == reason
