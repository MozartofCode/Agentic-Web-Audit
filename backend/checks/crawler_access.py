"""Category A — AI crawler access: can AI crawlers and assistants reach the site at all?"""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from checks.base import Outcome, check, examples
from models import CrawlerAccess
from site_fetcher import SiteContext, is_challenge_page

CATEGORY = "crawler"
MAX_SAMPLE_PATHS = 15

# (robots.txt token, owner, purpose). "search"/"user" bots fetch pages when someone asks an
# assistant about you; "training" bots collect data for model training.
AI_BOT_INFO: tuple[tuple[str, str, str], ...] = (
    ("OAI-SearchBot", "OpenAI", "search"),
    ("ChatGPT-User", "OpenAI", "user"),
    ("GPTBot", "OpenAI", "training"),
    ("Claude-SearchBot", "Anthropic", "search"),
    ("Claude-User", "Anthropic", "user"),
    ("ClaudeBot", "Anthropic", "training"),
    ("PerplexityBot", "Perplexity", "search"),
    ("Perplexity-User", "Perplexity", "user"),
    ("Google-Extended", "Google", "training"),
    ("Applebot-Extended", "Apple", "training"),
    ("CCBot", "Common Crawl", "training"),
    ("Bytespider", "ByteDance", "training"),
    ("meta-externalagent", "Meta", "training"),
)


def _sample_paths(ctx: SiteContext) -> list[str]:
    urls = [page.url for page in ctx.pages.values()] + ctx.sitemap_urls[:MAX_SAMPLE_PATHS]
    paths = [urlparse(u).path or "/" for u in urls]
    return [p for p in dict.fromkeys(paths) if p != "/"][:MAX_SAMPLE_PATHS]


def crawler_access_matrix(ctx: SiteContext) -> list[CrawlerAccess]:
    """Per-bot robots.txt verdict: blocked from /, blocked from some key pages, or allowed."""
    if not ctx.robots_txt.strip():
        return [
            CrawlerAccess(
                bot=bot, owner=owner, purpose=purpose, status="allowed",
                detail="No robots.txt — allowed by default.",
            )
            for bot, owner, purpose in AI_BOT_INFO
        ]

    parser = RobotFileParser()
    parser.parse(ctx.robots_txt.splitlines())
    paths = _sample_paths(ctx)

    matrix = []
    for bot, owner, purpose in AI_BOT_INFO:
        if not parser.can_fetch(bot, "/"):
            status, detail = "blocked", "Disallowed from the whole site."
        else:
            blocked = [p for p in paths if not parser.can_fetch(bot, p)]
            if blocked:
                status, detail = "partial", f"Blocked from {examples(blocked)}."
            else:
                status, detail = "allowed", "Allowed."
        matrix.append(
            CrawlerAccess(bot=bot, owner=owner, purpose=purpose, status=status, detail=detail)
        )
    return matrix


@check(
    "robots_txt",
    CATEGORY,
    "robots.txt is published",
    weight=2,
    why="robots.txt is where crawlers look first for your rules and your sitemap.",
)
def robots_txt(ctx: SiteContext) -> Outcome:
    if ctx.robots_txt.strip():
        lines = [line for line in ctx.robots_txt.splitlines() if line.strip()]
        return Outcome("pass", f"Found {ctx.origin}/robots.txt ({len(lines)} rules).")
    return Outcome(
        "warn",
        "No robots.txt found. Every crawler is allowed by default, but bots can't discover "
        "your sitemap.",
        f"User-agent: *\nAllow: /\n\nSitemap: {ctx.origin}/sitemap.xml\n",
        "text",
    )


@check(
    "answer_bots_allowed",
    CATEGORY,
    "AI assistants may read your pages",
    weight=10,
    why="When someone asks ChatGPT, Claude or Perplexity about you, these bots fetch your "
    "pages live. Blocked = the assistant answers from guesses or competitors.",
    critical=True,
)
def answer_bots_allowed(ctx: SiteContext) -> Outcome:
    answer_bots = [e for e in crawler_access_matrix(ctx) if e.purpose in ("search", "user")]
    blocked = [e.bot for e in answer_bots if e.status == "blocked"]
    partial = [e for e in answer_bots if e.status == "partial"]
    fix = (
        "# Remove any Disallow rules for these bots, then add:\n"
        + "".join(f"User-agent: {e.bot}\n" for e in answer_bots)
        + "Allow: /\n"
    )
    if blocked:
        return Outcome("fail", f"robots.txt blocks {examples(blocked, 6)}.", fix, "text")
    if partial:
        bots = examples([e.bot for e in partial], 6)
        return Outcome("warn", f"Some pages are blocked for {bots}. {partial[0].detail}", fix)
    return Outcome("pass", "All AI search and assistant bots are allowed by robots.txt.")


@check(
    "cdn_bot_blocking",
    CATEGORY,
    "No firewall/CDN blocking of AI bots",
    weight=8,
    why="Many CDNs (e.g. Cloudflare's AI-bot blocking) reject AI crawlers before robots.txt "
    "is even read.",
)
def cdn_bot_blocking(ctx: SiteContext) -> Outcome:
    probe = ctx.bot_probe
    if probe is None:
        return Outcome("na", "The AI-bot test request couldn't complete.")
    if is_challenge_page(probe):
        return Outcome(
            "warn",
            f"A request identifying as GPTBot got HTTP {probe.status} / a bot-challenge page, "
            f"while a browser got HTTP {ctx.homepage.status}. Real AI crawlers may be blocked "
            "the same way (verified bots are sometimes let through — check your settings).",
            "In your CDN / firewall bot settings (e.g. Cloudflare → Security → Bots), allow "
            "verified AI search and assistant bots: OAI-SearchBot, ChatGPT-User, Claude-User, "
            "Claude-SearchBot, PerplexityBot.",
        )
    return Outcome("pass", f"A request identifying as GPTBot got HTTP {probe.status}, same as a "
                   "browser.")


@check(
    "robots_meta",
    CATEGORY,
    "No noindex / noai directives on the homepage",
    weight=8,
    why="A noindex or nosnippet directive tells search and AI systems not to show or quote "
    "the page.",
)
def robots_meta(ctx: SiteContext) -> Outcome:
    directives: list[str] = []
    for tag in ctx.home_soup.find_all("meta"):
        name = (tag.get("name") or "").lower()
        if name in ("robots", "googlebot", "bingbot") and tag.get("content"):
            directives += [d.strip().lower() for d in tag["content"].split(",")]
    header = ctx.homepage.headers.get("x-robots-tag", "")
    directives += [d.strip().lower() for d in header.split(",") if d.strip()]

    blocking = [d for d in directives if d in ("noindex", "none")]
    limiting = [d for d in directives if d in ("noai", "noimageai", "nosnippet")]
    if blocking:
        return Outcome(
            "fail",
            f"Homepage says {', '.join(sorted(set(blocking)))} (meta robots / X-Robots-Tag).",
            '<meta name="robots" content="index, follow">',
            "html",
        )
    if limiting:
        return Outcome(
            "warn",
            f"Homepage says {', '.join(sorted(set(limiting)))} — AI answers can't quote it.",
            '<meta name="robots" content="index, follow">',
            "html",
        )
    return Outcome("pass", "No blocking robots meta tags or X-Robots-Tag headers.")


@check(
    "sitemap",
    CATEGORY,
    "Sitemap is published and discoverable",
    weight=4,
    why="A sitemap is how crawlers find pages that aren't linked from your homepage.",
)
def sitemap(ctx: SiteContext) -> Outcome:
    line = f"Sitemap: {ctx.sitemap_url or ctx.origin + '/sitemap.xml'}"
    if not ctx.sitemap_url:
        return Outcome(
            "fail",
            "No sitemap found in robots.txt or at /sitemap.xml.",
            "Generate a sitemap.xml (most CMSs and frameworks have a plugin), then add to "
            f"robots.txt:\n\n{line}",
        )
    found = f"Found {ctx.sitemap_url} ({len(ctx.sitemap_urls)} URLs read)."
    if not ctx.sitemap_in_robots:
        return Outcome("warn", found + " It isn't referenced from robots.txt.", line, "text")
    return Outcome("pass", found + " Referenced from robots.txt.")


@check(
    "sitemap_lastmod",
    CATEGORY,
    "Sitemap says when pages changed",
    weight=2,
    why="<lastmod> dates let crawlers re-read only what changed, so AI answers stay fresh.",
)
def sitemap_lastmod(ctx: SiteContext) -> Outcome:
    if not ctx.sitemap_url:
        return Outcome("na", "No sitemap to inspect.")
    if ctx.sitemap_has_lastmod:
        return Outcome("pass", "Sitemap entries include <lastmod> dates.")
    return Outcome(
        "warn",
        "Sitemap entries have no <lastmod> dates.",
        "<url>\n  <loc>https://example.com/page</loc>\n  <lastmod>2026-10-01</lastmod>\n</url>",
        "xml",
    )
