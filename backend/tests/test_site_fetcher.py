"""Tests for SiteContext building, against a mocked HTTP transport (no network)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

import site_fetcher
from site_fetcher import fetch_site, parse_sitemap_locs, select_key_pages
from tests.helpers import ORIGIN, ctx

HOMEPAGE = """<html><head><title>Shop</title></head><body>
<a href="/pricing">Pricing</a> <a href="/about-us">About</a> <a href="/blog/2020/a/b">Old</a>
<a href="https://other.example/contact">Elsewhere</a> <a href="mailto:x@y.z">Mail</a>
</body></html>"""

FILES = {
    "/": (200, "text/html", HOMEPAGE),
    "/robots.txt": (200, "text/plain", "User-agent: *\nAllow: /\nSitemap: /custom-sitemap.xml\n"),
    "/custom-sitemap.xml": (
        200, "application/xml",
        f"<urlset><url><loc>{ORIGIN}/faq</loc><lastmod>2026-01-01</lastmod></url></urlset>",
    ),
    "/llms.txt": (200, "text/plain", "# Shop\n\n> We sell things\n"),
    "/openapi.json": (200, "application/json", '{"openapi": "3.0.0"}'),
    "/pricing": (200, "text/html", "<p>$10/mo</p>"),
    "/about-us": (200, "text/html", "<p>About</p>"),
    "/faq": (200, "text/html", "<p>FAQ</p>"),
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host != "shop.example":
        return httpx.Response(404)
    if "GPTBot" in request.headers.get("user-agent", ""):
        return httpx.Response(403, text="Forbidden")
    status, content_type, body = FILES.get(
        request.url.path, (200, "text/html", "<html>catch-all SPA route</html>")
    )
    return httpx.Response(status, headers={"content-type": content_type}, text=body)


@pytest.fixture
def mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def allow(_: object) -> None:
        return None

    real_client = httpx.AsyncClient
    monkeypatch.setattr(site_fetcher, "assert_public_url", allow)
    monkeypatch.setattr(site_fetcher, "check_outbound_request", allow)
    monkeypatch.setattr(
        site_fetcher.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(_handler), **kw),
    )


async def test_fetch_site_builds_full_context(mocked: None) -> None:
    context = await fetch_site(ORIGIN + "/")
    assert context.has_website
    assert context.robots_txt.startswith("User-agent")
    assert context.sitemap_in_robots and context.sitemap_url.endswith("/custom-sitemap.xml")
    assert context.sitemap_urls == [ORIGIN + "/faq"] and context.sitemap_has_lastmod
    assert context.llms_txt.startswith("# Shop")
    assert context.llms_full_txt == ""  # catch-all HTML is not a file
    assert list(context.well_known) == ["/openapi.json"]
    assert context.bot_probe is not None and context.bot_probe.status == 403
    assert set(context.pages) == {"pricing", "about", "faq"}


async def test_unreachable_homepage_is_a_400(mocked: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(FILES, "/", (500, "text/html", "boom"))
    with pytest.raises(HTTPException) as exc:
        await fetch_site(ORIGIN + "/")
    assert exc.value.status_code == 400


def test_select_key_pages_prefers_shallow_same_origin_links() -> None:
    context = ctx(body=HOMEPAGE)
    selected = select_key_pages(context)
    assert selected["pricing"] == ORIGIN + "/pricing"
    assert selected["about"] == ORIGIN + "/about-us"
    assert "contact" not in selected  # other origin
    assert "blog" not in selected  # too deep


def test_parse_sitemap_locs() -> None:
    xml = "<urlset><url><loc> https://a.example/x </loc></url><url><loc>https://a.example/y</loc>"
    assert parse_sitemap_locs(xml) == ["https://a.example/x", "https://a.example/y"]


def test_select_key_pages_handles_locale_and_docs_prefixes() -> None:
    body = (
        '<a href="/docs/en/about-claude/pricing">Pricing</a>'
        '<a href="/docs/en/api/overview">API</a>'
        '<a href="/docs/en/build-with-claude/a/b/c/faq">Too deep</a>'
        '<a href="/de/kontakt">Kontakt</a> <a href="/en/contact">Contact</a>'
    )
    context = ctx(body=body)
    context.url = ORIGIN + "/docs/en/home"
    selected = select_key_pages(context)
    assert selected["pricing"] == ORIGIN + "/docs/en/about-claude/pricing"
    assert selected["docs"] == ORIGIN + "/docs/en/api/overview"
    assert selected["contact"] == ORIGIN + "/en/contact"
    assert "faq" not in selected


def test_select_key_pages_prefers_shallowest_match() -> None:
    body = '<a href="/docs/guides/start">Guide</a> <a href="/docs">Docs</a>'
    assert select_key_pages(ctx(body=body))["docs"] == ORIGIN + "/docs"


def test_select_key_pages_skips_section_roots_and_reuses_no_url() -> None:
    body = (
        '<a href="/docs">Docs root</a> <a href="/docs/en/about-claude/pricing">Pricing</a>'
        '<a href="/docs/en/about-claude/models">Models</a>'
    )
    context = ctx(body=body)
    context.url = ORIGIN + "/docs/en/home"
    selected = select_key_pages(context)
    assert "docs" not in selected  # /docs just redirects back to the scanned page
    assert selected["pricing"] == ORIGIN + "/docs/en/about-claude/pricing"
    assert selected["about"] == ORIGIN + "/docs/en/about-claude/models"


def test_select_key_pages_ignores_translations_of_the_start_page() -> None:
    context = ctx(body='<a href="/docs/de/home">Deutsch</a> <a href="/docs/de">DE</a>')
    context.url = ORIGIN + "/docs/en/home"
    assert select_key_pages(context) == {}
