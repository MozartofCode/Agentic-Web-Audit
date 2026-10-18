"""Category C — machine-readable meaning: titles, meta tags and schema.org structured data."""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from checks.base import Outcome, check, examples
from site_fetcher import SiteContext

CATEGORY = "structured"

ORG_TYPES = {
    "Organization", "Corporation", "LocalBusiness", "OnlineBusiness", "OnlineStore", "Store",
    "Restaurant", "CafeOrCoffeeShop", "Bakery", "BarOrPub", "FoodEstablishment", "Hotel",
    "ProfessionalService", "LegalService", "MedicalBusiness", "MedicalClinic", "Dentist",
    "HealthAndBeautyBusiness", "HomeAndConstructionBusiness", "AutomotiveBusiness",
    "FinancialService", "RealEstateAgent", "EducationalOrganization", "NGO",
    "SportsOrganization", "NewsMediaOrganization", "GovernmentOrganization", "Person",
}


def json_ld_blocks(soup: BeautifulSoup) -> tuple[list[object], int]:
    """Parse every JSON-LD script on a page. Returns (parsed blocks, invalid block count)."""
    parsed: list[object] = []
    invalid = 0
    for script in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        try:
            parsed.append(json.loads(script.get_text()))
        except ValueError:
            invalid += 1
    return parsed, invalid


def schema_nodes(data: object) -> list[dict]:
    """Flatten JSON-LD (lists, @graph, nested objects) into a list of typed nodes."""
    nodes: list[dict] = []
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, dict):
            if "@type" in item:
                nodes.append(item)
            stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
    return nodes


def node_types(node: dict) -> list[str]:
    """@type as a list of bare names ('https://schema.org/Product' → 'Product')."""
    raw = node.get("@type")
    types = raw if isinstance(raw, list) else [raw]
    return [str(t).rsplit("/", 1)[-1] for t in types if t]


def site_schema_nodes(ctx: SiteContext) -> list[dict]:
    """Every schema.org node on the homepage and key pages."""
    nodes: list[dict] = []
    for page in ctx.html_pages():
        blocks, _ = json_ld_blocks(ctx.soup(page))
        for block in blocks:
            nodes += schema_nodes(block)
    return nodes


def _meta(soup: BeautifulSoup, key: str) -> str:
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    return (tag.get("content") or "").strip() if tag else ""


def site_name(ctx: SiteContext) -> str:
    """Best guess at the brand name, for fix snippets."""
    soup = ctx.home_soup
    name = _meta(soup, "og:site_name")
    if not name and soup.title:
        name = re.split(r"\s[|·–—-]\s", soup.title.get_text(strip=True))[0]
    return name or ctx.origin.split("//", 1)[-1]


@check(
    "title_tag",
    CATEGORY,
    "Page title is descriptive",
    weight=5,
    why="The <title> is the label AI and search engines use when they cite your page.",
)
def title_tag(ctx: SiteContext) -> Outcome:
    title = ctx.home_soup.title.get_text(strip=True) if ctx.home_soup.title else ""
    fix = f"<title>{site_name(ctx)} — what you do, for whom</title>"
    if not title:
        return Outcome("fail", "The homepage has no <title>.", fix, "html")
    if not 10 <= len(title) <= 70:
        evidence = f'Title is {len(title)} characters: "{title[:90]}". Aim for 10–70.'
        return Outcome("warn", evidence, fix, "html")
    return Outcome("pass", f'Title: "{title}"')


@check(
    "meta_description",
    CATEGORY,
    "Meta description summarizes the page",
    weight=5,
    why="AI systems often use the meta description as the one-line summary of who you are.",
)
def meta_description(ctx: SiteContext) -> Outcome:
    desc = _meta(ctx.home_soup, "description")
    fix = (
        '<meta name="description" content="One or two plain sentences: what you offer, '
        'who it is for, and where.">'
    )
    if not desc:
        return Outcome("fail", "No meta description on the homepage.", fix, "html")
    if not 50 <= len(desc) <= 170:
        return Outcome(
            "warn", f'Description is {len(desc)} characters: "{desc[:120]}". Aim for 50–170.',
            fix, "html",
        )
    return Outcome("pass", f'Description: "{desc}"')


@check(
    "json_ld",
    CATEGORY,
    "Structured data (JSON-LD) is present",
    weight=8,
    why="schema.org JSON-LD states facts — prices, hours, products, FAQs — in a form machines "
    "don't have to guess at.",
)
def json_ld(ctx: SiteContext) -> Outcome:
    types: list[str] = []
    invalid = 0
    for page in ctx.html_pages():
        blocks, bad = json_ld_blocks(ctx.soup(page))
        invalid += bad
        for block in blocks:
            for node in schema_nodes(block):
                types += node_types(node)
    types = list(dict.fromkeys(types))
    fix = (
        "Add a <script type=\"application/ld+json\"> block describing your organization and "
        "main offering (see the Organization check for a ready-made snippet)."
    )
    if invalid:
        evidence = f"{invalid} JSON-LD block(s) contain invalid JSON and are ignored by parsers."
        if types:
            evidence += f" Valid types found: {examples(types, 6)}."
        return Outcome("warn", evidence, "Validate at https://validator.schema.org and fix the "
                       "syntax errors.")
    if not types:
        return Outcome("fail", "No JSON-LD structured data on the homepage or key pages.", fix)
    return Outcome("pass", f"schema.org types found: {examples(types, 8)}.")


@check(
    "organization_schema",
    CATEGORY,
    "Organization / business is described in schema.org",
    weight=5,
    why="An Organization or LocalBusiness node tells AI your official name, logo, contact "
    "details and social profiles.",
)
def organization_schema(ctx: SiteContext) -> Outcome:
    for node in site_schema_nodes(ctx):
        types = node_types(node)
        match = next(
            (t for t in types if t in ORG_TYPES or t.endswith(("Business", "Organization"))),
            None,
        )
        if match:
            fields = [k for k in ("name", "url", "logo", "sameAs") if node.get(k)]
            missing = [k for k in ("name", "url", "logo") if not node.get(k)]
            article = "an" if match[0] in "AEIOU" else "a"
            evidence = f"Found {article} {match} node with {', '.join(fields) or 'no key fields'}."
            if missing:
                example = {"url": ctx.origin, "logo": f"{ctx.origin}/logo.png", "name": "Name"}
                fix = "Add to that node:\n" + json.dumps({k: example[k] for k in missing}, indent=2)
                return Outcome("warn", evidence + f" Missing: {', '.join(missing)}.", fix, "json")
            return Outcome("pass", evidence)

    snippet = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site_name(ctx),
        "url": ctx.origin,
        "logo": f"{ctx.origin}/logo.png",
        "description": _meta(ctx.home_soup, "description") or "What you do, in one sentence.",
        "sameAs": ["https://www.linkedin.com/company/your-company"],
    }
    return Outcome(
        "fail",
        "No Organization or LocalBusiness schema found.",
        '<script type="application/ld+json">\n' + json.dumps(snippet, indent=2) + "\n</script>",
        "html",
    )


@check(
    "open_graph",
    CATEGORY,
    "Open Graph tags are set",
    weight=3,
    why="og:title / og:description / og:image control how links to you look in chats, "
    "assistants and social posts.",
)
def open_graph(ctx: SiteContext) -> Outcome:
    keys = ("og:title", "og:description", "og:image")
    present = [k for k in keys if _meta(ctx.home_soup, k)]
    missing = [k for k in keys if k not in present]
    fix = "\n".join(
        f'<meta property="{k}" content="...">' for k in missing
    )
    if not present:
        return Outcome("fail", "No Open Graph tags on the homepage.", fix, "html")
    if missing:
        return Outcome("warn", f"Missing {', '.join(missing)}.", fix, "html")
    return Outcome("pass", "og:title, og:description and og:image are all set.")


@check(
    "canonical",
    CATEGORY,
    "Canonical URL is declared",
    weight=2,
    why="A canonical link tells crawlers which URL is the real one, so duplicates don't split "
    "your signals.",
)
def canonical(ctx: SiteContext) -> Outcome:
    link = ctx.home_soup.find("link", rel=lambda r: r and "canonical" in r)
    if link and link.get("href"):
        return Outcome("pass", f"Canonical: {link['href']}")
    return Outcome(
        "warn", "No <link rel=\"canonical\"> on the homepage.",
        f'<link rel="canonical" href="{ctx.origin}/">', "html",
    )


@check(
    "html_lang",
    CATEGORY,
    "Page language is declared",
    weight=2,
    why="The lang attribute tells AI which language to read and quote your content in.",
)
def html_lang(ctx: SiteContext) -> Outcome:
    html = ctx.home_soup.find("html")
    lang = html.get("lang") if html else None
    if lang:
        return Outcome("pass", f'<html lang="{lang}">')
    return Outcome("warn", "The <html> tag has no lang attribute.", '<html lang="en">', "html")


@check(
    "heading_structure",
    CATEGORY,
    "Headings form a clear outline",
    weight=3,
    why="A single <h1> with nested <h2>/<h3> lets AI split your page into labelled sections.",
)
def heading_structure(ctx: SiteContext) -> Outcome:
    levels = [int(h.name[1]) for h in ctx.home_soup.find_all(re.compile(r"^h[1-6]$"))]
    if not levels:
        return Outcome(
            "fail", "No headings (<h1>–<h6>) on the homepage.",
            "Use one <h1> for the page topic and <h2> for each section.",
        )
    h1_count = levels.count(1)
    skips = sum(1 for a, b in zip(levels, levels[1:]) if b > a + 1)
    evidence = f"{len(levels)} headings, {h1_count} <h1>, {skips} skipped level(s)."
    if h1_count == 1 and skips == 0:
        return Outcome("pass", evidence)
    return Outcome(
        "warn", evidence,
        "Use exactly one <h1>, and don't jump levels (e.g. <h2> straight to <h4>).",
    )
