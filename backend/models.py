"""Pydantic models for all request, response, and internal data shapes."""

from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl, model_validator


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    website_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None

    @model_validator(mode="after")
    def at_least_one_url(self) -> "AnalyzeRequest":
        if not self.website_url and not self.github_url:
            raise ValueError("At least one of website_url or github_url is required")
        return self


class CoreAction(BaseModel):
    """A single action/endpoint the product exposes."""

    name: str
    description: str
    http_method: str
    endpoint: str


class ProductAnalysis(BaseModel):
    """Internal model — output of LLM parsing, input to the artifact generator."""

    product_name: str
    product_description: str
    product_category: str
    core_actions: list[CoreAction]
    auth_method: str
    tech_stack: list[str]
    has_existing_openapi: bool
    has_existing_docs: bool
    webhook_support: bool
    missing_agent_features: list[str]
    recommendations: list[str]


class AuditBreakdown(BaseModel):
    """Boolean pass/fail for each scored agent-readiness check."""

    has_api: bool
    has_openapi_spec: bool
    has_llms_txt: bool
    has_structured_docs: bool
    has_api_key_auth: bool
    has_webhook_support: bool


class AuditScore(BaseModel):
    """Overall agent-readiness score out of `total`."""

    total: int = 100
    score: int
    breakdown: AuditBreakdown


class Artifacts(BaseModel):
    """The four generated output files, as raw strings."""

    llms_txt: str
    audit_md: str
    mcp_server_ts: str
    openapi_yaml: str


CheckStatus = Literal["pass", "warn", "fail", "na"]


class CheckResult(BaseModel):
    """One measured audit check, with the evidence behind it and how to fix it."""

    id: str
    category: str
    title: str
    status: CheckStatus
    weight: int
    evidence: str
    why: str
    fix: str = ""
    fix_language: str = "text"


class CategoryScore(BaseModel):
    """Sub-score for one audit category. `score` is None when every check was n/a."""

    id: str
    label: str
    description: str
    score: Optional[int]
    passed: int
    warned: int
    failed: int


class CrawlerAccess(BaseModel):
    """Whether one AI crawler/agent may read the site, per robots.txt."""

    bot: str
    owner: str
    purpose: Literal["training", "search", "user"]
    status: Literal["allowed", "partial", "blocked"]
    detail: str


class Audit(BaseModel):
    """The measured agent-readiness audit (deterministic — no LLM judgment in pass/fail)."""

    overall: int
    grade: str
    categories: list[CategoryScore]
    checks: list[CheckResult]
    crawler_access: list[CrawlerAccess]
    pages_scanned: list[str]
    critical_failures: list[str] = []  # titles of failed critical checks; they cap `overall`


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze. `audit_score` is the legacy 6-check rubric."""

    product_name: str
    product_summary: str
    artifacts: Artifacts
    audit_score: AuditScore
    audit: Audit
