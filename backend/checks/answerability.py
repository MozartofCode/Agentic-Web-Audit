"""Category E — answerability: does the site state the facts people ask AI about?"""

from __future__ import annotations

import re

from checks.base import Outcome, check, plural
from checks.structured_data import node_types, site_schema_nodes
from site_fetcher import SiteContext

CATEGORY = "answerability"

PRICE_PATTERN = re.compile(
    r"(?:[$€£¥₹]\s?\d[\d,.]*|\d[\d,.]*\s?(?:USD|EUR|GBP|€|£|kr|zł)\b|"
    r"\d[\d,.]*\s?(?:/\s?mo(?:nth)?|per (?:month|year|user|seat)|/\s?yr|/\s?year)|\bfree plan\b)",
    re.I,
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
MIN_PARAGRAPH_WORDS = 12


@check(
    "pricing_info",
    CATEGORY,
    "Prices are stated in text",
    weight=6,
    why="\"How much does X cost?\" is one of the most common questions people ask AI. Prices "
    "in images or behind JavaScript can't be quoted.",
)
def pricing_info(ctx: SiteContext) -> Outcome:
    page = ctx.pages.get("pricing")
    if page and page.ok:
        match = PRICE_PATTERN.search(ctx.visible_text(page))
        if match:
            return Outcome("pass", f'Pricing page {page.url} states prices (e.g. "{match[0]}").')
        return Outcome(
            "warn", f"Found {page.url} but no prices in its HTML text — they may be images or "
            "rendered by JavaScript.",
            "Write plan names and prices as plain HTML text on the pricing page.",
        )
    match = PRICE_PATTERN.search(ctx.visible_text(ctx.homepage))
    if match:
        return Outcome("pass", f'The homepage states prices (e.g. "{match[0]}").')
    return Outcome(
        "warn", "No pricing page or prices found. (Fine if you don't sell anything.)",
        "Add a /pricing page (or a prices section) with plan names and amounts as text.",
    )


@check(
    "about_page",
    CATEGORY,
    "There's an About page",
    weight=3,
    why="AI answers to \"who is behind X / is X legit?\" come from your About page.",
)
def about_page(ctx: SiteContext) -> Outcome:
    page = ctx.pages.get("about")
    if page and page.ok:
        return Outcome("pass", f"About page: {page.url}")
    return Outcome(
        "warn", "No About page linked from the homepage or sitemap.",
        "Add /about: who you are, where you're based, since when, and why customers trust you.",
    )


@check(
    "contact_info",
    CATEGORY,
    "Contact details are findable",
    weight=5,
    why="Agents booking, buying or asking on a customer's behalf need an email, phone number "
    "or contact page.",
    effort="minutes",
)
def contact_info(ctx: SiteContext) -> Outcome:
    found: list[str] = []
    for page in ctx.html_pages():
        soup = ctx.soup(page)
        if soup.find("a", href=re.compile(r"^mailto:", re.I)):
            found.append("email link")
        if soup.find("a", href=re.compile(r"^tel:", re.I)):
            found.append("phone link")
        if EMAIL_PATTERN.search(ctx.visible_text(page)):
            found.append("email address")
    if ctx.pages.get("contact") and ctx.pages["contact"].ok:
        found.append(f"contact page ({ctx.pages['contact'].url})")
    nodes = site_schema_nodes(ctx)
    if any(n.get("telephone") or n.get("email") or n.get("address") for n in nodes):
        found.append("schema.org contact fields")
    found = list(dict.fromkeys(found))
    if found:
        return Outcome("pass", f"Found: {', '.join(found)}.")
    return Outcome(
        "fail", "No email, phone link or contact page found.",
        '<a href="mailto:hello@example.com">hello@example.com</a>', "html",
    )


@check(
    "faq_content",
    CATEGORY,
    "Common questions are answered",
    weight=3,
    why="Question-and-answer content maps directly onto how people phrase prompts to AI.",
)
def faq_content(ctx: SiteContext) -> Outcome:
    if any("FAQPage" in node_types(n) for n in site_schema_nodes(ctx)):
        return Outcome("pass", "FAQPage structured data found.")
    page = ctx.pages.get("faq")
    if page and page.ok:
        return Outcome("pass", f"FAQ / help page: {page.url}")
    questions = [
        h.get_text(" ", strip=True)
        for p in ctx.html_pages()
        for h in ctx.soup(p).find_all(re.compile(r"^(h[2-4]|summary|dt)$"))
        if h.get_text(strip=True).endswith("?")
    ]
    if len(questions) >= 3:
        return Outcome("pass", f"{len(questions)} question-style headings found.")
    return Outcome(
        "warn", "No FAQ page, FAQ schema, or question-style headings found.",
        "Add an FAQ section answering the 5–10 questions customers ask most, as "
        "<h3>Question?</h3><p>Answer.</p>, and mark it up with FAQPage schema.",
    )


@check(
    "plain_language",
    CATEGORY,
    "Homepage explains itself in sentences",
    weight=5,
    why="Taglines and buttons alone don't tell an AI what you do. A couple of plain paragraphs "
    "does.",
)
def plain_language(ctx: SiteContext) -> Outcome:
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in ctx.home_soup.find_all("p")
        if len(p.get_text(" ", strip=True).split()) >= MIN_PARAGRAPH_WORDS
    ]
    evidence = f"The homepage has {plural(len(paragraphs), 'paragraph')} of 12+ words."
    fix = (
        "Near the top of the homepage, add 2–3 sentences: what you offer, who it's for, "
        "where you operate, and what it costs."
    )
    if len(paragraphs) >= 3:
        return Outcome("pass", evidence)
    return Outcome("warn" if paragraphs else "fail", evidence, fix)
