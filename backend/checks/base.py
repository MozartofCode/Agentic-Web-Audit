"""Check registry: every audit check is a pure function over a SiteContext."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, NamedTuple, Optional

from site_fetcher import SiteContext


class Outcome(NamedTuple):
    """What a check function returns. `fix` is a copy-paste snippet or instruction."""

    status: str  # "pass" | "warn" | "fail" | "na"
    evidence: str
    fix: str = ""
    fix_language: str = "text"


@dataclass(frozen=True)
class CheckSpec:
    """Static metadata for one check plus the function that evaluates it."""

    id: str
    category: str
    title: str
    weight: int
    why: str
    fn: Callable[[SiteContext], Outcome]
    needs_website: bool = True
    applies: Optional[Callable[[SiteContext], bool]] = None
    na_reason: str = ""
    critical: bool = False


REGISTRY: list[CheckSpec] = []


def check(
    id: str,
    category: str,
    title: str,
    weight: int,
    why: str,
    needs_website: bool = True,
    applies: Optional[Callable[[SiteContext], bool]] = None,
    na_reason: str = "",
    critical: bool = False,
) -> Callable[[Callable[[SiteContext], Outcome]], Callable[[SiteContext], Outcome]]:
    """
    Decorator that registers a check function in REGISTRY (in definition order).

    A failing `critical` check caps the overall score: if AI can't reach or read the site,
    nothing else matters.
    """

    def register(fn: Callable[[SiteContext], Outcome]) -> Callable[[SiteContext], Outcome]:
        if any(spec.id == id for spec in REGISTRY):
            raise ValueError(f"Duplicate check id: {id}")
        REGISTRY.append(
            CheckSpec(
                id, category, title, weight, why, fn, needs_website, applies, na_reason, critical
            )
        )
        return fn

    return register


def ratio_status(ratio: float, pass_at: float, warn_at: float) -> str:
    """Map a 0–1 ratio onto pass/warn/fail thresholds."""
    if ratio >= pass_at:
        return "pass"
    if ratio >= warn_at:
        return "warn"
    return "fail"


def plural(n: int, word: str, plural_word: str = "") -> str:
    """'1 page', '3 pages'."""
    return f"{n} {word if n == 1 else (plural_word or word + 's')}"


def examples(items: list[str], limit: int = 3) -> str:
    """Comma-joined preview of a list, e.g. 'a, b, c (+4 more)'."""
    shown = ", ".join(items[:limit])
    return shown + (f" (+{len(items) - limit} more)" if len(items) > limit else "")
