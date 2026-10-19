"""Category D — agent discovery & usability: can an agent find a guide and operate the site?"""

from __future__ import annotations

import re

from bs4 import Tag

from checks.base import Outcome, check, examples, ratio_status
from checks.structured_data import site_name
from crawler import looks_like_llms_txt
from site_fetcher import SiteContext

CATEGORY = "agent"

FIELD_EXCLUDED_TYPES = {"hidden", "submit", "button", "image", "reset"}
CAPTCHA_MARKERS = {
    "reCAPTCHA": "google.com/recaptcha",
    "hCaptcha": "hcaptcha.com",
    "Cloudflare Turnstile": "challenges.cloudflare.com/turnstile",
    "Friendly Captcha": "friendlycaptcha",
}
INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea", "summary", "label", "option"}


def llms_txt_template(ctx: SiteContext) -> str:
    """A starter llms.txt built from what was crawled."""
    desc = ""
    meta = ctx.home_soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        desc = meta["content"].strip()
    lines = [f"# {site_name(ctx)}", "", f"> {desc or 'One-sentence summary of what you offer.'}"]
    lines += ["", "## Key pages", f"- [Home]({ctx.url}): Overview"]
    lines += [f"- [{kind.title()}]({page.url})" for kind, page in ctx.pages.items() if page.ok]
    return "\n".join(lines) + "\n"


@check(
    "llms_txt",
    CATEGORY,
    "llms.txt guides AI to your content",
    weight=2,
    why="/llms.txt is a proposed standard: a short markdown map of your site for language "
    "models. Coding assistants and some AI tools read it, but the big AI search crawlers "
    "rarely request it today, so it's cheap to add with a modest payoff.",
    effort="minutes",
)
def llms_txt(ctx: SiteContext) -> Outcome:
    text = ctx.llms_txt
    fix = (
        "Save as /llms.txt at your site root (Fix-it pack below has a fuller version):\n\n"
        + llms_txt_template(ctx)
    )
    if not text.strip():
        evidence = "No llms.txt at /llms.txt."
        if ctx.llms_txt_status == 200:
            evidence = "/llms.txt returns an HTML page (catch-all route), not a markdown file."
        return Outcome("fail", evidence, fix, "markdown")
    if not looks_like_llms_txt(text):
        return Outcome("warn", "/llms.txt exists but doesn't start with a '# Title' line.", fix,
                       "markdown")
    links = len(re.findall(r"\[[^\]]+\]\([^)]+\)", text))
    if not links:
        return Outcome("warn", "/llms.txt has a title but no links to your pages.", fix,
                       "markdown")
    return Outcome("pass", f"/llms.txt found with {links} links.")


@check(
    "llms_full_txt",
    CATEGORY,
    "llms-full.txt offers the full content",
    weight=1,
    why="Optional companion to llms.txt with your full docs/content in one file, so AI can "
    "read everything in a single request.",
)
def llms_full_txt(ctx: SiteContext) -> Outcome:
    if ctx.llms_full_txt.strip():
        return Outcome("pass", f"/llms-full.txt found ({len(ctx.llms_full_txt) // 1024} KB read).")
    return Outcome(
        "warn", "No /llms-full.txt (optional).",
        "Publish /llms-full.txt containing the markdown text of your most important pages.",
    )


def _field_label(field: Tag, labelled_ids: set[str]) -> str:
    """'label' | 'placeholder' | '' for one form field."""
    if field.get("aria-label") or field.get("aria-labelledby") or field.get("title"):
        return "label"
    if field.get("id") and field["id"] in labelled_ids:
        return "label"
    if field.find_parent("label") is not None:
        return "label"
    return "placeholder" if field.get("placeholder") else ""


@check(
    "form_labels",
    CATEGORY,
    "Form fields have labels",
    weight=5,
    why="Browser agents (ChatGPT agent, Claude, Operator-style tools) fill forms through the "
    "accessibility tree — an unlabeled field is a guess.",
)
def form_labels(ctx: SiteContext) -> Outcome:
    total = labelled = placeholder_only = 0
    for page in ctx.html_pages():
        soup = ctx.soup(page)
        labelled_ids = {lbl["for"] for lbl in soup.find_all("label") if lbl.get("for")}
        for field in soup.find_all(["input", "select", "textarea"]):
            if (field.get("type") or "").lower() in FIELD_EXCLUDED_TYPES:
                continue
            total += 1
            kind = _field_label(field, labelled_ids)
            labelled += kind == "label"
            placeholder_only += kind == "placeholder"
    if not total:
        return Outcome("na", "No form fields on the pages scanned.")
    evidence = f"{labelled} of {total} form fields have a real label"
    if placeholder_only:
        evidence += f"; {placeholder_only} rely on placeholder text only"
    status = ratio_status(labelled / total, 0.9, 0.5)
    fix = '<label for="email">Work email</label>\n<input id="email" name="email" type="email">'
    return Outcome(status, evidence + ".", "" if status == "pass" else fix, "html")


def _accessible_name(el: Tag) -> str:
    for attr in ("aria-label", "aria-labelledby", "title"):
        if el.get(attr):
            return el[attr]
    if el.name == "input":
        return el.get("value") or ""
    text = el.get_text(" ", strip=True)
    if text:
        return text
    img = el.find("img", alt=True)
    return img["alt"] if img else ""


@check(
    "control_names",
    CATEGORY,
    "Buttons and links have names",
    weight=4,
    why="Agents pick what to click by its accessible name. Icon-only buttons with no label "
    "are invisible to them.",
)
def control_names(ctx: SiteContext) -> Outcome:
    controls: list[Tag] = []
    for page in ctx.html_pages():
        soup = ctx.soup(page)
        controls += soup.find_all("button")
        controls += soup.find_all("a", href=True)
        controls += soup.find_all("input", type=re.compile(r"^(submit|button)$", re.I))
    if not controls:
        return Outcome("na", "No buttons or links found.")
    unnamed = [c for c in controls if not _accessible_name(c).strip()]
    named = len(controls) - len(unnamed)
    hrefs = [c.get("href", f"<{c.name}>") for c in unnamed]
    evidence = f"{named} of {len(controls)} buttons/links have an accessible name."
    if unnamed:
        evidence += f" Unnamed: {examples(hrefs)}."
    status = ratio_status(named / len(controls), 0.95, 0.8)
    fix = '<a href="https://twitter.com/you" aria-label="Twitter">\n  <svg>…</svg>\n</a>'
    return Outcome(status, evidence, "" if status == "pass" else fix, "html")


@check(
    "clickable_divs",
    CATEGORY,
    "Clickable things are real buttons and links",
    weight=2,
    why="A <div onclick> doesn't appear as a control in the accessibility tree, so agents "
    "can't find it.",
    effort="dev",
)
def clickable_divs(ctx: SiteContext) -> Outcome:
    offenders = [
        el.name
        for page in ctx.html_pages()
        for el in ctx.soup(page).find_all(attrs={"onclick": True})
        if el.name not in INTERACTIVE_TAGS and el.get("role") not in ("button", "link")
    ]
    if offenders:
        return Outcome(
            "warn", f"{len(offenders)} non-interactive element(s) with onclick handlers "
            f"(e.g. <{offenders[0]}>).",
            '<button type="button" onclick="...">Do the thing</button>', "html",
        )
    return Outcome("pass", "No onclick handlers on non-interactive elements in the HTML.")


@check(
    "captcha",
    CATEGORY,
    "No CAPTCHA wall on main pages",
    weight=4,
    why="Agents can't solve CAPTCHAs. A CAPTCHA on sign-up or contact blocks every agent "
    "trying to act for a customer.",
    effort="dev",
)
def captcha(ctx: SiteContext) -> Outcome:
    found = {
        name: page.url
        for page in ctx.html_pages()
        for name, marker in CAPTCHA_MARKERS.items()
        if marker in page.text.lower()
    }
    if found:
        name, url = next(iter(found.items()))
        return Outcome(
            "warn", f"{', '.join(found)} detected (e.g. on {url}).",
            "Prefer invisible / risk-based bot checks, and offer an API or an agent-friendly "
            "path (e.g. a documented booking or contact endpoint) for important actions.",
        )
    return Outcome("pass", "No CAPTCHA scripts on the pages scanned.")


@check(
    "image_alt",
    CATEGORY,
    "Images have alt text",
    weight=3,
    why="Alt text is the only way an AI that reads HTML knows what an image shows — products, "
    "menus, team photos.",
)
def image_alt(ctx: SiteContext) -> Outcome:
    images = [img for page in ctx.html_pages() for img in ctx.soup(page).find_all("img")]
    if not images:
        return Outcome("na", "No images in the HTML.")
    missing = [img.get("src", "?") for img in images if img.get("alt") is None]
    with_alt = len(images) - len(missing)
    evidence = f"{with_alt} of {len(images)} images have an alt attribute."
    if missing:
        evidence += f" Missing on: {examples([m[:80] for m in missing])}."
    status = ratio_status(with_alt / len(images), 0.9, 0.6)
    fix = '<img src="/menu.jpg" alt="Lunch menu: soups from $6, sandwiches from $9">'
    return Outcome(status, evidence, "" if status == "pass" else fix, "html")
