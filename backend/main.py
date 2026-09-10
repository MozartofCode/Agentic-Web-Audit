"""FastAPI app init, CORS configuration, and route definitions."""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()  # must run before importing llm_analyzer, which reads GROQ_API_KEY at import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from artifact_generator import compute_audit_score, generate_artifacts
from crawler import crawl_website
from github_fetcher import fetch_github_repo
from llm_analyzer import analyze_product
from models import AnalyzeRequest, AnalyzeResponse

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


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Crawl the given website/repo, analyze with Groq, and generate all four artifacts."""
    website_url = str(request.website_url) if request.website_url else None
    github_url = str(request.github_url) if request.github_url else None

    website_data: dict = {}
    github_data: dict = {}

    if website_url and github_url:
        website_data, github_data = await asyncio.gather(
            crawl_website(website_url), fetch_github_repo(github_url)
        )
    elif website_url:
        website_data = await crawl_website(website_url)
    elif github_url:
        github_data = await fetch_github_repo(github_url)

    analysis = await analyze_product(website_data, github_data)

    artifacts = generate_artifacts(analysis, website_url)
    audit_score = compute_audit_score(analysis)

    return AnalyzeResponse(
        product_name=analysis.product_name,
        product_summary=analysis.product_description,
        artifacts=artifacts,
        audit_score=audit_score,
    )
