"""Shareable images for a report: the README badge (SVG) and the social preview card (PNG)."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from models import Audit

# Colors from the UI.md token set.
BG_BASE = "#09090b"
BG_ELEVATED = "#18181b"
BORDER = "#2a2a2e"
DOT = "#17171a"
TEXT_PRIMARY = "#f4f4f5"
TEXT_SECONDARY = "#a1a1aa"
TEXT_MUTED = "#71717a"
ACCENT = "#06b6d4"
SCORE_GOOD = "#22c55e"
SCORE_WARN = "#f59e0b"
SCORE_BAD = "#ef4444"
NOT_SCANNED = "#52525b"

OG_WIDTH, OG_HEIGHT = 1200, 630
BADGE_HEIGHT = 20
BADGE_PADDING = 6


def score_color(score: Optional[int]) -> str:
    """Same thresholds as the results UI (frontend/src/status.js)."""
    if score is None:
        return NOT_SCANNED
    if score >= 70:
        return SCORE_GOOD
    if score >= 40:
        return SCORE_WARN
    return SCORE_BAD


def _text_width(text: str) -> int:
    """Approximate width of `text` in 11px Verdana (what badge renderers fall back to)."""
    width = 0.0
    for ch in text:
        if ch in " ·":
            width += 3.9
        elif ch in "-.":
            width += 4.6
        elif ch.isupper() or ch.isdigit():
            width += 7.5
        else:
            width += 6.6
    return round(width)


def badge_svg(score: Optional[int]) -> str:
    """Shields-style badge reading "AI-Ready · NN" (or "not scanned" with no report yet)."""
    label = "AI-Ready"
    value = str(score) if score is not None else "not scanned"
    label_w = _text_width(label) + 2 * BADGE_PADDING
    value_w = _text_width(value) + 2 * BADGE_PADDING
    total = label_w + value_w
    value_text = BG_BASE if score is not None else TEXT_PRIMARY
    title = f"AI-Ready · {score}/100" if score is not None else "AI-Ready · not scanned yet"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{BADGE_HEIGHT}" '
        f'role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>"
        f'<clipPath id="r"><rect width="{total}" height="{BADGE_HEIGHT}" rx="3"/></clipPath>'
        f'<g clip-path="url(#r)">'
        f'<rect width="{label_w}" height="{BADGE_HEIGHT}" fill="{BG_ELEVATED}"/>'
        f'<rect x="{label_w}" width="{value_w}" height="{BADGE_HEIGHT}" '
        f'fill="{score_color(score)}"/></g>'
        f'<g font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" '
        f'text-anchor="middle">'
        f'<text x="{label_w / 2}" y="14" fill="{TEXT_PRIMARY}">{label}</text>'
        f'<text x="{label_w + value_w / 2}" y="14" fill="{value_text}" '
        f'font-weight="bold">{escape(value)}</text>'
        f"</g></svg>"
    )


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)  # Pillow's bundled scalable font, no files needed


def _fit(draw: ImageDraw.ImageDraw, text: str, size: int, max_width: int) -> tuple[str, int]:
    """Shrink (then truncate) `text` until it fits in `max_width` pixels."""
    while size > 28 and draw.textlength(text, font=_font(size)) > max_width:
        size -= 4
    while len(text) > 4 and draw.textlength(text, font=_font(size)) > max_width:
        text = text[:-2].rstrip(".") + "…"
    return text, size


def og_image_png(domain: str, audit: Audit, created_at: datetime) -> bytes:
    """1200×630 social card: domain, overall score and grade, and the category bars."""
    img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_BASE)
    draw = ImageDraw.Draw(img)
    for x in range(16, OG_WIDTH, 32):
        for y in range(16, OG_HEIGHT, 32):
            draw.rectangle((x, y, x + 1, y + 1), fill=DOT)

    left = 72
    draw.text((left, 56), "AgentReady", font=_font(30), fill=ACCENT)
    name, size = _fit(draw, domain, 60, 560)
    draw.text((left, 120), name, font=_font(size), fill=TEXT_PRIMARY)
    draw.text((left, 222), "AI Readiness Score", font=_font(28), fill=TEXT_SECONDARY)

    color = score_color(audit.overall)
    score_text = str(audit.overall)
    big = _font(190)
    draw.text((left - 8, 262), score_text, font=big, fill=color)
    score_w = draw.textlength(score_text, font=big)
    draw.text((left + score_w + 8, 400), "/100", font=_font(44), fill=TEXT_MUTED)

    grade_x, grade_y = left + score_w + 8, 300
    draw.rounded_rectangle(
        (grade_x, grade_y, grade_x + 84, grade_y + 76), 8, outline=BORDER, width=2
    )
    draw.text((grade_x + 42, grade_y + 38), audit.grade, font=_font(48), fill=color, anchor="mm")

    draw.text(
        (left, 560),
        f"Scanned {created_at:%b} {created_at.day}, {created_at.year}"
        " · see how AI assistants read your site",
        font=_font(22),
        fill=TEXT_MUTED,
    )

    col_x, col_w, row_y = 700, 428, 140
    for category in [c for c in audit.categories if c.score is not None][:6]:
        draw.text((col_x, row_y), category.label, font=_font(24), fill=TEXT_SECONDARY)
        draw.text(
            (col_x + col_w, row_y), str(category.score), font=_font(24),
            fill=score_color(category.score), anchor="ra",
        )
        bar_y = row_y + 38
        draw.rounded_rectangle((col_x, bar_y, col_x + col_w, bar_y + 8), 4, fill=BG_ELEVATED)
        filled = round(col_w * category.score / 100)
        if filled > 0:
            draw.rounded_rectangle(
                (col_x, bar_y, col_x + max(filled, 8), bar_y + 8), 4,
                fill=score_color(category.score),
            )
        row_y += 68

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
