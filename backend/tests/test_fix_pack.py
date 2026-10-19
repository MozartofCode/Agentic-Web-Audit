"""Tests for the Fix-it pack, platform detection, Top fixes and the AI preview grounding."""

from __future__ import annotations

import json
import re
from urllib.robotparser import RobotFileParser

import pytest

from checks import REGISTRY, run_audit
from fix_pack import ANSWER_BOTS, build_fix_pack, json_ld, meta_tags, site_faqs, suggested_robots
from fix_pack import llms_txt as build_llms_txt
from fix_pack import robots_patch, upgrade_check_fixes
from models import AIPreview, AIQuestion, AIUnknown, Artifacts, ProductAnalysis
from platform_detect import detect_platform
from prompts import build_analysis_prompt
from site_fetcher import SiteContext, key_page_excerpts
from tests.helpers import ORIGIN, ctx, page, words

ARTIFACTS = Artifacts(llms_txt="# Legacy\n", audit_md="", mcp_server_ts="// mcp",
                      openapi_yaml="openapi: 3.0.0")


def analysis(**overrides: object) -> ProductAnalysis:
    fields: dict = dict(
        product_name="Tartine",
        product_description="Neighborhood sourdough bakery in San Francisco's Mission district.",
        product_category="Other",
        core_actions=[],
        auth_method="none",
        tech_stack=[],
        has_existing_openapi=False,
        has_existing_docs=False,
        webhook_support=False,
        missing_agent_features=[],
        recommendations=[],
        business_type="local_business",
    )
    fields.update(overrides)
    return ProductAnalysis(**fields)


def bakery_site(**fields: object) -> SiteContext:
    pricing = page(
        "<html><head><title>Prices | Tartine</title>"
        '<meta name="description" content="Bread from $6, pastries from $4."></head>'
        f"<body><h1>Prices</h1><p>Country loaf $6. {words(120)}</p></body></html>",
        "/pricing",
    )
    about = page(
        "<html><head><title>About us — Tartine</title></head><body>"
        "<h2>Do you deliver?</h2><p>Yes, we deliver within San Francisco every day.</p>"
        f"<p>{words(120)}</p></body></html>",
        "/about",
    )
    return ctx(
        body=f"<h1>Tartine</h1><p>{words(200)}</p>"
        '<a href="mailto:hi@tartine.example">Email</a>'
        '<a href="https://www.instagram.com/tartine">Instagram</a>',
        head="<title>Tartine</title>",
        pages={"pricing": pricing, "about": about},
        **fields,
    )


# --- AI preview -----------------------------------------------------------------------------


def test_ai_preview_cleaned_trims_and_caps() -> None:
    preview = AIPreview(
        summary=" Tartine is a bakery. ",
        unknowns=[AIUnknown(fact="Opening hours", fix="List hours"), AIUnknown(fact=" ")],
        questions=[AIQuestion(id=f"q{i}") for i in range(10)],
    )
    cleaned = preview.cleaned()
    assert cleaned.summary == "Tartine is a bakery."
    assert [u.fact for u in cleaned.unknowns] == ["Opening hours"]
    assert len(cleaned.questions) == 8


def test_ai_preview_defaults_when_llm_omits_it() -> None:
    result = analysis()
    assert result.ai_preview == AIPreview()
    assert analysis(business_type="bakery").business_type == "other"


def test_prompt_includes_key_pages_for_citation() -> None:
    site = bakery_site()
    excerpts = key_page_excerpts(site)
    assert {e["kind"] for e in excerpts} == {"pricing", "about"}
    prompt = build_analysis_prompt({"url": site.url, "title": "Tartine"}, {}, excerpts)
    assert ORIGIN + "/pricing" in prompt and "Country loaf $6" in prompt
    assert '"ai_preview"' in prompt
    assert '"price": How much does it cost?' in prompt and "copied\n  EXACTLY" in prompt


# --- Top fixes ------------------------------------------------------------------------------


def test_every_check_declares_a_valid_effort() -> None:
    assert {spec.effort for spec in REGISTRY} <= {"minutes", "hour", "dev"}


def test_top_fixes_ranked_with_points() -> None:
    audit = run_audit(ctx(body=f"<p>{words(200)}</p>"))
    fixes = audit.top_fixes
    assert 1 <= len(fixes) <= 5
    assert all(f.status in ("warn", "fail") and f.fix and f.points >= 1 for f in fixes)
    # Ranked by impact: llms.txt is a low-weight proposal now and must not lead the list,
    # and slow light fixes stay out of the top five.
    ids = [f.check_id for f in fixes]
    assert ids[0] != "llms_txt"
    assert "heading_structure" not in ids


def test_critical_fix_is_first_and_unlocks_the_cap() -> None:
    blocked = ctx(
        body=f"<h1>Bakery</h1><p>{words(200)}</p>",
        robots_txt="User-agent: OAI-SearchBot\nDisallow: /\n",
    )
    audit = run_audit(blocked)
    assert audit.top_fixes[0].check_id == "answer_bots_allowed"
    assert audit.overall <= 49
    assert audit.top_fixes[0].points >= 1


# --- llms.txt -------------------------------------------------------------------------------


def test_llms_txt_follows_spec_and_uses_crawled_pages() -> None:
    site = bakery_site(sitemap_urls=[ORIGIN + "/our-story", ORIGIN + "/tag/bread",
                                     ORIGIN + "/pricing"])
    preview = AIPreview(questions=[AIQuestion(question="Do they deliver?", answered=True,
                                              answer="Yes, within San Francisco.",
                                              source=ORIGIN + "/about")])
    text = build_llms_txt(site, analysis(ai_preview=preview))
    lines = text.splitlines()
    assert lines[0] == "# Tartine"
    assert lines[2].startswith("> Neighborhood sourdough bakery")
    assert "## Main pages" in text and "## Optional" in text
    assert f"- [Home]({ORIGIN}/)" in text
    assert f"- [Prices]({ORIGIN}/pricing): Bread from $6, pastries from $4." in text
    assert f"- [About us]({ORIGIN}/about)" in text
    assert f"- [Our story]({ORIGIN}/our-story)" in text
    assert "/tag/bread" not in text
    assert text.count(f"({ORIGIN}/pricing)") == 1
    assert "- Do they deliver? Yes, within San Francisco." in text


# --- robots.txt -----------------------------------------------------------------------------


def _parser(text: str) -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    return parser


def test_robots_patch_unblocks_answer_bots_only() -> None:
    robots = (
        "User-agent: OAI-SearchBot\nUser-agent: GPTBot\nDisallow: /\n\n"
        "User-agent: PerplexityBot\nDisallow: /\n\n"
        "User-agent: *\nDisallow: /admin\n"
    )
    site = ctx(robots_txt=robots, sitemap_url=ORIGIN + "/sitemap.xml")
    suggested = suggested_robots(site)
    parser = _parser(suggested)
    assert all(parser.can_fetch(bot, "/") for bot in ANSWER_BOTS)
    assert not parser.can_fetch("GPTBot", "/")  # training choice left alone
    assert not parser.can_fetch("Googlebot", "/admin")
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in suggested

    diff = robots_patch(site)
    assert diff.splitlines()[0] == "--- robots.txt (current)"
    assert "-User-agent: OAI-SearchBot" in diff
    assert "-User-agent: PerplexityBot" in diff


def test_robots_patch_handles_wildcard_block_and_keeps_private_paths() -> None:
    site = ctx(robots_txt="User-agent: *\nDisallow: /\nDisallow: /admin\n")
    suggested = suggested_robots(site)
    parser = _parser(suggested)
    assert parser.can_fetch("Claude-User", "/pricing")
    assert not parser.can_fetch("Claude-User", "/admin")
    assert not parser.can_fetch("Googlebot", "/")
    assert "opt out of AI model training" not in suggested  # `*` already blocks them


def test_robots_patch_offers_training_opt_out_commented_out() -> None:
    suggested = suggested_robots(ctx(robots_txt="User-agent: *\nAllow: /\n"))
    assert "# User-agent: GPTBot" in suggested
    assert _parser(suggested).can_fetch("GPTBot", "/")


def test_robots_patch_creates_file_when_missing_and_noop_when_fine() -> None:
    assert robots_patch(ctx()).startswith("# No robots.txt found")
    fine = (
        "User-agent: *\nAllow: /\n\nSitemap: https://shop.example/sitemap.xml\n\n"
        + "".join(f"User-agent: {b}\n" for b in
                  ("GPTBot", "ClaudeBot", "Google-Extended", "Applebot-Extended", "CCBot",
                   "Bytespider", "meta-externalagent"))
        + "Disallow: /\n"
    )
    assert "No changes" in robots_patch(ctx(robots_txt=fine))


# --- JSON-LD and meta tags ------------------------------------------------------------------


def _ld_blocks(html: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(r'ld\+json">\n(.*?)\n</script>', html, re.S)]


def test_json_ld_local_business_with_site_faqs() -> None:
    site = bakery_site()
    blocks = _ld_blocks(json_ld(site, analysis()))
    types = [b["@type"] for b in blocks]
    assert types == ["LocalBusiness", "FAQPage"]
    org = blocks[0]
    assert org["email"] == "hi@tartine.example"
    assert org["sameAs"] == ["https://www.instagram.com/tartine"]
    assert org["address"]["streetAddress"] == "TODO"
    faq = blocks[1]["mainEntity"][0]
    assert faq["name"] == "Do you deliver?"
    assert faq["acceptedAnswer"]["text"].startswith("Yes, we deliver")


def test_json_ld_software_offer_and_skips_existing_types() -> None:
    ld = json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": "X"})
    site = bakery_site(
        homepage=page(f'<html><head><script type="application/ld+json">{ld}</script></head>'
                      f"<body><p>{words(10)}</p></body></html>")
    )
    blocks = _ld_blocks(json_ld(site, analysis(business_type="saas")))
    assert [b["@type"] for b in blocks] == ["FAQPage", "SoftwareApplication"]
    offer = blocks[1]["offers"]
    assert offer == {"@type": "Offer", "price": "6", "priceCurrency": "USD",
                     "url": ORIGIN + "/pricing"}


def test_site_faqs_from_details_and_definition_lists() -> None:
    site = ctx(body="<details><summary>Can I return it?</summary>Yes, within 30 days of "
                    "purchase.</details><dl><dt>Do you ship abroad?</dt><dd>We ship to the "
                    "EU and UK.</dd></dl>")
    assert site_faqs(site) == [
        ("Can I return it?", "Yes, within 30 days of purchase."),
        ("Do you ship abroad?", "We ship to the EU and UK."),
    ]


def test_meta_tags_only_adds_missing_or_weak_tags() -> None:
    site = ctx(head='<title>Home</title><meta property="og:title" content="T">', html_attrs="")
    audit = run_audit(site)
    statuses = {c.id: c.status for c in audit.checks}
    block = meta_tags(site, analysis(product_description='Sourdough & "cakes" daily.'), statuses)
    assert "<title>Tartine — Sourdough &amp; &quot;cakes&quot; daily</title>" in block
    assert 'content="Sourdough &amp; &quot;cakes&quot; daily."' in block
    assert 'property="og:title"' not in block
    assert 'property="og:image"' in block and '<html lang="en">' in block
    assert '<link rel="canonical"' in block


def test_meta_title_drops_repeated_brand_name() -> None:
    site = ctx(head="<title>Home</title>")
    statuses = {c.id: c.status for c in run_audit(site).checks}
    long = analysis(product_description="Tartine offers modern craft bakery goods with online "
                    "ordering and nationwide shipping across the Bay Area.")
    block = meta_tags(site, long, statuses)
    title = re.search(r"<title>(.*)</title>", block)[1]
    assert title.startswith("Tartine — Modern craft bakery goods")
    assert len(title) <= 60 and not title.endswith((" with", " and", "…"))


# --- Platform detection and the pack --------------------------------------------------------


@pytest.mark.parametrize(
    "head,headers,expected",
    [
        ('<meta name="generator" content="WordPress 6.6">', {}, "wordpress"),
        ('<link rel="stylesheet" href="//cdn.shopify.com/s/theme.css">', {}, "shopify"),
        ("", {"x-wix-request-id": "1"}, "wix"),
        ('<script src="https://static1.squarespace.com/x.js"></script>', {}, "squarespace"),
        ('<html data-wf-site="abc">', {}, "webflow"),
        ('<link href="https://framerusercontent.com/x.css">', {}, "framer"),
        ('<script id="__NEXT_DATA__"></script>', {}, "nextjs"),
        ('<meta name="generator" content="WordPress"><script src="//cdn.shopify.com/b.js">',
         {}, "wordpress"),
        ("", {}, None),
    ],
)
def test_detect_platform(head: str, headers: dict[str, str], expected: str | None) -> None:
    site = ctx(head=head)
    site.homepage.headers.update(headers)
    platform = detect_platform(site)
    assert (platform.id if platform else None) == expected
    if platform:
        assert platform.evidence


def test_fix_pack_for_shopify_store_hides_developer_files() -> None:
    site = bakery_site()
    site.homepage.text += '<script src="//cdn.shopify.com/s/x.js"></script>'
    pack = build_fix_pack(site, analysis(business_type="ecommerce"), run_audit(site), ARTIFACTS)
    assert pack.platform.name == "Shopify"
    assert not pack.developer_track
    assert [f.id for f in pack.files] == ["llms_txt", "robots_txt", "json_ld", "meta_tags"]
    robots = next(f for f in pack.files if f.id == "robots_txt")
    assert robots.language == "diff" and "robots.txt.liquid" in " ".join(robots.how_to)
    assert all(f.how_to for f in pack.files)


def test_llms_txt_fix_upgraded_everywhere() -> None:
    site = bakery_site()
    audit = run_audit(site)
    pack = build_fix_pack(site, analysis(), audit, ARTIFACTS)
    upgrade_check_fixes(audit, pack)
    check = next(c for c in audit.checks if c.id == "llms_txt")
    assert "> Neighborhood sourdough bakery" in check.fix
    top = next((f for f in audit.top_fixes if f.check_id == "llms_txt"), None)
    assert top is None or top.fix == check.fix


def test_fix_pack_developer_track_adds_openapi_and_mcp() -> None:
    site = bakery_site(llm_says_api=True)
    pack = build_fix_pack(site, analysis(business_type="developer_tool"), run_audit(site),
                          ARTIFACTS)
    assert pack.developer_track
    dev = [f for f in pack.files if f.developer]
    assert [f.filename for f in dev] == ["openapi.yaml", "mcp_server.ts"]


def test_fix_pack_github_only_uses_repo_llms_txt() -> None:
    site = SiteContext(github={"readme": "API", "file_tree": []})
    pack = build_fix_pack(site, analysis(), run_audit(site), ARTIFACTS)
    assert pack.files[0].content == "# Legacy\n"
    assert pack.platform is None and pack.developer_track
