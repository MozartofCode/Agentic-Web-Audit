"""Fixture tests for every audit check, plus scoring rules."""

from __future__ import annotations

import json

import pytest

from checks import REGISTRY, _evaluate, grade_for, run_audit
from checks.crawler_access import crawler_access_matrix
from site_fetcher import SiteContext
from tests.helpers import ORIGIN, ctx, page, words

SPECS = {spec.id: spec for spec in REGISTRY}

PARAGRAPHS = "".join(f"<p>{words(15)}</p>" for _ in range(3))
GOOD_HEAD = (
    "<title>Tartine — sourdough bakery in San Francisco</title>"
    '<meta name="description" content="Neighborhood bakery baking sourdough, pastries and cakes '
    'daily in the Mission, San Francisco.">'
    '<meta property="og:title" content="Tartine"><meta property="og:description" content="x">'
    '<meta property="og:image" content="/og.png">'
    f'<link rel="canonical" href="{ORIGIN}/">'
)
ORG_LD = json.dumps(
    {"@context": "https://schema.org", "@graph": [
        {"@type": "Bakery", "name": "Tartine", "url": ORIGIN, "logo": ORIGIN + "/l.png",
         "telephone": "+1 415 555 0100"},
        {"@type": "FAQPage", "mainEntity": []},
    ]}
)
LD_SCRIPT = f'<script type="application/ld+json">{ORG_LD}</script>'


def status(check_id: str, context: SiteContext) -> str:
    return _evaluate(SPECS[check_id], context).status


def test_every_check_has_a_test() -> None:
    tested = {case[0] for case in CASES}
    assert tested == set(SPECS), f"untested: {set(SPECS) - tested}"


ROBOTS_BLOCK_ANSWER = "User-agent: OAI-SearchBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
ROBOTS_PARTIAL = "User-agent: PerplexityBot\nDisallow: /pricing\n"

CASES = [
    # A — crawler access
    ("robots_txt", ctx(robots_txt="User-agent: *\nAllow: /"), "pass"),
    ("robots_txt", ctx(), "warn"),
    ("answer_bots_allowed", ctx(robots_txt="User-agent: GPTBot\nDisallow: /\n"), "pass"),
    ("answer_bots_allowed", ctx(robots_txt=ROBOTS_BLOCK_ANSWER), "fail"),
    ("answer_bots_allowed", ctx(robots_txt=ROBOTS_PARTIAL,
                                pages={"pricing": page("<p>x</p>", "/pricing")}), "warn"),
    ("cdn_bot_blocking", ctx(), "pass"),
    ("cdn_bot_blocking", ctx(probe=page("Forbidden", status=403)), "warn"),
    ("cdn_bot_blocking", ctx(probe=page("<title>Just a moment...</title>")), "warn"),
    ("robots_meta", ctx(), "pass"),
    ("robots_meta", ctx(head='<meta name="robots" content="noindex, nofollow">'), "fail"),
    ("robots_meta", ctx(head='<meta name="robots" content="index, nosnippet">'), "warn"),
    ("sitemap", ctx(sitemap_url=ORIGIN + "/sitemap.xml", sitemap_in_robots=True), "pass"),
    ("sitemap", ctx(sitemap_url=ORIGIN + "/sitemap.xml"), "warn"),
    ("sitemap", ctx(), "fail"),
    ("sitemap_lastmod", ctx(sitemap_url="x", sitemap_has_lastmod=True), "pass"),
    ("sitemap_lastmod", ctx(sitemap_url="x"), "warn"),
    ("sitemap_lastmod", ctx(), "na"),
    # B — rendering
    ("raw_html_text", ctx(body=f"<p>{words(200)}</p>"), "pass"),
    ("raw_html_text", ctx(body=f"<p>{words(60)}</p>"), "warn"),
    ("raw_html_text", ctx(body='<div id="root"></div><script>render()</script>'), "fail"),
    ("h1_present", ctx(body="<h1>Sourdough daily</h1>"), "pass"),
    ("h1_present", ctx(body="<h1> </h1>"), "fail"),
    ("response_time", ctx(), "pass"),
    ("key_pages_text", ctx(pages={"about": page(f"<p>{words(150)}</p>", "/about")}), "pass"),
    ("key_pages_text", ctx(pages={"about": page('<div id="root"></div>', "/about")}), "fail"),
    ("key_pages_text", ctx(), "na"),
    ("page_weight", ctx(), "pass"),
    # C — structured data
    ("title_tag", ctx(head="<title>Tartine — sourdough bakery</title>"), "pass"),
    ("title_tag", ctx(head="<title>Home</title>"), "warn"),
    ("title_tag", ctx(), "fail"),
    ("meta_description", ctx(head=GOOD_HEAD), "pass"),
    ("meta_description", ctx(head='<meta name="description" content="Bakery">'), "warn"),
    ("meta_description", ctx(), "fail"),
    ("json_ld", ctx(head=LD_SCRIPT), "pass"),
    ("json_ld", ctx(head='<script type="application/ld+json">{bad json</script>'), "warn"),
    ("json_ld", ctx(), "fail"),
    ("organization_schema", ctx(head=LD_SCRIPT), "pass"),
    ("organization_schema", ctx(head='<script type="application/ld+json">'
                                     '{"@type": "Organization", "name": "X"}</script>'), "warn"),
    ("organization_schema", ctx(), "fail"),
    ("open_graph", ctx(head=GOOD_HEAD), "pass"),
    ("open_graph", ctx(head='<meta property="og:title" content="x">'), "warn"),
    ("open_graph", ctx(), "fail"),
    ("canonical", ctx(head=GOOD_HEAD), "pass"),
    ("canonical", ctx(), "warn"),
    ("html_lang", ctx(), "pass"),
    ("html_lang", ctx(html_attrs=""), "warn"),
    ("heading_structure", ctx(body="<h1>a</h1><h2>b</h2><h3>c</h3>"), "pass"),
    ("heading_structure", ctx(body="<h1>a</h1><h1>b</h1><h4>c</h4>"), "warn"),
    ("heading_structure", ctx(body="<p>no headings</p>"), "fail"),
    # D — agent discovery & usability
    ("llms_txt", ctx(llms_txt="# Tartine\n\n> Bakery\n\n- [Menu](https://x/menu)\n"), "pass"),
    ("llms_txt", ctx(llms_txt="# Tartine\n\nWe bake.\n"), "warn"),
    ("llms_txt", ctx(llms_txt="Tartine bakery"), "warn"),
    ("llms_txt", ctx(llms_txt_status=200), "fail"),
    ("llms_txt", ctx(), "fail"),
    ("llms_full_txt", ctx(llms_full_txt="# Everything"), "pass"),
    ("llms_full_txt", ctx(), "warn"),
    ("form_labels", ctx(body='<label for="e">Email</label><input id="e" type="email">'), "pass"),
    ("form_labels", ctx(body='<input type="email" placeholder="Email">'), "fail"),
    ("form_labels", ctx(body='<input type="hidden" name="csrf">'), "na"),
    ("control_names", ctx(body='<a href="/menu">Menu</a><button>Order</button>'), "pass"),
    ("control_names", ctx(body='<a href="/x"><svg></svg></a><button></button>'), "fail"),
    ("control_names", ctx(body="<p>nothing</p>"), "na"),
    ("clickable_divs", ctx(body='<button onclick="go()">Go</button>'), "pass"),
    ("clickable_divs", ctx(body='<div onclick="go()">Go</div>'), "warn"),
    ("captcha", ctx(), "pass"),
    ("captcha", ctx(body='<script src="https://www.google.com/recaptcha/api.js"></script>'),
     "warn"),
    ("image_alt", ctx(body='<img src="a.jpg" alt="Croissant"><img src="b.jpg" alt="">'), "pass"),
    ("image_alt", ctx(body='<img src="a.jpg"><img src="b.jpg">'), "fail"),
    ("image_alt", ctx(), "na"),
    # E — answerability
    ("pricing_info", ctx(pages={"pricing": page("<p>Pro plan $29/mo</p>", "/pricing")}), "pass"),
    ("pricing_info", ctx(pages={"pricing": page("<img src=p.png>", "/pricing")}), "warn"),
    ("pricing_info", ctx(body="<p>Croissant €3.50</p>"), "pass"),
    ("pricing_info", ctx(), "warn"),
    ("about_page", ctx(pages={"about": page("<p>Us</p>", "/about")}), "pass"),
    ("about_page", ctx(), "warn"),
    ("contact_info", ctx(body='<a href="mailto:hi@tartine.com">Email us</a>'), "pass"),
    ("contact_info", ctx(head=LD_SCRIPT), "pass"),
    ("contact_info", ctx(body="<p>Visit us</p>"), "fail"),
    ("faq_content", ctx(head=LD_SCRIPT), "pass"),
    ("faq_content", ctx(body="<h3>Open Sunday?</h3><h3>Vegan?</h3><h3>Delivery?</h3>"), "pass"),
    ("faq_content", ctx(), "warn"),
    ("plain_language", ctx(body=PARAGRAPHS), "pass"),
    ("plain_language", ctx(body=f"<p>{words(15)}</p>"), "warn"),
    ("plain_language", ctx(body="<p>Bread.</p>"), "fail"),
    # Developer track
    ("openapi_spec", ctx(well_known={"/openapi.json": "{}"}), "pass"),
    ("openapi_spec", ctx(github={"file_tree": ["api/openapi.yaml"]}), "pass"),
    ("openapi_spec", ctx(llm_says_api=True), "fail"),
    ("openapi_spec", ctx(), "na"),
    ("api_docs", ctx(llm_says_api=True, pages={"docs": page("<p>x</p>", "/docs")}), "pass"),
    ("api_docs", ctx(github={"readme": "x" * 2000}), "warn"),
    ("api_docs", ctx(url="https://docs.shop.example/en/home"), "pass"),
    ("api_docs", ctx(llm_says_api=True), "fail"),
    ("mcp_server", ctx(github={"file_tree": ["packages/mcp-server/index.ts"]}), "pass"),
    ("mcp_server", ctx(well_known={"/.well-known/mcp.json": "{}"}, llm_says_api=True), "pass"),
    ("mcp_server", ctx(llm_says_api=True), "warn"),
    ("auth_documented", ctx(github={"readme": "Send your API key as a Bearer token"}), "pass"),
    ("auth_documented", ctx(llm_says_api=True), "warn"),
    ("webhooks", ctx(github={"readme": "Configure webhooks for events"}), "pass"),
    ("webhooks", ctx(llm_says_api=True), "warn"),
    ("rate_limits", ctx(github={"readme": "Rate limits: 100 req/min"}), "pass"),
    ("rate_limits", ctx(llm_says_api=True), "warn"),
]


@pytest.mark.parametrize("check_id,context,expected", CASES)
def test_check(check_id: str, context: SiteContext, expected: str) -> None:
    outcome = _evaluate(SPECS[check_id], context)
    assert outcome.status == expected, outcome.evidence
    assert outcome.evidence
    if expected in ("warn", "fail"):
        assert outcome.fix, f"{check_id} {expected} has no fix"


def test_slow_and_heavy_pages() -> None:
    slow = ctx()
    slow.homepage.elapsed_ms = 5000
    assert status("response_time", slow) == "fail"
    heavy = ctx()
    heavy.homepage.size_bytes = 3_000_000
    assert status("page_weight", heavy) == "fail"


def test_github_only_scan_skips_website_checks() -> None:
    context = SiteContext(github={"readme": "API docs. API key auth.", "file_tree": []})
    audit = run_audit(context)
    web = [r for r in audit.checks if r.category != "developer"]
    assert all(r.status == "na" for r in web)
    assert [c.score for c in audit.categories if c.id != "developer"] == [None] * 5
    assert audit.crawler_access == []


def test_na_checks_do_not_count_and_dev_track_is_skipped_for_non_api_sites() -> None:
    audit = run_audit(ctx(body=f"<h1>Bakery</h1>{PARAGRAPHS}", head=GOOD_HEAD + LD_SCRIPT))
    dev = next(c for c in audit.categories if c.id == "developer")
    assert dev.score is None
    assert all(r.status == "na" for r in audit.checks if r.category == "developer")


def test_critical_failure_caps_overall() -> None:
    good = ctx(body=f"<h1>Bakery</h1>{PARAGRAPHS}{words(200)}", head=GOOD_HEAD + LD_SCRIPT)
    assert run_audit(good).critical_failures == []
    blocked = ctx(
        body=f"<h1>Bakery</h1>{PARAGRAPHS}{words(200)}", head=GOOD_HEAD + LD_SCRIPT,
        robots_txt=ROBOTS_BLOCK_ANSWER,
    )
    audit = run_audit(blocked)
    assert audit.critical_failures == ["AI assistants may read your pages"]
    assert audit.overall <= 49 and audit.grade == "F"


def test_fix_only_shown_for_failing_checks() -> None:
    audit = run_audit(ctx(head=GOOD_HEAD))
    assert all(r.fix == "" for r in audit.checks if r.status in ("pass", "na"))


def test_crawler_matrix_statuses() -> None:
    context = ctx(
        robots_txt="User-agent: GPTBot\nDisallow: /\n\nUser-agent: PerplexityBot\n"
        "Disallow: /pricing\n",
        pages={"pricing": page("<p>x</p>", "/pricing")},
    )
    matrix = {e.bot: e for e in crawler_access_matrix(context)}
    assert matrix["GPTBot"].status == "blocked"
    assert matrix["PerplexityBot"].status == "partial"
    assert "/pricing" in matrix["PerplexityBot"].detail
    assert matrix["ClaudeBot"].status == "allowed"
    assert {e.purpose for e in matrix.values()} == {"training", "search", "user"}


def test_grades() -> None:
    assert [grade_for(s) for s in (95, 85, 70, 55, 10)] == ["A", "B", "C", "D", "F"]
