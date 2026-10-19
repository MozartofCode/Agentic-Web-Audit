"""Tests for the blind-reader test: fixed questions, quotes verified against the page text."""

from __future__ import annotations

from blind_reader import BLIND_QUESTIONS, normalize, quote_found, verify_preview
from models import AIPreview, AIQuestion
from prompts import MAX_HOMEPAGE_CHARS, homepage_text, prompt_texts

HOME = "https://bakery.test/"
PRICING = "https://bakery.test/pricing"
TEXTS = {
    HOME: "Tartine is a neighborhood sourdough bakery in San Francisco. "
    "Footer: Email hello@bakery.test or call (415) 555-0100.",
    PRICING: "Our country loaf costs $6 and a dozen croissants cost “$30”.",
}


def claim(qid: str, quote: str, source: str = "", answer: str = "An answer") -> AIQuestion:
    return AIQuestion(id=qid, answered=True, answer=answer, quote=quote, source=source)


def test_normalize_ignores_case_spacing_and_typographic_quotes() -> None:
    assert normalize("  Dozen  CROISSANTS cost “$30”. ") == "dozen croissants cost $30"


def test_quote_needs_enough_words_and_must_be_on_the_page() -> None:
    assert quote_found("country loaf costs $6", TEXTS[PRICING])
    assert not quote_found("costs $6", TEXTS[PRICING])  # too short to prove anything
    assert not quote_found("country loaf costs $7", TEXTS[PRICING])


def test_verify_builds_the_fixed_question_set_in_order() -> None:
    result = verify_preview(AIPreview(), TEXTS)
    assert [q.id for q in result.questions] == [qid for qid, _ in BLIND_QUESTIONS]
    assert all(not q.answered and not q.unverified for q in result.questions)


def test_verified_unverified_and_relocated_answers() -> None:
    preview = AIPreview(questions=[
        claim("price", "Our country loaf costs $6", PRICING, "A loaf is $6."),
        # Real quote, wrong page cited: accepted and re-pointed to the page it's on.
        claim("contact", "Email hello@bakery.test or call", PRICING),
        # Invented quote: rejected and flagged.
        claim("policy", "Full refunds within 30 days of purchase", HOME),
        claim("made-up-id", "Tartine is a neighborhood sourdough bakery", HOME),
    ])

    by_id = {q.id: q for q in verify_preview(preview, TEXTS).questions}

    assert by_id["price"].answered and by_id["price"].source == PRICING
    assert by_id["price"].answer == "A loaf is $6."
    assert by_id["contact"].answered and by_id["contact"].source == HOME
    assert not by_id["policy"].answered and by_id["policy"].unverified
    assert by_id["policy"].answer == "" and by_id["policy"].quote == ""
    assert "made-up-id" not in by_id  # only the fixed questions are reported


def test_github_only_scans_have_no_blind_reader_questions() -> None:
    preview = AIPreview(summary="A library.", questions=[claim("what", "x y z w")])
    assert verify_preview(preview, {}).questions == []


def test_prompt_texts_match_what_the_model_sees() -> None:
    website = {"url": HOME, "body_text": "b" * 5000, "footer_text": "Call (415) 555-0100"}
    pages = [{"url": PRICING, "kind": "pricing", "text": "p" * 5000}]

    texts = prompt_texts(website, pages)

    home = texts[HOME]
    assert home.endswith("Footer: Call (415) 555-0100")
    assert len(homepage_text(website)) <= MAX_HOMEPAGE_CHARS
    assert home.endswith(homepage_text(website))
    assert texts[PRICING] == "p" * 1500


def test_quotes_from_title_and_meta_description_count() -> None:
    website = {"url": HOME, "title": "Tartine Bakery",
               "description": "Sourdough loaves baked fresh every morning in the Mission.",
               "body_text": "Welcome."}
    preview = AIPreview(questions=[
        claim("what", "Sourdough loaves baked fresh every morning", HOME)])
    result = verify_preview(preview, prompt_texts(website, []))
    assert result.questions[0].answered


def test_quote_with_ellipsis_needs_every_fragment_on_the_page() -> None:
    page = "Special order cakes for your event. Gift cards: buy a Tartine gift card online."
    assert quote_found("Special order cakes ... buy a Tartine gift card online", page)
    assert not quote_found("Special order cakes ... free delivery citywide", page)
    assert not quote_found("Special order cakes ... cards", page)  # one-word fragment


def test_cloudflare_obfuscated_email_is_not_an_answer() -> None:
    # Cloudflare writes the placeholder with a non-breaking space.
    texts = {HOME: "Contact: Press [email\u00a0protected] Wholesale [email\u00a0protected]"}
    preview = AIPreview(
        questions=[claim("contact", "Press [email\u00a0protected] Wholesale", HOME)]
    )

    contact = verify_preview(preview, texts).questions[4]

    assert contact.id == "contact" and not contact.answered and not contact.unverified
    assert "Cloudflare" in contact.note
