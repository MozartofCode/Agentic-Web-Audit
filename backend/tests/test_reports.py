"""Tests for the reports store, the re-scan delta, and the report / badge / compare endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import store as store_module
from delta import compute_delta
from main import app
from models import (
    AIPreview,
    AnalyzeResponse,
    Artifacts,
    Audit,
    AuditBreakdown,
    AuditScore,
    CheckResult,
    FixPack,
)
from reports import get_scanner, get_store
from safety import RateLimiter, enforce_compare_rate_limit, enforce_rate_limit
from store import (
    MemoryReportStore,
    NullReportStore,
    PostgresReportStore,
    create_store,
    domain_of,
    normalize_domain,
    normalize_url,
    scan_key,
)

UTC = timezone.utc
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def check(check_id: str, status: str, title: Optional[str] = None) -> CheckResult:
    return CheckResult(
        id=check_id,
        category="agent",
        title=title or check_id.replace("_", " ").title(),
        status=status,  # type: ignore[arg-type]
        weight=5,
        evidence="",
        why="",
    )


def audit(overall: int, statuses: Optional[dict[str, str]] = None) -> Audit:
    return Audit(
        overall=overall,
        grade="C",
        categories=[],
        checks=[check(i, s) for i, s in (statuses or {}).items()],
        crawler_access=[],
        pages_scanned=["https://shop.example/"],
    )


def report(
    website_url: Optional[str] = "https://shop.example/",
    overall: int = 50,
    statuses: Optional[dict[str, str]] = None,
) -> AnalyzeResponse:
    return AnalyzeResponse(
        product_name="Shop",
        product_summary="A shop.",
        artifacts=Artifacts(llms_txt="# Shop", audit_md="", mcp_server_ts="", openapi_yaml=""),
        audit_score=AuditScore(
            score=10,
            breakdown=AuditBreakdown(
                has_api=False,
                has_openapi_spec=False,
                has_llms_txt=False,
                has_structured_docs=False,
                has_api_key_auth=False,
                has_webhook_support=False,
            ),
        ),
        audit=audit(overall, statuses),
        ai_preview=AIPreview(),
        fix_pack=FixPack(files=[]),
        website_url=website_url,
    )


class FakeScanner:
    """Stands in for the real pipeline (no network, no LLM). Scores come from `overalls`."""

    def __init__(self, overalls: Optional[list[int]] = None, statuses: Any = None) -> None:
        self.calls: list[tuple[Optional[str], Optional[str]]] = []
        self.overalls = overalls or [50]
        self.statuses = statuses or [{"llms_txt": "fail", "robots": "pass"}]

    async def __call__(
        self, website_url: Optional[str], github_url: Optional[str]
    ) -> AnalyzeResponse:
        i = min(len(self.calls), len(self.overalls) - 1)
        statuses = self.statuses[min(len(self.calls), len(self.statuses) - 1)]
        self.calls.append((website_url, github_url))
        return report(website_url, self.overalls[i], statuses)


async def _no_limit() -> None:
    return None


@pytest.fixture
def memory_store() -> MemoryReportStore:
    return MemoryReportStore()


def make_client(report_store: Any, scanner: Any) -> TestClient:
    app.dependency_overrides[get_store] = lambda: report_store
    app.dependency_overrides[get_scanner] = lambda: scanner
    app.dependency_overrides[enforce_rate_limit] = _no_limit
    app.dependency_overrides[enforce_compare_rate_limit] = _no_limit
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


# --- URL keys ---------------------------------------------------------------------------


def test_normalize_url_and_scan_key() -> None:
    assert normalize_url("HTTPS://Shop.Example/") == "https://shop.example"
    assert normalize_url("https://shop.example/docs/#top") == "https://shop.example/docs"
    assert normalize_url("https://shop.example/?a=1") == "https://shop.example?a=1"
    assert scan_key("https://shop.example/", None) == "https://shop.example"
    assert (
        scan_key("https://shop.example/", "https://github.com/o/r/")
        == "https://shop.example https://github.com/o/r"
    )


def test_domain_keys_drop_www() -> None:
    assert domain_of("https://WWW.Shop.Example/pricing") == "shop.example"
    assert normalize_domain("www.shop.example") == "shop.example"
    assert normalize_domain("shop.example") == "shop.example"
    for bad in ("localhost", "shop..example", "shop.example/x", "<script>", ""):
        assert normalize_domain(bad) is None


# --- Stores -----------------------------------------------------------------------------


async def test_memory_store_lookups(memory_store: MemoryReportStore) -> None:
    first = await memory_store.save("https://a.example", "a.example", 40, {"n": 1})
    second = await memory_store.save("https://a.example", "a.example", 60, {"n": 2})
    second.created_at = first.created_at + timedelta(minutes=5)
    await memory_store.save("https://b.example", "b.example", 90, {"n": 3})

    assert first.id != second.id
    assert (await memory_store.get(first.id)).payload == {"n": 1}
    assert await memory_store.get("missing") is None

    since = first.created_at - timedelta(hours=1)
    assert (await memory_store.latest_for_url("https://a.example", since)).id == second.id
    future = second.created_at + timedelta(seconds=1)
    assert await memory_store.latest_for_url("https://a.example", future) is None

    assert (await memory_store.latest_for_domain("a.example")).overall == 60
    previous = await memory_store.previous_for_domain("a.example", second.created_at)
    assert previous.id == first.id
    assert await memory_store.previous_for_domain("a.example", first.created_at) is None


async def test_null_store_saves_nothing() -> None:
    null = NullReportStore()
    saved = await null.save("https://a.example", "a.example", 40, {})
    assert not null.enabled and saved.id == ""
    assert await null.get(saved.id) is None
    assert await null.latest_for_domain("a.example") is None


class FakeRecord(dict):
    """asyncpg.Record supports both rec["col"] and rec.keys(); a dict does too."""


class FakePool:
    """Records every query and answers fetchrow from a queue."""

    def __init__(self, rows: list[Optional[dict]]) -> None:
        self.rows = rows
        self.queries: list[tuple[str, tuple]] = []
        self.closed = False

    async def fetchrow(self, sql: str, *args: Any) -> Optional[FakeRecord]:
        self.queries.append((sql, args))
        row = self.rows.pop(0)
        return FakeRecord(row) if row is not None else None

    async def close(self) -> None:
        self.closed = True


async def test_postgres_store_save_sends_json_and_reads_created_at() -> None:
    created = datetime(2026, 10, 18, 12, tzinfo=UTC)
    pool = FakePool([{"created_at": created}])
    saved = await PostgresReportStore(pool).save("https://a.example", "a.example", 72, {"x": [1]})

    sql, args = pool.queries[0]
    assert sql.startswith("INSERT INTO reports") and "$5::jsonb" in sql
    assert args[1:4] == ("https://a.example", "a.example", 72)
    assert json.loads(args[4]) == {"x": [1]}
    assert saved.id == args[0] and saved.created_at == created and saved.overall == 72


async def test_postgres_store_decodes_rows() -> None:
    created = datetime(2026, 10, 18, 12, tzinfo=UTC)
    row = {"id": "abcdefgh", "url": "u", "domain": "a.example", "created_at": created,
           "overall": 61, "payload": json.dumps({"audit": {}})}
    badge_row = {k: v for k, v in row.items() if k != "payload"}
    pool = FakePool([row, None, badge_row, row])
    pg = PostgresReportStore(pool)

    got = await pg.get("abcdefgh")
    assert got.payload == {"audit": {}} and got.domain == "a.example"
    assert await pg.latest_for_url("u", created) is None
    badge = await pg.latest_for_domain("a.example")
    assert badge.overall == 61 and badge.payload == {}
    assert "payload" not in pool.queries[2][0]  # the badge query never loads the payload
    previous = await pg.previous_for_domain("a.example", created)
    assert "created_at < $2" in pool.queries[3][0] and previous.id == "abcdefgh"

    await pg.close()
    assert pool.closed


async def test_create_store_picks_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(await create_store(None), NullReportStore)
    assert isinstance(await create_store(""), NullReportStore)
    assert isinstance(await create_store("memory://"), MemoryReportStore)

    async def unreachable(cls: Any, dsn: str) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(store_module.PostgresReportStore, "connect", classmethod(unreachable))
    assert isinstance(await create_store("postgresql://db.invalid/x"), NullReportStore)


# --- Delta ------------------------------------------------------------------------------


def test_delta_counts_points_and_flipped_checks() -> None:
    before = audit(40, {"llms_txt": "fail", "robots": "pass", "faq": "warn", "api": "na"})
    after = audit(
        55, {"llms_txt": "pass", "robots": "warn", "faq": "pass", "api": "pass", "new": "pass"}
    )
    when = datetime(2026, 10, 1, tzinfo=UTC)
    delta = compute_delta(after, before, "prev1234", when)

    assert delta.points == 15
    assert delta.previous_overall == 40 and delta.previous_report_id == "prev1234"
    assert delta.previous_created_at == when
    assert delta.now_passing == ["Llms Txt", "Faq"]  # n/a → pass and brand-new checks don't count
    assert delta.regressed == ["Robots"]


def test_delta_can_be_negative_and_empty() -> None:
    same = {"llms_txt": "fail"}
    delta = compute_delta(audit(30, same), audit(35, same), "p", datetime.now(UTC))
    assert delta.points == -5 and delta.now_passing == [] and delta.regressed == []


# --- POST /analyze ----------------------------------------------------------------------


def test_analyze_without_store_still_works() -> None:
    scanner = FakeScanner()
    res = make_client(NullReportStore(), scanner).post(
        "/analyze", json={"website_url": "https://shop.example"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] is None and body["created_at"] and body["cached"] is False
    assert len(scanner.calls) == 1


def test_analyze_saves_then_serves_cache(memory_store: MemoryReportStore) -> None:
    scanner = FakeScanner()
    client = make_client(memory_store, scanner)

    first = client.post("/analyze", json={"website_url": "https://shop.example"}).json()
    assert first["report_id"] and first["cached"] is False and first["delta"] is None
    saved = memory_store.reports[0]
    assert saved.url == "https://shop.example" and saved.domain == "shop.example"
    assert saved.overall == 50
    assert not {"report_id", "created_at", "cached", "delta"} & saved.payload.keys()

    again = client.post("/analyze", json={"website_url": "https://Shop.example/"}).json()
    assert again["report_id"] == first["report_id"] and again["cached"] is True
    assert len(scanner.calls) == 1  # no second crawl, no second LLM call


def test_cache_expires_after_24h(memory_store: MemoryReportStore) -> None:
    scanner = FakeScanner()
    client = make_client(memory_store, scanner)
    client.post("/analyze", json={"website_url": "https://shop.example"})
    memory_store.reports[0].created_at -= timedelta(hours=25)

    res = client.post("/analyze", json={"website_url": "https://shop.example"}).json()
    assert res["cached"] is False and len(scanner.calls) == 2


def test_rescan_skips_cache_and_reports_delta(memory_store: MemoryReportStore) -> None:
    scanner = FakeScanner(
        overalls=[40, 58],
        statuses=[{"llms_txt": "fail", "robots": "pass"}, {"llms_txt": "pass", "robots": "pass"}],
    )
    client = make_client(memory_store, scanner)
    first = client.post("/analyze", json={"website_url": "https://shop.example"}).json()
    memory_store.reports[0].created_at -= timedelta(minutes=1)

    second = client.post(
        "/analyze", json={"website_url": "https://www.shop.example", "refresh": True}
    ).json()
    assert len(scanner.calls) == 2 and second["report_id"] != first["report_id"]
    assert second["delta"]["points"] == 18
    assert second["delta"]["previous_report_id"] == first["report_id"]
    assert second["delta"]["now_passing"] == ["Llms Txt"]


def test_repo_only_scans_have_no_domain(memory_store: MemoryReportStore) -> None:
    client = make_client(memory_store, FakeScanner())
    res = client.post("/analyze", json={"github_url": "https://github.com/o/r"})
    assert res.status_code == 200
    assert memory_store.reports[0].domain is None
    assert memory_store.reports[0].url == "https://github.com/o/r"


class BrokenStore(MemoryReportStore):
    """A database that is down: every call raises."""

    async def save(self, *args: Any) -> Any:
        raise OSError("db down")

    async def latest_for_url(self, *args: Any) -> Any:
        raise OSError("db down")

    async def get(self, *args: Any) -> Any:
        raise OSError("db down")


def test_database_errors_never_break_a_scan() -> None:
    res = make_client(BrokenStore(), FakeScanner()).post(
        "/analyze", json={"website_url": "https://shop.example"}
    )
    assert res.status_code == 200 and res.json()["report_id"] is None


# --- GET /reports/{id} ------------------------------------------------------------------


def test_get_report_by_id(memory_store: MemoryReportStore) -> None:
    client = make_client(memory_store, FakeScanner())
    report_id = client.post("/analyze", json={"website_url": "https://shop.example"}).json()[
        "report_id"
    ]

    res = client.get(f"/reports/{report_id}")
    assert res.status_code == 200
    assert res.json()["report_id"] == report_id and res.json()["product_name"] == "Shop"
    assert client.get("/reports/doesnotexist").status_code == 404
    assert client.get("/reports/bad%20id!").status_code == 404


def test_old_unreadable_report_is_gone(memory_store: MemoryReportStore) -> None:
    saved = asyncio.run(memory_store.save("https://a.example", "a.example", 10, {"v": 0}))
    res = make_client(memory_store, FakeScanner()).get(f"/reports/{saved.id}")
    assert res.status_code == 410


# --- Badge, OG image, share page --------------------------------------------------------


def test_badge_shows_latest_score(memory_store: MemoryReportStore) -> None:
    client = make_client(memory_store, FakeScanner(overalls=[73]))

    empty = client.get("/badge/shop.example.svg")
    assert empty.status_code == 200 and "not scanned" in empty.text
    assert empty.headers["content-type"].startswith("image/svg+xml")

    client.post("/analyze", json={"website_url": "https://www.shop.example"})
    res = client.get("/badge/shop.example.svg")
    assert "AI-Ready · 73/100" in res.text and ">73<" in res.text
    assert "max-age" in res.headers["cache-control"]
    assert ">73<" in client.get("/badge/www.shop.example.svg").text
    assert client.get("/badge/not_a_domain.svg").status_code == 400


def test_og_image_is_a_png(memory_store: MemoryReportStore) -> None:
    client = make_client(memory_store, FakeScanner())
    report_id = client.post("/analyze", json={"website_url": "https://shop.example"}).json()[
        "report_id"
    ]
    res = client.get(f"/og/{report_id}.png")
    assert res.status_code == 200 and res.headers["content-type"] == "image/png"
    assert res.content.startswith(PNG_SIGNATURE)
    assert client.get("/og/missing1.png").status_code == 404


def test_share_page_has_open_graph_tags(
    memory_store: MemoryReportStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_URL", "https://agentready.example")
    monkeypatch.setenv("PUBLIC_API_URL", "https://api.agentready.example")
    client = make_client(memory_store, FakeScanner(overalls=[64]))
    report_id = client.post("/analyze", json={"website_url": "https://shop.example"}).json()[
        "report_id"
    ]

    page = client.get(f"/share/{report_id}").text
    assert f'content="https://api.agentready.example/og/{report_id}.png"' in page
    assert f'content="https://agentready.example/r/{report_id}"' in page
    assert "shop.example scores 64/100" in page
    assert 'name="twitter:card" content="summary_large_image"' in page


# --- POST /compare ----------------------------------------------------------------------


class ParallelScanner(FakeScanner):
    """Fails unless both scans are in flight at the same time."""

    def __init__(self) -> None:
        super().__init__(overalls=[30, 80])
        self.in_flight = 0
        self.both: Optional[asyncio.Event] = None  # made on the app's loop (Python 3.9)

    async def __call__(
        self, website_url: Optional[str], github_url: Optional[str]
    ) -> AnalyzeResponse:
        self.both = self.both or asyncio.Event()
        self.in_flight += 1
        if self.in_flight == 2:
            self.both.set()
        await asyncio.wait_for(self.both.wait(), timeout=2)
        return await super().__call__(website_url, github_url)


def test_compare_runs_both_sites_in_parallel(memory_store: MemoryReportStore) -> None:
    scanner = ParallelScanner()
    res = make_client(memory_store, scanner).post(
        "/compare", json={"website_urls": ["https://a.example", "https://b.example"]}
    )
    assert res.status_code == 200
    reports = res.json()["reports"]
    assert [r["website_url"] for r in reports] == ["https://a.example/", "https://b.example/"]
    assert all(r["report_id"] for r in reports) and len(memory_store.reports) == 2


def test_compare_validation(memory_store: MemoryReportStore) -> None:
    client = make_client(memory_store, FakeScanner())
    same = client.post(
        "/compare", json={"website_urls": ["https://a.example", "https://A.example/"]}
    )
    assert same.status_code == 400
    assert client.post("/compare", json={"website_urls": ["https://a.example"]}).status_code == 422


def test_compare_names_the_site_that_failed(memory_store: MemoryReportStore) -> None:
    async def scanner(website_url: Optional[str], github_url: Optional[str]) -> AnalyzeResponse:
        if "b.example" in (website_url or ""):
            raise HTTPException(status_code=400, detail="Could not resolve b.example.")
        return report(website_url)

    res = make_client(memory_store, scanner).post(
        "/compare", json={"website_urls": ["https://a.example", "https://b.example"]}
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "b.example: Could not resolve b.example."


def test_compare_costs_two_scans() -> None:
    limiter = RateLimiter(limit=3, window_seconds=3600)
    assert limiter.allow("ip", now=0, cost=2)
    assert not limiter.allow("ip", now=1, cost=2)  # 2 + 2 > 3
    assert limiter.allow("ip", now=2, cost=1)
