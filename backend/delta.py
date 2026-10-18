"""Re-scan delta: what changed between a report and the previous report for the same domain."""

from __future__ import annotations

from datetime import datetime

from models import Audit, ReportDelta


def compute_delta(
    current: Audit, previous: Audit, previous_id: str, previous_created_at: datetime
) -> ReportDelta:
    """
    Points gained (or lost) and which checks flipped since `previous`.

    Checks are matched by id; a check that didn't exist in the older report is ignored, and an
    n/a check never counts as passing or regressing.
    """
    before = {c.id: c.status for c in previous.checks}
    now_passing: list[str] = []
    regressed: list[str] = []
    for check in current.checks:
        old = before.get(check.id)
        if old is None or old == "na" or check.status == "na":
            continue
        if check.status == "pass" and old in ("warn", "fail"):
            now_passing.append(check.title)
        elif old == "pass" and check.status in ("warn", "fail"):
            regressed.append(check.title)
    return ReportDelta(
        previous_report_id=previous_id,
        previous_overall=previous.overall,
        previous_created_at=previous_created_at,
        points=current.overall - previous.overall,
        now_passing=now_passing,
        regressed=regressed,
    )
