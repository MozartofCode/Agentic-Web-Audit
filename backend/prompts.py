"""All prompt strings for the Groq LLM analysis call."""

SYSTEM_PROMPT = """You are an expert at analyzing software products and APIs.
You will be given content scraped from a website and/or GitHub repository.
Return ONLY valid JSON. No explanation. No markdown. No code fences. Just JSON."""


def build_analysis_prompt(website_data: dict, github_data: dict) -> str:
    """Build the user prompt from scraped website and GitHub data."""
    return f"""Analyze this product and return a JSON object with this EXACT structure:
{{
  "product_name": "string",
  "product_description": "one sentence",
  "product_category": "API | SaaS | CLI | Library | Other",
  "core_actions": [
    {{"name": "snake_case_action", "description": "string", "http_method": "GET|POST|PUT|PATCH|DELETE|UNKNOWN", "endpoint": "/path or UNKNOWN"}}
  ],
  "auth_method": "api_key | oauth2 | jwt | basic_auth | none | unknown",
  "tech_stack": ["string"],
  "has_existing_openapi": true,
  "has_existing_docs": true,
  "webhook_support": false,
  "missing_agent_features": ["string"],
  "recommendations": ["string"]
}}

--- WEBSITE ---
Title: {website_data.get('title', 'N/A')}
Description: {website_data.get('description', 'N/A')}
Headings: {' | '.join(website_data.get('headings', [])[:10])}
Body: {website_data.get('body_text', 'N/A')[:3000]}

--- GITHUB ---
Repo: {github_data.get('repo_name', 'N/A')}
Description: {github_data.get('description', 'N/A')}
Language: {github_data.get('language', 'N/A')}
README: {github_data.get('readme', 'N/A')[:2000]}
Files: {', '.join(github_data.get('file_tree', [])[:50])}
"""
