"""Developer track — API products only: specs, docs and MCP that let agents call the API."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from checks.base import Outcome, check
from site_fetcher import SiteContext

CATEGORY = "developer"
SPEC_NAMES = ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json")
MCP_PATHS = ("/.well-known/mcp.json", "/.well-known/mcp/server-card.json")
DEV_LINK_PATTERN = re.compile(r"(/api\b|/api/|developer|swagger|openapi|/reference)", re.I)


def _home_hrefs(ctx: SiteContext) -> list[str]:
    if not ctx.has_website:
        return []
    return [a["href"] for a in ctx.home_soup.find_all("a", href=True)]


def is_developer_product(ctx: SiteContext) -> bool:
    """Whether the developer track applies: a repo, an API spec, API links, or the LLM says so."""
    return bool(
        ctx.github
        or ctx.llm_says_api
        or any(p in ctx.well_known for p in ("/openapi.json", "/openapi.yaml", "/swagger.json"))
        or _site_is_docs(ctx)
        or any(DEV_LINK_PATTERN.search(href) for href in _home_hrefs(ctx))
    )


def _dev_text(ctx: SiteContext) -> str:
    """Docs page, homepage and README text, lowercased, for keyword checks."""
    parts = [ctx.github.get("readme", "")]
    if ctx.has_website:
        parts.append(ctx.visible_text(ctx.homepage))
    docs = ctx.pages.get("docs")
    if docs and docs.ok:
        parts.append(ctx.visible_text(docs))
    return " ".join(parts).lower()


def _site_is_docs(ctx: SiteContext) -> bool:
    """The scanned URL itself is a docs site (docs.example.com, example.com/docs/...)."""
    if not ctx.has_website:
        return False
    parsed = urlparse(ctx.url)
    return parsed.netloc.lower().startswith(("docs.", "developer.", "developers.")) or (
        "docs" in parsed.path.lower().split("/")
    )


def _repo_files(ctx: SiteContext) -> list[str]:
    return [p.lower() for p in ctx.github.get("file_tree", [])]


DEV = {
    "needs_website": False,
    "applies": is_developer_product,
    "na_reason": "No API or developer product detected, so the developer track was skipped.",
}


@check(
    "openapi_spec",
    CATEGORY,
    "OpenAPI spec is published",
    weight=8,
    why="An OpenAPI spec is the machine-readable contract agents and SDK generators use to "
    "call your API correctly.",
    **DEV,
    effort="dev",
)
def openapi_spec(ctx: SiteContext) -> Outcome:
    found = [p for p in ("/openapi.json", "/openapi.yaml", "/swagger.json",
                         "/.well-known/openapi.json") if p in ctx.well_known]
    if found:
        return Outcome("pass", f"Spec served at {ctx.origin}{found[0]}.")
    linked = [h for h in _home_hrefs(ctx) if re.search(r"(openapi|swagger)", h, re.I)]
    if linked:
        return Outcome("pass", f"Homepage links to a spec: {linked[0]}")
    in_repo = [p for p in _repo_files(ctx) if p.rsplit("/", 1)[-1] in SPEC_NAMES]
    if in_repo:
        return Outcome("pass", f"Spec in the repo: {in_repo[0]}")
    return Outcome(
        "fail", "No OpenAPI/Swagger spec found on the site or in the repo.",
        "Publish your spec at /openapi.json (the Fix-it pack has a draft to start from).",
    )


@check(
    "api_docs",
    CATEGORY,
    "API documentation exists",
    weight=5,
    why="Agents (and the developers building them) need reference docs for endpoints, "
    "parameters and errors.",
    **DEV,
    effort="dev",
)
def api_docs(ctx: SiteContext) -> Outcome:
    docs = ctx.pages.get("docs")
    if docs and docs.ok:
        return Outcome("pass", f"Docs page: {docs.url}")
    if _site_is_docs(ctx):
        return Outcome("pass", f"The scanned site is documentation: {ctx.url}")
    if len(ctx.github.get("readme", "")) > 1500:
        return Outcome(
            "warn", "Only README documentation was found.",
            "Publish reference docs (e.g. generated from your OpenAPI spec) at /docs.",
        )
    return Outcome("fail", "No docs page found.", "Publish API reference docs at /docs.")


@check(
    "mcp_server",
    CATEGORY,
    "An MCP server is available",
    weight=5,
    why="An MCP server lets Claude, ChatGPT and IDE agents use your product as a tool, "
    "without custom integration code.",
    **DEV,
    effort="dev",
)
def mcp_server(ctx: SiteContext) -> Outcome:
    for path in MCP_PATHS:
        if path in ctx.well_known:
            return Outcome("pass", f"MCP discovery file at {ctx.origin}{path}.")
    sources = " ".join(ctx.github.get("source_files", {}).values()).lower()
    if "@modelcontextprotocol" in sources or any("mcp" in p for p in _repo_files(ctx)):
        return Outcome("pass", "The repo contains an MCP server.")
    if "mcp server" in _dev_text(ctx) or "model context protocol" in _dev_text(ctx):
        return Outcome("pass", "Your docs mention an MCP server.")
    return Outcome(
        "warn", "No MCP server found.",
        "Start from the MCP server scaffold in the Fix-it pack below and publish it as an npm "
        "package or a remote MCP endpoint.",
    )


@check(
    "auth_documented",
    CATEGORY,
    "API authentication is documented",
    weight=3,
    why="Agents need to know how to authenticate (API key, OAuth) before they can make a "
    "single call.",
    **DEV,
)
def auth_documented(ctx: SiteContext) -> Outcome:
    match = re.search(r"api[ -]?keys?|bearer token|oauth|access token", _dev_text(ctx))
    if match:
        return Outcome("pass", f'Docs mention "{match[0]}".')
    return Outcome(
        "warn", "No mention of API keys, OAuth or tokens in the docs scanned.",
        "Document how to get credentials and which header to send, e.g. "
        "`Authorization: Bearer <API_KEY>`.",
    )


@check(
    "webhooks",
    CATEGORY,
    "Webhooks are offered",
    weight=2,
    why="Webhooks let agents react to events instead of polling your API.",
    **DEV,
)
def webhooks(ctx: SiteContext) -> Outcome:
    if "webhook" in _dev_text(ctx):
        return Outcome("pass", "Docs mention webhooks.")
    return Outcome("warn", "No mention of webhooks in the docs scanned.",
                   "If you support event callbacks, document them under /docs/webhooks.")


@check(
    "rate_limits",
    CATEGORY,
    "Rate limits are documented",
    weight=2,
    why="Agents call APIs in bursts. Documented limits (and 429 + Retry-After) let them back "
    "off correctly.",
    **DEV,
)
def rate_limits(ctx: SiteContext) -> Outcome:
    if re.search(r"rate[ -]limit", _dev_text(ctx)):
        return Outcome("pass", "Docs mention rate limits.")
    return Outcome(
        "warn", "No mention of rate limits in the docs scanned.",
        "Document your limits and return 429 with a Retry-After header when they're hit.",
    )
