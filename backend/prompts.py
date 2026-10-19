"""All prompt strings for the Groq LLM analysis call."""

from __future__ import annotations

from blind_reader import BLIND_QUESTIONS

SYSTEM_PROMPT = """You are an expert at analyzing websites, software products and APIs, and at
predicting how AI assistants (ChatGPT, Claude, Perplexity) would describe them.
You will be given content scraped from a website and/or GitHub repository.
Base every statement ONLY on the content provided. Never invent facts.
Return ONLY valid JSON. No explanation. No markdown. No code fences. Just JSON."""

MAX_PAGE_CHARS = 1500
MAX_HOMEPAGE_CHARS = 3000


def homepage_text(website_data: dict) -> str:
    """Homepage main text plus its footer (contact details), within MAX_HOMEPAGE_CHARS."""
    footer = website_data.get("footer_text", "")
    room = MAX_HOMEPAGE_CHARS - (len(footer) + 9 if footer else 0)
    body = website_data.get("body_text", "")[:room]
    return f"{body} Footer: {footer}" if footer else body


def prompt_texts(website_data: dict, pages: list[dict]) -> dict[str, str]:
    """
    URL → the exact page text the model is shown (truncated as in the prompt).

    The blind-reader check verifies quotes against this, so it must match the prompt.
    """
    texts: dict[str, str] = {}
    # The prompt shows the homepage title, meta description and headings on their own lines;
    # they're real text in the raw HTML, so quotes from them count too.
    shown = [
        website_data.get("title", ""),
        website_data.get("description", ""),
        " | ".join(website_data.get("headings", [])[:10]),
        homepage_text(website_data),
    ]
    text = " ".join(part for part in shown if part)
    if website_data.get("url") and text.strip():
        texts[website_data["url"]] = text
    for page in pages:
        texts.setdefault(page["url"], page["text"][:MAX_PAGE_CHARS])
    return texts


def _questions_block() -> str:
    return "\n".join(f'  - "{qid}": {question}' for qid, question in BLIND_QUESTIONS)


def _pages_block(pages: list[dict]) -> str:
    """Key pages as labelled excerpts the model can cite by URL."""
    if not pages:
        return "(none)"
    return "\n\n".join(
        f"[{p['kind']}] URL: {p['url']}\nTitle: {p.get('title') or 'N/A'}\n"
        f"Text: {p['text'][:MAX_PAGE_CHARS]}"
        for p in pages
    )


def build_analysis_prompt(
    website_data: dict, github_data: dict, pages: list[dict] | None = None
) -> str:
    """Build the user prompt from scraped website data, key page excerpts and GitHub data."""
    pages = pages or []
    homepage_url = website_data.get("url", "N/A")
    return f"""Analyze this product and return a JSON object with this EXACT structure:
{{
  "product_name": "string",
  "product_description": "one sentence",
  "product_category": "API | SaaS | CLI | Library | Other",
  "business_type": "local_business|ecommerce|saas|developer_tool|publisher|nonprofit|other",
  "core_actions": [
    {{"name": "snake_case_action", "description": "string", "http_method": "GET|POST|PUT|PATCH|DELETE|UNKNOWN", "endpoint": "/path or UNKNOWN"}}
  ],
  "auth_method": "api_key | oauth2 | jwt | basic_auth | none | unknown",
  "tech_stack": ["string"],
  "has_existing_openapi": true,
  "has_existing_docs": true,
  "webhook_support": false,
  "missing_agent_features": ["string"],
  "recommendations": ["string"],
  "ai_preview": {{
    "summary": "string",
    "unknowns": [{{"fact": "string", "fix": "string"}}],
    "questions": [{{"id": "price", "answered": true, "answer": "string", "quote": "string", "source": "URL"}}]
  }}
}}

Rules for "ai_preview" (this shows the site owner how an AI assistant would see them):
- "summary": the 2-3 sentence answer an AI assistant would give if asked "What is
  <product_name>?", written in third person, using ONLY facts stated in the pages below.
  If the pages are vague, the summary should be vague too — that is the point.
- "unknowns": up to 5 facts a customer would expect to find but that the pages do NOT state
  (e.g. "Pricing", "Location / service area", "Who it is for", "How to sign up or buy",
  "Opening hours", "Contact details"). "fix" is one short instruction, e.g.
  "State plan prices as text on your pricing page". Empty list if nothing important is missing.
- "questions": one entry for EACH of these fixed question ids, about this business:
{_questions_block()}
  Answer ONLY from the page text below (it is exactly what an AI crawler that doesn't run
  JavaScript receives). "answered" is true ONLY if the text clearly answers the question.
  Then "answer" is the answer in at most 25 words, "quote" is 6-30 consecutive words copied
  EXACTLY, character for character, from the page text that supports the answer, and
  "source" is the exact URL (copied from the list below) of the page the quote is from.
  The quote is checked automatically; an inexact quote counts as not answered.
  If not answered: "answered": false, "answer": "", "quote": "", "source": "".

--- WEBSITE HOMEPAGE ---
URL: {homepage_url}
Title: {website_data.get('title', 'N/A')}
Description: {website_data.get('description', 'N/A')}
Headings: {' | '.join(website_data.get('headings', [])[:10])}
Body: {homepage_text(website_data) or 'N/A'}

--- OTHER KEY PAGES ---
{_pages_block(pages)}

--- GITHUB ---
Repo: {github_data.get('repo_name', 'N/A')}
Description: {github_data.get('description', 'N/A')}
Language: {github_data.get('language', 'N/A')}
README: {github_data.get('readme', 'N/A')[:2000]}
Files: {', '.join(github_data.get('file_tree', [])[:50])}
"""
