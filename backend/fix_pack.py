"""Fix-it pack v2: paste-ready files built from the crawled pages, tailored to the platform."""

from __future__ import annotations

import difflib
import html
import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from checks.answerability import PRICE_PATTERN
from checks.crawler_access import AI_BOT_INFO, sample_paths
from checks.developer import is_developer_product
from checks.structured_data import meta_content, node_types, site_name, site_schema_nodes
from models import AIPreview, Artifacts, Audit, FixPack, FixPackFile, ProductAnalysis
from platform_detect import detect_platform
from platform_guides import how_to
from site_fetcher import SiteContext, base_segments, relative_segments

ANSWER_BOTS = [bot for bot, _, purpose in AI_BOT_INFO if purpose in ("search", "user")]
TRAINING_BOTS = [bot for bot, _, purpose in AI_BOT_INFO if purpose == "training"]

# llms.txt sections: (heading, page kinds), in order.
LLMS_SECTIONS = (
    ("Main pages", ("features", "menu", "pricing", "about", "contact", "faq")),
    ("Docs", ("docs",)),
    ("Optional", ("blog",)),
)
MAX_EXTRA_PAGES = 10
MAX_FAQ_ITEMS = 8
MAX_LINK_DESCRIPTION = 140
MIN_LEAD_WORDS = 12
SKIP_EXTRA_SEGMENTS = {"tag", "tags", "category", "categories", "author", "page", "feed", "cart",
                       "account", "login", "search", "wp-content", "cdn-cgi"}
SOCIAL_HOSTS = ("linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
                "youtube.com", "github.com", "tiktok.com", "threads.net", "bsky.app")
DANGLING_WORDS = {"a", "an", "the", "and", "or", "with", "for", "of", "to", "in", "on", "across"}
CURRENCIES = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR"}


def build_fix_pack(
    ctx: SiteContext, analysis: ProductAnalysis, audit: Audit, artifacts: Artifacts
) -> FixPack:
    """
    Every Fix-it pack file for this scan.

    Website scans get llms.txt, a robots.txt diff, JSON-LD and meta tags with platform-specific
    install steps. OpenAPI and MCP drafts are only included on the developer track.
    """
    platform = detect_platform(ctx)
    pid = platform.id if platform else None
    developer = is_developer_product(ctx)
    files: list[FixPackFile] = []

    if ctx.has_website:
        statuses = {c.id: c.status for c in audit.checks}
        files += [
            FixPackFile(
                id="llms_txt", label="llms.txt", filename="llms.txt", language="markdown",
                content=llms_txt(ctx, analysis),
                description="A map of your site for AI, built from the pages we crawled "
                "(llmstxt.org format).",
                how_to=how_to("llms_txt", pid),
            ),
            FixPackFile(
                id="robots_txt", label="robots.txt", filename="robots.txt.diff",
                language="diff", content=robots_patch(ctx),
                description="Changes to your robots.txt so AI search and assistant bots can "
                "read you. Training-bot opt-out is optional.",
                how_to=how_to("robots_txt", pid),
            ),
            FixPackFile(
                id="json_ld", label="JSON-LD", filename="structured-data.html", language="html",
                content=json_ld(ctx, analysis),
                description="schema.org structured data your site is missing, pre-filled from "
                "your pages.",
                how_to=how_to("json_ld", pid),
            ),
            FixPackFile(
                id="meta_tags", label="Meta tags", filename="meta-tags.html", language="html",
                content=meta_tags(ctx, analysis, statuses),
                description="Title, description and social tags to fix or add.",
                how_to=how_to("meta_tags", pid),
            ),
        ]
    else:
        files.append(
            FixPackFile(
                id="llms_txt", label="llms.txt", filename="llms.txt", language="markdown",
                content=artifacts.llms_txt,
                description="A starting llms.txt drafted from your repository.",
                how_to=how_to("llms_txt", None),
            )
        )

    if developer:
        files += [
            FixPackFile(
                id="openapi", label="OpenAPI draft", filename="openapi.yaml", language="yaml",
                content=artifacts.openapi_yaml, developer=True,
                description="A draft OpenAPI spec inferred from your docs. Review every path.",
            ),
            FixPackFile(
                id="mcp_server", label="MCP server", filename="mcp_server.ts",
                language="typescript", content=artifacts.mcp_server_ts, developer=True,
                description="An MCP server scaffold so Claude, ChatGPT and IDE agents can use "
                "your API as a tool.",
            ),
        ]

    return FixPack(platform=platform, developer_track=developer, files=files)


def upgrade_check_fixes(audit: Audit, pack: FixPack) -> None:
    """
    Swap the llms.txt check's starter template for the full crawled-pages version, in the
    check list and in Top fixes, so every place shows the same file.
    """
    llms = next((f for f in pack.files if f.id == "llms_txt"), None)
    if llms is None:
        return
    fix = "Save as /llms.txt at your site root:\n\n" + llms.content
    for check in audit.checks:
        if check.id == "llms_txt" and check.fix:
            check.fix = fix
    for top in audit.top_fixes:
        if top.check_id == "llms_txt":
            top.fix = fix


# --- llms.txt ------------------------------------------------------------------------------


def _clean_title(title: str, brand: str) -> str:
    """'Pricing | Acme' → 'Pricing'. Keeps the title if splitting would leave only the brand."""
    parts = [p.strip() for p in re.split(r"\s[|·–—-]\s", title) if p.strip()]
    useful = [p for p in parts if p.lower() != brand.lower()]
    return (useful[0] if useful else title).strip()


def _first_sentence(text: str, limit: int = MAX_LINK_DESCRIPTION) -> str:
    text = " ".join(text.split())
    match = re.match(r"(.{20,}?[.!?])\s", text + " ")
    sentence = match[1] if match else text
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rsplit(" ", 1)[0] + "…"


def _lead_paragraph(soup: BeautifulSoup) -> str:
    """First real paragraph of the main content (skips nav, footers and one-line blurbs)."""
    root = soup.find("main") or soup.find(attrs={"role": "main"}) or soup
    for p in root.find_all("p"):
        if p.find_parent(["nav", "footer", "header", "aside"]) is not None:
            continue
        text = " ".join(p.get_text(" ", strip=True).split())
        if len(text.split()) >= MIN_LEAD_WORDS:
            return text
    return ""


def _page_link(ctx: SiteContext, kind: str, url: str, soup: BeautifulSoup, title: str = "") -> str:
    """'- [Title](url): description' for one crawled page."""
    title_tag = soup.title.get_text(strip=True) if soup.title else ""
    if not title:
        title = _clean_title(title_tag, site_name(ctx)) if title_tag else kind.title()
    description = meta_content(soup, "description") or _lead_paragraph(soup)
    line = f"- [{title.replace(']', '')}]({url})"
    return line + (f": {_first_sentence(description)}" if description else "")


def _slug_title(url: str) -> str:
    segments = [s for s in urlparse(url).path.split("/") if s]
    last = re.sub(r"\.\w+$", "", segments[-1]) if segments else "Home"
    return last.replace("-", " ").replace("_", " ").strip().capitalize() or "Page"


def _extra_pages(ctx: SiteContext, listed: set[str]) -> list[str]:
    """Shallow sitemap URLs not already listed, as plain links."""
    base = base_segments(ctx.url)
    lines = []
    for url in ctx.sitemap_urls:
        if url.rstrip("/") in listed or urlparse(url).query:
            continue
        segments = relative_segments(url, base)
        if not 1 <= len(segments) <= 2 or SKIP_EXTRA_SEGMENTS & set(segments):
            continue
        if re.search(r"\.(xml|pdf|jpe?g|png|gif|zip)$", url, re.I):
            continue
        lines.append(f"- [{_slug_title(url)}]({url})")
        listed.add(url.rstrip("/"))
        if len(lines) >= MAX_EXTRA_PAGES:
            break
    return lines


def llms_txt(ctx: SiteContext, analysis: ProductAnalysis) -> str:
    """An llms.txt (llmstxt.org: H1, blockquote summary, details, H2 link lists) from real pages."""
    name = analysis.product_name.strip() or site_name(ctx)
    summary = (
        analysis.product_description.strip()
        or meta_content(ctx.home_soup, "description")
        or "One-sentence summary of what you offer."
    )
    lines = [f"# {name}", "", f"> {' '.join(summary.split())}", ""]

    facts = [q for q in analysis.ai_preview.questions if q.answered and q.answer][:5]
    if facts:
        lines += ["Key facts:", ""]
        lines += [f"- {q.question.strip()} {q.answer.strip()}" for q in facts]
        lines.append("")

    home = ctx.homepage
    listed = {home.url.rstrip("/")}
    by_kind = {kind: page for kind, page in ctx.pages.items() if page.ok and page.is_html}
    for heading, kinds in LLMS_SECTIONS:
        links = []
        if heading == "Main pages":
            links.append(
                _page_link(ctx, "home", home.url, ctx.home_soup, "Home")
            )
        for kind in kinds:
            page = by_kind.get(kind)
            if page and page.url.rstrip("/") not in listed:
                links.append(_page_link(ctx, kind, page.url, ctx.soup(page)))
                listed.add(page.url.rstrip("/"))
        if heading == "Optional":
            links += _extra_pages(ctx, listed)
        if links:
            lines += [f"## {heading}", "", *links, ""]

    return "\n".join(lines).rstrip() + "\n"


# --- robots.txt ----------------------------------------------------------------------------


def _robots_groups(lines: list[str]) -> list[dict]:
    """Split robots.txt into groups: {'agents': [(index, token)], 'rules': [index, ...]}."""
    groups: list[dict] = []
    current: Optional[dict] = None
    for i, raw in enumerate(lines):
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or current["rules"]:
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append((i, value))
        elif key in ("allow", "disallow", "crawl-delay") and current is not None:
            current["rules"].append(i)
    return groups


def _rule(lines: list[str], index: int) -> tuple[str, str]:
    key, value = lines[index].split("#", 1)[0].split(":", 1)
    return key.strip().lower(), value.strip()


def _blocked_answer_bots(robots: str, paths: list[str]) -> list[str]:
    parser = RobotFileParser()
    parser.parse(robots.splitlines())
    return [b for b in ANSWER_BOTS if not all(parser.can_fetch(b, p) for p in ["/", *paths])]


def suggested_robots(ctx: SiteContext) -> str:
    """robots.txt with answer bots unblocked, the sitemap declared, and an optional opt-out."""
    original = ctx.robots_txt.strip("\n")
    lines = original.splitlines() if original else []
    drop: set[int] = set()
    answer_tokens = {b.lower() for b in ANSWER_BOTS}
    star_disallows: list[str] = []

    for group in _robots_groups(lines):
        tokens = {t.lower() for _, t in group["agents"]}
        rules = [_rule(lines, i) for i in group["rules"]]
        if "*" in tokens:
            star_disallows += [v for k, v in rules if k == "disallow" and v and v != "/"]
        if not any(k == "disallow" and v for k, v in rules):
            continue
        named = [i for i, t in group["agents"] if t.lower() in answer_tokens]
        if not named:
            continue
        drop.update(named)
        if len(named) == len(group["agents"]):  # group only applied to answer bots
            drop.update(group["rules"])

    kept = [line for i, line in enumerate(lines) if i not in drop]
    if not kept:
        kept = ["User-agent: *", "Allow: /"]
    text = "\n".join(kept)

    still_blocked = _blocked_answer_bots(text, sample_paths(ctx))
    if still_blocked:
        block = ["", "# Let AI search and assistant bots read your site"]
        block += [f"User-agent: {bot}" for bot in still_blocked]
        block += [f"Disallow: {path}" for path in dict.fromkeys(star_disallows)]
        block.append("Allow: /")
        text += "\n" + "\n".join(block)

    if not re.search(r"(?im)^\s*sitemap:", text):
        text += f"\n\nSitemap: {ctx.sitemap_url or ctx.origin + '/sitemap.xml'}"

    parser = RobotFileParser()
    parser.parse(text.splitlines())
    open_training = [b for b in TRAINING_BOTS if parser.can_fetch(b, "/")]
    if open_training:
        text += (
            "\n\n# Optional: opt out of AI model training (doesn't affect AI search answers).\n"
            "# Uncomment to apply.\n"
            + "\n".join(f"# User-agent: {bot}" for bot in open_training)
            + "\n# Disallow: /"
        )
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n") + "\n"


def robots_patch(ctx: SiteContext) -> str:
    """The suggested robots.txt as a unified diff against the live one."""
    before = ctx.robots_txt.strip("\n").splitlines() if ctx.robots_txt.strip() else []
    after = suggested_robots(ctx).splitlines()
    diff = list(
        difflib.unified_diff(
            before, after, "robots.txt (current)", "robots.txt (suggested)", lineterm=""
        )
    )
    if not diff:
        return "# Your robots.txt already lets AI search and assistant bots in. No changes.\n"
    header = "# No robots.txt found — create one with these lines.\n" if not before else ""
    return header + "\n".join(diff) + "\n"


# --- JSON-LD -------------------------------------------------------------------------------


def _script(data: dict) -> str:
    body = json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{body}\n</script>'


def _logo_url(ctx: SiteContext) -> str:
    soup = ctx.home_soup
    for img in soup.find_all("img", src=True):
        label = " ".join([img.get("alt") or "", " ".join(img.get("class") or []), img["src"]])
        if "logo" in label.lower():
            return _absolute(ctx, img["src"])
    icon = soup.find("link", rel=lambda r: r and "apple-touch-icon" in r)
    if icon and icon.get("href"):
        return _absolute(ctx, icon["href"])
    return f"{ctx.origin}/logo.png"


def _absolute(ctx: SiteContext, href: str) -> str:
    return urljoin(ctx.url, href)


def _links(ctx: SiteContext, scheme: str) -> list[str]:
    found = []
    for page in ctx.html_pages():
        for a in ctx.soup(page).find_all("a", href=re.compile(rf"^{scheme}:", re.I)):
            value = a["href"].split(":", 1)[1].split("?")[0].strip()
            if value:
                found.append(value)
    return list(dict.fromkeys(found))


def _social_profiles(ctx: SiteContext) -> list[str]:
    profiles = []
    for a in ctx.home_soup.find_all("a", href=True):
        host = urlparse(a["href"]).netloc.lower().removeprefix("www.")
        if host in SOCIAL_HOSTS and urlparse(a["href"]).path.strip("/"):
            profiles.append(a["href"].split("?")[0])
    return list(dict.fromkeys(profiles))[:6]


def _organization(ctx: SiteContext, analysis: ProductAnalysis) -> dict:
    local = analysis.business_type == "local_business"
    data: dict = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness" if local else "Organization",
        "name": analysis.product_name or site_name(ctx),
        "url": ctx.origin + "/",
        "logo": _logo_url(ctx),
        "description": analysis.product_description
        or meta_content(ctx.home_soup, "description"),
    }
    emails, phones = _links(ctx, "mailto"), _links(ctx, "tel")
    if emails:
        data["email"] = emails[0]
    if phones:
        data["telephone"] = phones[0]
    if local:
        data["telephone"] = data.get("telephone", "TODO: +1-555-555-0100")
        data["address"] = {
            "@type": "PostalAddress",
            "streetAddress": "TODO",
            "addressLocality": "TODO: city",
            "postalCode": "TODO",
            "addressCountry": "TODO: e.g. US",
        }
        data["openingHours"] = "TODO: e.g. Mo-Fr 09:00-17:00"
    profiles = _social_profiles(ctx)
    data["sameAs"] = profiles or ["TODO: https://www.linkedin.com/company/your-company"]
    return data


def site_faqs(ctx: SiteContext) -> list[tuple[str, str]]:
    """Question/answer pairs visible on the scanned pages (headings, <details>, <dl>)."""
    faqs: list[tuple[str, str]] = []
    for page in ctx.html_pages():
        soup = ctx.soup(page)
        for summary in soup.find_all("summary"):
            question = summary.get_text(" ", strip=True)
            details = summary.find_parent("details")
            if details and question.endswith("?"):
                answer = details.get_text(" ", strip=True).removeprefix(question).strip()
                faqs.append((question, answer))
        for tag in soup.find_all(re.compile(r"^(h[2-4]|dt)$")):
            question = tag.get_text(" ", strip=True)
            if not question.endswith("?"):
                continue
            sibling = tag.find_next_sibling(["dd"] if tag.name == "dt" else ["p", "div"])
            if sibling is not None:
                faqs.append((question, sibling.get_text(" ", strip=True)))
    unique = {q: a for q, a in faqs if 3 <= len(a.split()) and len(q) <= 200}
    return [(q, _first_sentence(a, 300)) for q, a in unique.items()][:MAX_FAQ_ITEMS]


def _faq_page(faqs: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }


def _price(ctx: SiteContext) -> tuple[str, str]:
    """(amount, ISO currency) of the first price on the pricing page or homepage."""
    pages = [ctx.pages.get("pricing"), ctx.homepage]
    for page in pages:
        if page is None or not page.ok:
            continue
        for match in PRICE_PATTERN.finditer(ctx.visible_text(page)):
            symbol = next((s for s in CURRENCIES if s in match[0]), "")
            amount = re.search(r"\d[\d,]*(?:\.\d+)?", match[0])
            if symbol and amount:
                return amount[0].replace(",", ""), CURRENCIES[symbol]
    return "TODO: lowest price", "TODO: e.g. USD"


def _offering(ctx: SiteContext, analysis: ProductAnalysis) -> Optional[dict]:
    software = analysis.business_type in ("saas", "developer_tool") or (
        analysis.product_category.strip().upper() in ("API", "SAAS", "CLI", "LIBRARY")
    )
    if not software and analysis.business_type != "ecommerce":
        return None
    amount, currency = _price(ctx)
    offer = {"@type": "Offer", "price": amount, "priceCurrency": currency}
    pricing = ctx.pages.get("pricing")
    if pricing and pricing.ok:
        offer["url"] = pricing.url
    if software:
        return {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": analysis.product_name or site_name(ctx),
            "description": analysis.product_description,
            "url": ctx.origin + "/",
            "applicationCategory": (
                "DeveloperApplication" if analysis.business_type == "developer_tool"
                else "BusinessApplication"
            ),
            "operatingSystem": "Web",
            "offers": offer,
        }
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "TODO: product name",
        "description": "TODO: one-sentence product description",
        "image": "TODO: https://example.com/product.jpg",
        "brand": {"@type": "Brand", "name": analysis.product_name or site_name(ctx)},
        "offers": {**offer, "availability": "https://schema.org/InStock"},
    }


def json_ld(ctx: SiteContext, analysis: ProductAnalysis) -> str:
    """Paste-ready schema.org blocks for whatever the site is missing."""
    existing = {t for node in site_schema_nodes(ctx) for t in node_types(node)}
    has_org = any(
        t.endswith(("Organization", "Business")) or t in ("Corporation", "Restaurant", "Store")
        for t in existing
    )
    blocks: list[str] = []
    notes: list[str] = []

    if has_org:
        notes.append("Organization: already on your site.")
    else:
        blocks.append("<!-- Who you are -->\n" + _script(_organization(ctx, analysis)))

    if "FAQPage" in existing:
        notes.append("FAQPage: already on your site.")
    else:
        faqs = site_faqs(ctx)
        source = "taken from questions on your pages"
        if not faqs:
            faqs = _preview_faqs(analysis.ai_preview)
            source = "drafted by AI from your pages — check the wording, and show these Q&As " \
                "on the page too"
        if faqs:
            blocks.append(f"<!-- FAQ ({source}) -->\n" + _script(_faq_page(faqs)))

    if existing & {"Product", "SoftwareApplication", "WebApplication", "Offer"}:
        notes.append("Product / SoftwareApplication: already on your site.")
    else:
        offering = _offering(ctx, analysis)
        if offering:
            blocks.append(f"<!-- What you sell ({offering['@type']}) -->\n" + _script(offering))

    header = "<!-- Paste into <head>. Replace every TODO value before publishing. -->"
    if notes:
        header += "\n<!-- " + " ".join(notes) + " -->"
    if not blocks:
        return header + "\n<!-- Nothing to add: your key structured data is in place. -->\n"
    return header + "\n\n" + "\n\n".join(blocks) + "\n"


def _preview_faqs(preview: AIPreview) -> list[tuple[str, str]]:
    return [(q.question, q.answer) for q in preview.questions if q.answered and q.answer][
        :MAX_FAQ_ITEMS
    ]


# --- Meta tags -----------------------------------------------------------------------------


def _truncate(text: str, limit: int, ellipsis: bool = True) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    words = text[: limit - 1].rsplit(" ", 1)[0].split()
    if not ellipsis:  # a title shouldn't end on "with" or "and"
        while len(words) > 1 and words[-1].lower() in DANGLING_WORDS:
            words.pop()
    return " ".join(words).rstrip(",;:—-") + ("…" if ellipsis else "")


def _without_name(description: str, name: str) -> str:
    """'Acme offers fast invoicing.' → 'Fast invoicing' (for a 'Name — tagline' title)."""
    text = " ".join(description.split()).rstrip(".")
    pattern = rf"^(?:the\s+)?{re.escape(name)}\s+(?:is|are|offers|provides|makes|sells|builds|" \
        r"helps|lets|gives)\s+(?:an?\s+|the\s+)?"
    stripped = re.sub(pattern, "", text, count=1, flags=re.I)
    return stripped[:1].upper() + stripped[1:] if stripped else ""


def _attr(value: str) -> str:
    return html.escape(value, quote=True)


def meta_tags(ctx: SiteContext, analysis: ProductAnalysis, statuses: dict[str, str]) -> str:
    """A <head> block with only the meta tags that are missing or need work."""
    soup = ctx.home_soup
    name = analysis.product_name or site_name(ctx)
    current_title = soup.title.get_text(strip=True) if soup.title else ""
    current_desc = meta_content(soup, "description")

    title = current_title
    if statuses.get("title_tag") in ("warn", "fail") or not title:
        tagline = _without_name(analysis.product_description, name)
        room = max(60 - len(name) - 3, 20)
        title = f"{name} — {_truncate(tagline, room, ellipsis=False)}" if tagline else name
    description = current_desc
    if statuses.get("meta_description") in ("warn", "fail") or not description:
        source = analysis.product_description or analysis.ai_preview.summary
        description = _first_sentence(source, 160) if source else ""
    canonical = f"{ctx.origin}{urlparse(ctx.url).path or '/'}"

    tags: list[str] = []
    if title != current_title:
        tags.append(f"<title>{html.escape(title)}</title>")
    if description and description != current_desc:
        tags.append(f'<meta name="description" content="{_attr(description)}">')
    if statuses.get("canonical") in ("warn", "fail"):
        tags.append(f'<link rel="canonical" href="{_attr(canonical)}">')

    og = {
        "og:title": title,
        "og:description": description,
        "og:image": meta_content(soup, "og:image") or f"{ctx.origin}/og-image.png",
        "og:url": canonical,
        "og:type": "website",
    }
    missing_og = [k for k in og if not meta_content(soup, k)]
    if missing_og:
        tags.append("<!-- Social / AI link previews -->")
        tags += [f'<meta property="{k}" content="{_attr(og[k])}">' for k in missing_og]
        if "og:image" in missing_og:
            tags.append("<!-- TODO: upload a 1200×630 image at the og:image URL above -->")
    if not meta_content(soup, "twitter:card"):
        tags.append('<meta name="twitter:card" content="summary_large_image">')
    if statuses.get("html_lang") in ("warn", "fail"):
        tags.append('<!-- On your <html> tag: -->\n<html lang="en">')

    if not tags:
        return "<!-- Your title, description, canonical and social tags look good. -->\n"
    return "<!-- Paste inside <head>, replacing existing tags with the same name. -->\n" + \
        "\n".join(tags) + "\n"
