"""Builds a SiteContext: everything the audit checks need, fetched once with an SSRF-safe client."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Comment
from fastapi import HTTPException

from crawler import (
    MAX_BODY_CHARS,
    blocked_ai_bots,
    find_api_links,
    get_meta_description,
    looks_like_llms_txt,
)
from safety import assert_public_url, check_outbound_request

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 8.0
KEY_PAGES_BUDGET_SECONDS = 12.0
MAX_CONCURRENT_FETCHES = 4
MAX_KEY_PAGES = 8
MAX_HTML_BYTES = 3_000_000
MAX_TEXT_FILE_BYTES = 500_000
MAX_SITEMAP_URLS = 500

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 AgentReady/0.2"
)
# Same UA string OpenAI's crawler sends, to see whether a CDN/WAF treats AI bots differently.
AI_BOT_PROBE_UA = (
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2; "
    "+https://openai.com/gptbot"
)

WELL_KNOWN_PATHS = (
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/.well-known/openapi.json",
    "/.well-known/mcp.json",
    "/.well-known/mcp/server-card.json",
    "/.well-known/ai-plugin.json",
    "/.well-known/api-catalog",
)

# Page kind → URL path keywords, in priority order. One page per kind.
KEY_PAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing": ("pricing", "plans", "price"),
    "about": ("about", "company", "who-we-are"),
    "contact": ("contact",),
    "faq": ("faq", "help", "support"),
    "docs": ("docs", "documentation", "developers", "developer", "api"),
    "features": ("features", "product", "services", "solutions"),
    "blog": ("blog", "news", "articles"),
    "menu": ("menu", "shop", "store", "products"),
}

NON_CONTENT_TAGS = {"script", "style", "noscript", "template", "head", "title", "meta", "svg"}

CHALLENGE_MARKERS = (
    "cf-chl-",
    "challenge-platform",
    "just a moment...",
    "attention required! | cloudflare",
    "_incapsula_resource",
    "px-captcha",
    "access denied",
)


@dataclass
class FetchedPage:
    """One fetched URL. `text` is the decoded body, truncated to a size cap."""

    url: str
    status: int
    headers: dict[str, str]
    text: str
    elapsed_ms: int
    size_bytes: int

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def is_html(self) -> bool:
        return "html" in self.headers.get("content-type", "").lower()

    def plain_text(self) -> str:
        """Body if this is a successful non-HTML file (SPAs answer every path with HTML)."""
        return self.text if self.ok and not self.is_html else ""


@dataclass
class SiteContext:
    """Everything fetched for one scan. Checks are pure functions over this object."""

    url: str = ""
    homepage: Optional[FetchedPage] = None
    robots_txt: str = ""
    sitemap_url: str = ""
    sitemap_in_robots: bool = False
    sitemap_urls: list[str] = field(default_factory=list)
    sitemap_has_lastmod: bool = False
    llms_txt: str = ""
    llms_full_txt: str = ""
    llms_txt_status: Optional[int] = None
    well_known: dict[str, str] = field(default_factory=dict)
    bot_probe: Optional[FetchedPage] = None
    pages: dict[str, FetchedPage] = field(default_factory=dict)
    github: dict = field(default_factory=dict)
    llm_says_api: bool = False
    _soups: dict[str, BeautifulSoup] = field(default_factory=dict, repr=False)
    _texts: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def has_website(self) -> bool:
        return self.homepage is not None

    @property
    def origin(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def soup(self, page: FetchedPage) -> BeautifulSoup:
        """Parsed raw HTML for a page (cached). Never mutate the returned tree."""
        if page.url not in self._soups:
            self._soups[page.url] = BeautifulSoup(page.text, "html.parser")
        return self._soups[page.url]

    def visible_text(self, page: FetchedPage) -> str:
        """Human-readable text in the raw HTML (what a non-JS crawler can read), cached."""
        if page.url not in self._texts:
            strings = (
                s.strip()
                for s in self.soup(page).find_all(string=True)
                if s.parent is not None and s.parent.name not in NON_CONTENT_TAGS
                and not isinstance(s, Comment)
            )
            self._texts[page.url] = " ".join(s for s in strings if s)
        return self._texts[page.url]

    @property
    def home_soup(self) -> BeautifulSoup:
        return self.soup(self.homepage) if self.homepage else BeautifulSoup("", "html.parser")

    def html_pages(self) -> list[FetchedPage]:
        """Homepage plus every successfully fetched key page."""
        pages = [self.homepage] if self.homepage else []
        return pages + [p for p in self.pages.values() if p.ok and p.is_html]


async def fetch_site(url: str) -> SiteContext:
    """
    Fetch everything the audit needs for `url`.

    The homepage is required (HTTPException(400) if unreachable); every other file is optional
    and a failure just means "not there". All requests pass through the SSRF guard, including
    redirect hops.
    """
    await assert_public_url(url)
    ctx = SiteContext(url=url)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": BROWSER_UA, "Accept-Language": "en"},
        event_hooks={"request": [check_outbound_request]},
    ) as client:
        logger.info("Fetching site %s", url)
        homepage_task = asyncio.ensure_future(_fetch(client, url, MAX_HTML_BYTES))
        aux = await asyncio.gather(
            _fetch_optional(client, semaphore, urljoin(url, "/robots.txt")),
            _fetch_optional(client, semaphore, urljoin(url, "/sitemap.xml")),
            _fetch_optional(client, semaphore, urljoin(url, "/llms.txt")),
            _fetch_optional(client, semaphore, urljoin(url, "/llms-full.txt")),
            _fetch_optional(
                client, semaphore, url, headers={"User-Agent": AI_BOT_PROBE_UA}
            ),
            *[_fetch_optional(client, semaphore, urljoin(url, p)) for p in WELL_KNOWN_PATHS],
        )
        homepage = await _await_homepage(homepage_task, url)

        robots, sitemap, llms, llms_full, probe = aux[:5]
        ctx.homepage = homepage
        ctx.url = homepage.url
        ctx.bot_probe = probe
        ctx.robots_txt = robots.plain_text() if robots else ""
        ctx.llms_txt = llms.plain_text() if llms else ""
        ctx.llms_txt_status = llms.status if llms else None
        ctx.llms_full_txt = llms_full.plain_text() if llms_full else ""
        for path, page in zip(WELL_KNOWN_PATHS, aux[5:]):
            body = page.plain_text() if page else ""
            if body.strip() and _looks_like_spec(path, body):
                ctx.well_known[path] = body

        await _load_sitemap(ctx, client, semaphore, sitemap)

        targets = select_key_pages(ctx)
        if targets:
            try:
                fetches = [
                    _fetch_optional(client, semaphore, target, MAX_HTML_BYTES)
                    for target in targets.values()
                ]
                fetched = await asyncio.wait_for(
                    asyncio.gather(*fetches),
                    timeout=KEY_PAGES_BUDGET_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.warning("Key page fetch budget exceeded for %s", url)
                fetched = [None] * len(targets)
            for kind, page in zip(targets.keys(), fetched):
                # Skip links that just redirect back to the homepage.
                if page is not None and page.url.rstrip("/") != ctx.url.rstrip("/"):
                    ctx.pages[kind] = page

    return ctx


async def _await_homepage(task: asyncio.Future, url: str) -> FetchedPage:
    try:
        page = await task
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=400,
            detail=f"Timed out connecting to {url}. The site may be too slow or blocking crawlers.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=400, detail=f"Could not reach {url}. Check the URL and try again."
        )
    if not page.ok:
        raise HTTPException(
            status_code=400,
            detail=f"The site returned {page.status}. Try the GitHub URL alone.",
        )
    return page


async def _fetch(
    client: httpx.AsyncClient,
    url: str,
    max_bytes: int = MAX_TEXT_FILE_BYTES,
    headers: Optional[dict[str, str]] = None,
) -> FetchedPage:
    """GET `url`, reading at most `max_bytes` of the body."""
    start = time.monotonic()
    async with client.stream("GET", url, headers=headers) as response:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            size += len(chunk)
            if size >= max_bytes:
                break
        body = b"".join(chunks)[:max_bytes]
        try:
            text = body.decode(response.encoding or "utf-8", errors="replace")
        except LookupError:  # unknown charset in Content-Type
            text = body.decode("utf-8", errors="replace")
        return FetchedPage(
            url=str(response.url),
            status=response.status_code,
            headers={k.lower(): v for k, v in response.headers.items()},
            text=text,
            elapsed_ms=int((time.monotonic() - start) * 1000),
            size_bytes=size,
        )


async def _fetch_optional(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
    max_bytes: int = MAX_TEXT_FILE_BYTES,
    headers: Optional[dict[str, str]] = None,
) -> Optional[FetchedPage]:
    """Like _fetch, but any failure (network, SSRF block, bad encoding) returns None."""
    async with semaphore:
        try:
            return await _fetch(client, url, max_bytes, headers)
        except (httpx.HTTPError, HTTPException) as e:
            logger.info("Optional fetch failed for %s: %s", url, type(e).__name__)
            return None


def _looks_like_spec(path: str, body: str) -> bool:
    """Filter out soft-404 pages that return 200 for every path."""
    head = body.lstrip()[:2000].lower()
    if path.endswith(".yaml"):
        return "openapi:" in head or "swagger:" in head
    return head.startswith("{") or head.startswith("[") or path.endswith("api-catalog")


async def _load_sitemap(
    ctx: SiteContext,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    default_sitemap: Optional[FetchedPage],
) -> None:
    """Find the sitemap (robots.txt `Sitemap:` first, else /sitemap.xml) and read its URLs."""
    declared = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", ctx.robots_txt)
    ctx.sitemap_in_robots = bool(declared)

    page = default_sitemap if default_sitemap and _is_sitemap(default_sitemap) else None
    if declared and (page is None or page.url != declared[0]):
        candidate = await _fetch_optional(client, semaphore, urljoin(ctx.url, declared[0]))
        if candidate and _is_sitemap(candidate):
            page = candidate
    if page is None:
        return

    ctx.sitemap_url = page.url
    text = page.text
    if "<sitemapindex" in text[:2000].lower():
        children = parse_sitemap_locs(text)
        child = await _fetch_optional(client, semaphore, children[0]) if children else None
        if child is None or not _is_sitemap(child):
            ctx.sitemap_has_lastmod = "<lastmod" in text.lower()
            return
        text = child.text

    ctx.sitemap_urls = parse_sitemap_locs(text)[:MAX_SITEMAP_URLS]
    ctx.sitemap_has_lastmod = "<lastmod" in text.lower()


def _is_sitemap(page: FetchedPage) -> bool:
    head = page.text.lstrip()[:2000].lower()
    return page.ok and ("<urlset" in head or "<sitemapindex" in head)


def parse_sitemap_locs(xml: str) -> list[str]:
    """Extract <loc> URLs from a sitemap or sitemap index (regex: tolerant of bad XML)."""
    return [loc.strip() for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml, re.I)]


def select_key_pages(ctx: SiteContext) -> dict[str, str]:
    """
    Pick up to MAX_KEY_PAGES same-origin URLs worth reading, one per page kind.

    Homepage links win over sitemap URLs because nav links are what a visitor (or agent) sees.
    """
    host = urlparse(ctx.url).netloc.lower().removeprefix("www.")
    home = ctx.url.rstrip("/")

    candidates: list[str] = []
    for a in ctx.home_soup.find_all("a", href=True):
        candidates.append(urljoin(ctx.url, a["href"]).split("#")[0])
    candidates += ctx.sitemap_urls

    same_origin = []
    for candidate in dict.fromkeys(candidates):
        parsed = urlparse(candidate)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower().removeprefix("www.") != host or candidate.rstrip("/") == home:
            continue
        same_origin.append(candidate)

    selected: dict[str, str] = {}
    for kind, keywords in KEY_PAGE_KEYWORDS.items():
        for keyword in keywords:
            match = next((u for u in same_origin if _path_has_keyword(u, keyword)), None)
            if match and match not in selected.values():
                selected[kind] = match
                break
        if len(selected) >= MAX_KEY_PAGES:
            break
    return selected


def _path_has_keyword(url: str, keyword: str) -> bool:
    segments = [s for s in urlparse(url).path.lower().split("/") if s]
    # Prefer shallow pages: /pricing over /blog/2021/our-pricing-changes.
    return len(segments) <= 2 and any(
        s == keyword or s.startswith(keyword + "-") or s.startswith(keyword + ".")
        for s in segments
    )


def is_challenge_page(page: FetchedPage) -> bool:
    """True if a response looks like a bot-challenge / WAF block page rather than content."""
    if page.status in (401, 403, 429, 503):
        return True
    head = page.text[:5000].lower()
    return any(marker in head for marker in CHALLENGE_MARKERS)


def website_data_from_context(ctx: SiteContext) -> dict:
    """The homepage summary dict the LLM prompt and legacy artifact generators expect."""
    soup = BeautifulSoup(ctx.homepage.text if ctx.homepage else "", "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    title = soup.find("title")
    return {
        "title": title.get_text(strip=True) if title else "",
        "description": get_meta_description(soup),
        "headings": [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:20]],
        "api_links": find_api_links(soup, ctx.url),
        "body_text": soup.get_text(separator=" ", strip=True)[:MAX_BODY_CHARS],
        "has_llms_txt": looks_like_llms_txt(ctx.llms_txt),
        "blocked_ai_bots": blocked_ai_bots(ctx.robots_txt) if ctx.robots_txt else [],
    }
