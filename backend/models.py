"""Pydantic models for all request, response, and internal data shapes."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class CoreAction(BaseModel):
    """A single action/endpoint the product exposes."""

    name: str
    description: str
    http_method: str
    endpoint: str


MAX_AI_QUESTIONS = 8
MAX_AI_UNKNOWNS = 5


class AIUnknown(BaseModel):
    """A fact an AI assistant couldn't determine from the site, and how to state it."""

    fact: str
    fix: str = ""


class AIQuestion(BaseModel):
    """One blind-reader question and whether the raw HTML answers it (see blind_reader.py)."""

    id: str = ""  # blind_reader.BLIND_QUESTIONS id
    question: str = ""
    answered: bool = False  # True only when the quote was found on the cited page
    answer: str = ""  # short answer drawn from the site; empty when not answered
    quote: str = ""  # words copied from the page, verified by code
    source: str = ""  # URL of the scanned page the quote is on
    unverified: bool = False  # the model claimed an answer but its quote wasn't on the page
    note: str = ""  # why a seemingly answered question doesn't count (e.g. hidden email)


class AIPreview(BaseModel):
    """'How AI sees you': the one-call LLM read of the scanned pages (qualitative, not scored)."""

    summary: str = ""
    unknowns: list[AIUnknown] = []
    questions: list[AIQuestion] = []

    def cleaned(self) -> "AIPreview":
        """Copy with blank entries dropped and lists capped."""
        unknowns = [u for u in self.unknowns if u.fact.strip()][:MAX_AI_UNKNOWNS]
        return AIPreview(
            summary=self.summary.strip(), unknowns=unknowns,
            questions=self.questions[:MAX_AI_QUESTIONS],
        )


BusinessType = Literal[
    "local_business", "ecommerce", "saas", "developer_tool", "publisher", "nonprofit", "other"
]


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
    business_type: BusinessType = "other"
    ai_preview: AIPreview = AIPreview()

    @field_validator("business_type", mode="before")
    @classmethod
    def unknown_business_type_is_other(cls, value: object) -> object:
        allowed = BusinessType.__args__  # type: ignore[attr-defined]
        return value if value in allowed else "other"


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


Effort = Literal["minutes", "hour", "dev"]


class TopFix(BaseModel):
    """One of the highest-value fixes, with its estimated score gain."""

    check_id: str
    title: str
    category: str
    status: Literal["warn", "fail"]
    effort: Effort
    points: int  # estimated overall-score gain if this check passed
    evidence: str
    fix: str
    fix_language: str = "text"


class Audit(BaseModel):
    """The measured agent-readiness audit (deterministic — no LLM judgment in pass/fail)."""

    overall: int
    grade: str
    categories: list[CategoryScore]
    checks: list[CheckResult]
    crawler_access: list[CrawlerAccess]
    pages_scanned: list[str]
    critical_failures: list[str] = []  # titles of failed critical checks; they cap `overall`
    top_fixes: list[TopFix] = []


class Platform(BaseModel):
    """The CMS / site builder / framework the site appears to run on."""

    id: str
    name: str
    evidence: str


class FixPackFile(BaseModel):
    """One paste-ready file or snippet in the Fix-it pack."""

    id: str
    label: str
    filename: str
    language: str
    content: str
    description: str
    how_to: list[str] = []  # platform-specific steps to install it
    developer: bool = False  # developer-track artifact (OpenAPI, MCP)


class FixPack(BaseModel):
    """Paste-ready fixes built from the crawled pages, tailored to the detected platform."""

    platform: Optional[Platform] = None
    developer_track: bool = False
    files: list[FixPackFile]


class ReportDelta(BaseModel):
    """How a report changed since the previous report for the same domain."""

    previous_report_id: str
    previous_overall: int
    previous_created_at: datetime
    points: int  # current overall minus previous overall
    now_passing: list[str] = []  # titles of checks that were warn/fail and now pass
    regressed: list[str] = []  # titles of checks that passed before and now don't


# Fields describing a saved report rather than the scan itself; never stored in the payload.
REPORT_META_FIELDS = {"report_id", "created_at", "cached", "delta"}


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze and GET /reports/{id}. `audit_score` is legacy."""

    product_name: str
    product_summary: str
    artifacts: Artifacts
    audit_score: AuditScore
    audit: Audit
    ai_preview: AIPreview
    fix_pack: FixPack
    website_url: Optional[str] = None
    github_url: Optional[str] = None
    report_id: Optional[str] = None  # None when this server doesn't save reports
    created_at: Optional[datetime] = None
    cached: bool = False  # True when this is a saved scan of the same URL from the last 24h
    delta: Optional[ReportDelta] = None


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze. `refresh` skips the 24h cache (the Re-scan button)."""

    website_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    refresh: bool = False

    @model_validator(mode="after")
    def at_least_one_url(self) -> "AnalyzeRequest":
        if not self.website_url and not self.github_url:
            raise ValueError("At least one of website_url or github_url is required")
        return self


class CompareRequest(BaseModel):
    """Request body for POST /compare: exactly two websites, scanned side by side."""

    website_urls: list[HttpUrl] = Field(min_length=2, max_length=2)


class CompareResponse(BaseModel):
    """Response body for POST /compare: one full report per site, in request order."""

    reports: list[AnalyzeResponse]
