"""Fingerprints the CMS / site builder / framework a site runs on, from its raw HTML and headers."""

from __future__ import annotations

import re
from typing import Optional

from models import Platform
from site_fetcher import SiteContext

# (id, name, generator-meta pattern, HTML markers, header markers as (header, substring)).
# Within each signal type, hosted builders win over frameworks they may be built on.
FINGERPRINTS: tuple[tuple[str, str, str, tuple[str, ...], tuple[tuple[str, str], ...]], ...] = (
    ("shopify", "Shopify", r"shopify", ("cdn.shopify.com", "shopify.theme", "myshopify.com"),
     (("x-shopify-stage", ""), ("x-shopid", ""), ("powered-by", "shopify"))),
    ("wix", "Wix", r"wix\.com", ("static.wixstatic.com", "static.parastorage.com", "wix-image"),
     (("x-wix-request-id", ""),)),
    ("squarespace", "Squarespace", r"squarespace",
     ("static1.squarespace.com", "squarespace-cdn.com", "sqs-block"),
     (("server", "squarespace"),)),
    ("webflow", "Webflow", r"webflow",
     ("data-wf-site", "data-wf-page", "assets.website-files.com", "cdn.prod.website-files.com"),
     (("x-wf-", ""),)),
    ("framer", "Framer", r"framer", ("framerusercontent.com", "framer.com/m/", "data-framer-"),
     (("server", "framer"),)),
    ("wordpress", "WordPress", r"wordpress", ("/wp-content/", "/wp-includes/", "wp-json"),
     (("x-powered-by", "wp engine"), ("link", "api.w.org"))),
    ("nextjs", "Next.js", r"next\.js", ("__next_data__", "/_next/static/", "self.__next_f"),
     (("x-powered-by", "next.js"), ("x-nextjs-cache", ""))),
)


def _generator(ctx: SiteContext) -> str:
    tag = ctx.home_soup.find("meta", attrs={"name": re.compile("^generator$", re.I)})
    return (tag.get("content") or "").strip() if tag else ""


def detect_platform(ctx: SiteContext) -> Optional[Platform]:
    """The platform the homepage was built with, or None if nothing recognizable was found."""
    if not ctx.has_website:
        return None
    generator = _generator(ctx)
    html = ctx.homepage.text.lower()
    headers = ctx.homepage.headers

    # Strongest signal first across all platforms: a WordPress site embedding a Shopify buy
    # button is still WordPress.
    for pid, name, gen_pattern, _, _ in FINGERPRINTS:
        if generator and re.search(gen_pattern, generator, re.I):
            evidence = f'<meta name="generator" content="{generator[:60]}">'
            return Platform(id=pid, name=name, evidence=evidence)
    for pid, name, _, _, header_markers in FINGERPRINTS:
        for header, needle in header_markers:
            matched = [h for h in headers if h.startswith(header) and needle in headers[h].lower()]
            if matched:
                return Platform(id=pid, name=name, evidence=f"{matched[0]} response header")
    for pid, name, _, markers, _ in FINGERPRINTS:
        marker = next((m for m in markers if m in html), None)
        if marker:
            return Platform(id=pid, name=name, evidence=f'"{marker}" in the page HTML')
    return None
