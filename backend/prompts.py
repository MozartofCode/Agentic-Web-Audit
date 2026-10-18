"""All prompt strings for the Groq LLM analysis call."""

from __future__ import annotations

SYSTEM_PROMPT = """You are an expert at analyzing websites, software products and APIs, and at
predicting how AI assistants (ChatGPT, Claude, Perplexity) would describe them.
You will be given content scraped from a website and/or GitHub repository.
Base every statement ONLY on the content provided. Never invent facts.
Return ONLY valid JSON. No explanation. No markdown. No code fences. Just JSON."""

MAX_PAGE_CHARS = 1500
MAX_HOMEPAGE_CHARS = 3000


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
    "questions": [{{"question": "string", "answered": true, "answer": "string", "source": "URL"}}]
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
- "questions": exactly 8 questions real customers most often ask an AI assistant about a
  business of this type (typically: what it costs, where / when, who it is for, how to buy or
  sign up, how to contact, policies, how it compares). Choose them by how often customers ask,
  NOT by whether the pages answer them. "answered" is true ONLY if the pages below clearly
  answer it. Then
  "answer" is the answer in at most 25 words, using facts from that page, and "source" is the
  exact URL (copied from the list below) of the page that answers it. If not answered:
  "answered": false, "answer": "", "source": "".

--- WEBSITE HOMEPAGE ---
URL: {homepage_url}
Title: {website_data.get('title', 'N/A')}
Description: {website_data.get('description', 'N/A')}
Headings: {' | '.join(website_data.get('headings', [])[:10])}
Body: {website_data.get('body_text', 'N/A')[:MAX_HOMEPAGE_CHARS]}

--- OTHER KEY PAGES ---
{_pages_block(pages)}

--- GITHUB ---
Repo: {github_data.get('repo_name', 'N/A')}
Description: {github_data.get('description', 'N/A')}
Language: {github_data.get('language', 'N/A')}
README: {github_data.get('readme', 'N/A')[:2000]}
Files: {', '.join(github_data.get('file_tree', [])[:50])}
"""
