"""FastAPI app init, CORS configuration, and route definitions."""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()  # must run before importing llm_analyzer, which reads GROQ_API_KEY at import time

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from artifact_generator import compute_audit_score, generate_artifacts
from checks import run_audit
from fix_pack import build_fix_pack, upgrade_check_fixes
from github_fetcher import fetch_github_repo
from llm_analyzer import analyze_product
from models import AnalyzeRequest, AnalyzeResponse
from safety import enforce_rate_limit
from site_fetcher import SiteContext, fetch_site, key_page_excerpts, website_data_from_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentReady API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


@app.post(
    "/analyze", response_model=AnalyzeResponse, dependencies=[Depends(enforce_rate_limit)]
)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Crawl the website/repo, run the measured audit, one Groq call, and build the Fix-it pack."""
    website_url = str(request.website_url) if request.website_url else None
    github_url = str(request.github_url) if request.github_url else None

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
    )
