"""Measured agent-readiness audit: runs every registered check and scores the results."""

from __future__ import annotations

import logging

from checks import (  # noqa: F401 — importing registers each module's checks
    agent_discovery,
    answerability,
    crawler_access,
    developer,
    rendering,
    structured_data,
)
from checks.base import REGISTRY, CheckSpec, Outcome
from checks.crawler_access import crawler_access_matrix
from models import Audit, CategoryScore, CheckResult
from site_fetcher import SiteContext

logger = logging.getLogger(__name__)

# id → (label, description, weight in the overall score)
CATEGORIES: dict[str, tuple[str, str, int]] = {
    "crawler": ("AI crawler access", "Can AI crawlers and assistants reach your pages?", 25),
    "rendering": ("Readable without JavaScript", "Can a bot that doesn't run JS read you?", 20),
    "structured": ("Machine-readable meaning", "Titles, meta tags and schema.org data.", 15),
    "agent": ("Agent discovery & usability", "llms.txt, and controls agents can operate.", 15),
    "answerability": ("Answers what people ask", "Prices, contact, FAQs in plain text.", 15),
    "developer": ("Developer & API", "Specs, docs and MCP for API products.", 10),
}
STATUS_POINTS = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
GRADES = ((90, "A"), (80, "B"), (65, "C"), (50, "D"), (0, "F"))
CRITICAL_CAP = 49


def _evaluate(spec: CheckSpec, ctx: SiteContext) -> Outcome:
    if spec.needs_website and not ctx.has_website:
        return Outcome("na", "No website was scanned.")
    if spec.applies is not None and not spec.applies(ctx):
        return Outcome("na", spec.na_reason)
    try:
        return spec.fn(ctx)
    except Exception:  # one broken check must not sink the whole report
        logger.exception("Check %s failed on %s", spec.id, ctx.url)
        return Outcome("na", "This check couldn't run on your site.")


def _category_score(category: str, results: list[CheckResult]) -> CategoryScore:
    label, description, _ = CATEGORIES[category]
    scored = [r for r in results if r.status != "na"]
    total_weight = sum(r.weight for r in scored)
    score = (
        round(100 * sum(r.weight * STATUS_POINTS[r.status] for r in scored) / total_weight)
        if total_weight
        else None
    )
    return CategoryScore(
        id=category,
        label=label,
        description=description,
        score=score,
        passed=sum(r.status == "pass" for r in results),
        warned=sum(r.status == "warn" for r in results),
        failed=sum(r.status == "fail" for r in results),
    )


def grade_for(score: int) -> str:
    """Letter grade for an overall score."""
    return next(letter for floor, letter in GRADES if score >= floor)


def run_audit(ctx: SiteContext) -> Audit:
    """
    Evaluate every check against `ctx` and score it.

    n/a checks don't count toward any score, and categories with no applicable checks are left
    out of the overall score, so (for example) a bakery isn't penalized for having no API.
    """
    results: list[CheckResult] = []
    order = list(CATEGORIES)
    for spec in sorted(REGISTRY, key=lambda s: order.index(s.category)):
        outcome = _evaluate(spec, ctx)
        results.append(
            CheckResult(
                id=spec.id,
                category=spec.category,
                title=spec.title,
                status=outcome.status,
                weight=spec.weight,
                evidence=outcome.evidence,
                why=spec.why,
                fix=outcome.fix if outcome.status in ("warn", "fail") else "",
                fix_language=outcome.fix_language,
            )
        )

    categories = [
        _category_score(cat, [r for r in results if r.category == cat]) for cat in CATEGORIES
    ]
    weighted = [(c.score, CATEGORIES[c.id][2]) for c in categories if c.score is not None]
    weight_sum = sum(w for _, w in weighted)
    overall = round(sum(s * w for s, w in weighted) / weight_sum) if weight_sum else 0

    critical_ids = {spec.id for spec in REGISTRY if spec.critical}
    critical_failures = [r.title for r in results if r.id in critical_ids and r.status == "fail"]
    if critical_failures:
        overall = min(overall, CRITICAL_CAP)

    pages = [ctx.homepage.url] if ctx.homepage else []
    pages += [p.url for p in ctx.pages.values() if p.ok]

    return Audit(
        overall=overall,
        grade=grade_for(overall),
        categories=categories,
        checks=results,
        crawler_access=crawler_access_matrix(ctx) if ctx.has_website else [],
        pages_scanned=pages,
        critical_failures=critical_failures,
    )
