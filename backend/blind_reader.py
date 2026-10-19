"""
Blind-reader test: can an AI that sees only your raw HTML answer what customers ask?

The model gets exactly what a non-JavaScript AI crawler gets (the text of the HTML we
fetched) plus a FIXED list of customer questions, so it can't pick questions it knows the site
answers. For every answer it must copy a quote word for word from the page. Code then checks
that the quote really is on the cited page; an answer whose quote isn't found counts as not
answered. The LLM proposes, the code verifies.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from models import AIPreview, AIQuestion

# (id, question). The same eight for every site, chosen to cover what people ask an AI about
# any business: what, who, price, how to start, contact, where, what's offered, policies.
BLIND_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("what", "What does it do?"),
    ("audience", "Who is it for?"),
    ("price", "How much does it cost?"),
    ("start", "How do I sign up, buy or get started?"),
    ("contact", "How do I contact them or get support?"),
    ("location", "Where are they based, or which regions do they serve?"),
    ("offer", "What are the main products or features?"),
    ("policy", "What is the refund, cancellation or return policy?"),
)
MIN_QUOTE_WORDS = 4
MIN_FRAGMENT_WORDS = 2
# Cloudflare's email obfuscation replaces addresses in the HTML with this placeholder (with a
# non-breaking space), so a crawler never sees the address itself.
OBFUSCATED_EMAIL = "[email protected]"
OBFUSCATED_EMAIL_NOTE = (
    "Your email address is hidden by Cloudflare's email obfuscation, so AI sees "
    "\"[email protected]\" instead of the address. Turn off Email Address Obfuscation or add "
    "a contact page with a form or phone number."
)

_QUOTE_CHARS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                              "\u2013": "-", "\u2014": "-", "\u00a0": " "})


def normalize(text: str) -> str:
    """Lowercase, unify quotes/dashes, keep word characters, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_CHARS).lower()
    text = re.sub(r"[^\w$€£¥%.,'/-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip(" .,")


def quote_found(quote: str, page_text: str) -> bool:
    """
    True if `quote` appears in `page_text`.

    A quote may skip text with "..." — then every fragment must be on the page. Together the
    fragments need MIN_QUOTE_WORDS words, so a stray word or two proves nothing.
    """
    fragments = [normalize(f) for f in re.split(r"\.{3}|\u2026", quote)]
    fragments = [f for f in fragments if f]
    if not fragments or sum(len(f.split()) for f in fragments) < MIN_QUOTE_WORDS:
        return False
    if any(len(f.split()) < MIN_FRAGMENT_WORDS for f in fragments):
        return False
    haystack = normalize(page_text)
    return all(f in haystack for f in fragments)


def _locate(quote: str, source: str, texts_by_url: dict[str, str]) -> Optional[str]:
    """URL of the page the quote is on: the cited one if it matches, else any page we sent."""
    by_key = {url.rstrip("/"): url for url in texts_by_url}
    cited = by_key.get(source.rstrip("/")) if source else None
    if cited and quote_found(quote, texts_by_url[cited]):
        return cited
    return next((url for url, text in texts_by_url.items() if quote_found(quote, text)), None)


def verify_preview(preview: AIPreview, texts_by_url: dict[str, str]) -> AIPreview:
    """
    Rebuild the preview's questions as the fixed blind-reader set, each answer verified.

    `texts_by_url` must be exactly the page text the model was shown. With no website text
    (a GitHub-only scan) there is nothing to read blind, so the question list is empty.
    """
    if not texts_by_url:
        return preview.model_copy(update={"questions": []})

    claimed = {q.id: q for q in preview.questions if q.id}
    questions = []
    for qid, question in BLIND_QUESTIONS:
        raw = claimed.get(qid)
        claimed_answer = bool(raw and raw.answered and raw.answer.strip())
        url = _locate(raw.quote, raw.source, texts_by_url) if claimed_answer else None
        obfuscated = url is not None and normalize(OBFUSCATED_EMAIL) in normalize(raw.quote)
        if obfuscated:
            url = None
        questions.append(
            AIQuestion(
                id=qid,
                question=question,
                answered=url is not None,
                answer=raw.answer.strip() if url else "",
                quote=raw.quote.strip() if url else "",
                source=url or "",
                unverified=claimed_answer and url is None and not obfuscated,
                note=OBFUSCATED_EMAIL_NOTE if obfuscated else "",
            )
        )
    return preview.model_copy(update={"questions": questions})
