"""Builders for SiteContext fixtures used by the check tests."""

from __future__ import annotations

from typing import Optional

from site_fetcher import FetchedPage, SiteContext

ORIGIN = "https://shop.example"


def page(
    html: str = "",
    path: str = "/",
    status: int = 200,
    content_type: str = "text/html; charset=utf-8",
    elapsed_ms: int = 300,
    headers: Optional[dict[str, str]] = None,
) -> FetchedPage:
    """A fetched page at ORIGIN + path."""
    all_headers = {"content-type": content_type, **(headers or {})}
    return FetchedPage(
        url=ORIGIN + path,
        status=status,
        headers=all_headers,
        text=html,
        elapsed_ms=elapsed_ms,
        size_bytes=len(html.encode()),
    )


def ctx(
    body: str = "",
    head: str = "",
    html_attrs: str = 'lang="en"',
    pages: Optional[dict[str, FetchedPage]] = None,
    probe: Optional[FetchedPage] = None,
    **fields: object,
) -> SiteContext:
    """A SiteContext whose homepage is a minimal HTML document with `head` and `body`."""
    html = f"<!doctype html><html {html_attrs}><head>{head}</head><body>{body}</body></html>"
    context = SiteContext(url=ORIGIN + "/", homepage=page(html), pages=pages or {})
    context.bot_probe = probe if probe is not None else page(html)
    for key, value in fields.items():
        setattr(context, key, value)
    return context


def words(n: int, word: str = "bread") -> str:
    """A run of n words."""
    return " ".join([word] * n)
