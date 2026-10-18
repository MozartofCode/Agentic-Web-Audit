"""Category B — readable without JavaScript: most AI crawlers read raw HTML and never run JS."""

from __future__ import annotations

from checks.base import Outcome, check, examples, plural, ratio_status
from site_fetcher import SiteContext

CATEGORY = "rendering"
SPA_ROOT_IDS = ("root", "app", "__next", "__nuxt", "svelte", "___gatsby", "main-app")
MIN_PAGE_WORDS = 100

SSR_FIX = (
    "Serve your content in the initial HTML: enable server-side rendering or static "
    "generation (Next.js, Nuxt, Astro, SvelteKit, Remix), or put a prerendering service in "
    "front of your app for bots. Test with: curl -s https://yoursite.com | grep 'your headline'"
)


def word_count(text: str) -> int:
    """Words in a text blob."""
    return len(text.split())


@check(
    "raw_html_text",
    CATEGORY,
    "Content is in the HTML, not only in JavaScript",
    weight=10,
    why="GPTBot, ClaudeBot and PerplexityBot don't execute JavaScript. If your text is "
    "rendered client-side, AI sees an empty page.",
    critical=True,
)
def raw_html_text(ctx: SiteContext) -> Outcome:
    words = word_count(ctx.visible_text(ctx.homepage))
    shell = next(
        (f'<div id="{i}">' for i in SPA_ROOT_IDS if ctx.home_soup.find(id=i) is not None), None
    )
    evidence = f"The homepage's raw HTML contains {plural(words, 'word')} of readable text."
    if words >= 150:
        return Outcome("pass", evidence)
    if shell:
        evidence += f" It looks like a JavaScript app shell ({shell}) that renders in the browser."
    elif words < 40:
        evidence += " Bots get a JavaScript-only page (or a bot-challenge page) with no content."
    return Outcome("warn" if words >= 40 else "fail", evidence, SSR_FIX)


@check(
    "h1_present",
    CATEGORY,
    "Main headline is in the HTML",
    weight=5,
    why="The <h1> is the strongest signal of what a page is about.",
)
def h1_present(ctx: SiteContext) -> Outcome:
    h1s = [h.get_text(" ", strip=True) for h in ctx.home_soup.find_all("h1")]
    h1s = [h for h in h1s if h]
    if h1s:
        return Outcome("pass", f'Homepage <h1>: "{" ".join(h1s[0].split())[:120]}"')
    return Outcome(
        "fail",
        "No <h1> with text in the homepage's raw HTML.",
        "<h1>What you do, for whom — in one line</h1>",
        "html",
    )


@check(
    "response_time",
    CATEGORY,
    "Homepage responds quickly",
    weight=4,
    why="AI assistants fetch pages while the user waits and give up on slow sites.",
)
def response_time(ctx: SiteContext) -> Outcome:
    ms = ctx.homepage.elapsed_ms
    status = "pass" if ms < 1500 else "warn" if ms < 4000 else "fail"
    fix = "" if status == "pass" else (
        "Cache your HTML at the edge (CDN), and avoid slow server-side work on the homepage."
    )
    return Outcome(status, f"Homepage HTML downloaded in {ms} ms.", fix)


@check(
    "page_weight",
    CATEGORY,
    "HTML is a reasonable size",
    weight=3,
    why="Crawlers truncate very large HTML documents, so content near the end may be lost.",
)
def page_weight(ctx: SiteContext) -> Outcome:
    kb = ctx.homepage.size_bytes // 1024
    status = "pass" if kb < 1000 else "warn" if kb < 2500 else "fail"
    fix = "" if status == "pass" else (
        "Move inline scripts, styles and embedded JSON blobs out of the HTML into cached files."
    )
    return Outcome(status, f"Homepage HTML is {kb} KB.", fix)


@check(
    "key_pages_text",
    CATEGORY,
    "Key pages are readable without JavaScript",
    weight=5,
    why="Pricing, docs and about pages are what assistants quote — they need text in the HTML.",
)
def key_pages_text(ctx: SiteContext) -> Outcome:
    pages = [p for p in ctx.pages.values() if p.ok and p.is_html]
    if not pages:
        return Outcome("na", "No key pages (pricing, about, docs…) were found to check.")
    thin = [p.url for p in pages if word_count(ctx.visible_text(p)) < MIN_PAGE_WORDS]
    readable = len(pages) - len(thin)
    evidence = f"Readable text in the HTML on {readable} of {plural(len(pages), 'key page')}."
    if thin:
        evidence += f" Nearly empty: {examples(thin)}."
    status = ratio_status(readable / len(pages), 0.8, 0.4)
    return Outcome(status, evidence, "" if status == "pass" else SSR_FIX)
