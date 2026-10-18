"""The scan pipeline: fetch the site/repo, run the measured audit, one Groq call, Fix-it pack."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from artifact_generator import compute_audit_score, generate_artifacts
from checks import run_audit
from fix_pack import build_fix_pack, upgrade_check_fixes
from github_fetcher import fetch_github_repo
from llm_analyzer import analyze_product
from models import AnalyzeResponse
from site_fetcher import SiteContext, fetch_site, key_page_excerpts, website_data_from_context

logger = logging.getLogger(__name__)


async def run_scan(website_url: Optional[str], github_url: Optional[str]) -> AnalyzeResponse:
    """Run one full analysis (exactly one LLM call). Raises HTTPException on user errors."""
    ctx = SiteContext()
    github_data: dict = {}

    if website_url and github_url:
        ctx, github_data = await asyncio.gather(
            fetch_site(website_url), fetch_github_repo(github_url)
        )
    elif website_url:
        ctx = await fetch_site(website_url)
    elif github_url:
        github_data = await fetch_github_repo(github_url)

    website_data = website_data_from_context(ctx) if ctx.has_website else {}
    pages = key_page_excerpts(ctx) if ctx.has_website else []
    analysis = await analyze_product(website_data, github_data, pages)

    ctx.github = github_data
    ctx.llm_says_api = analysis.product_category.strip().upper() == "API"
    audit = run_audit(ctx)

    has_llms_txt = bool(website_data.get("has_llms_txt") or github_data.get("has_llms_txt"))
    artifacts = generate_artifacts(
        analysis, website_url, has_llms_txt, website_data.get("blocked_ai_bots", [])
    )
    audit_score = compute_audit_score(analysis, has_llms_txt)
    fix_pack = build_fix_pack(ctx, analysis, audit, artifacts)
    upgrade_check_fixes(audit, fix_pack)
    llms_file = next(f for f in fix_pack.files if f.id == "llms_txt")
    artifacts.llms_txt = llms_file.content  # one llms.txt everywhere: the crawled-pages version

    return AnalyzeResponse(
        product_name=analysis.product_name,
        product_summary=analysis.product_description,
        artifacts=artifacts,
        audit_score=audit_score,
        audit=audit,
        ai_preview=analysis.ai_preview,
        fix_pack=fix_pack,
        website_url=website_url,
        github_url=github_url,
    )
