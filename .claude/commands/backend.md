---
description: Scaffold, debug, or extend any FastAPI backend code for AgentReady. Use when building a new endpoint, writing a crawler function, fixing a Python error, working with the Groq API, or debugging the GitHub fetcher. Always check this before writing any Python.
---

# /backend — FastAPI Backend Development

You are a senior Python engineer working on the AgentReady FastAPI backend.
Your code is async, typed, tested mentally before writing, and clean enough
that another engineer could pick it up immediately.

---

## Backend File Map (Know Before You Touch)

```
backend/
├── main.py              ← FastAPI app init, CORS, route definitions only
├── models.py            ← ALL Pydantic models (request bodies, responses, internal)
├── crawler.py           ← Website fetching + HTML parsing (httpx + BeautifulSoup)
├── github_fetcher.py    ← GitHub REST API integration
├── llm_analyzer.py      ← Groq API call + JSON response parsing
├── artifact_generator.py ← Generates the 4 output files from structured LLM data
├── prompts.py           ← ALL prompt strings (system prompts, user prompt templates)
└── requirements.txt     ← Dependencies
```

**Rule:** `main.py` only contains route definitions and app setup. No business logic.
Business logic lives in the module that owns it.

---

## Pydantic Models (models.py)

All data shapes live here. Add new models here, never inline in route files.

```python
# Key models — reference these when building
class AnalyzeRequest(BaseModel):
    website_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None

    @model_validator(mode='after')
    def at_least_one_url(self) -> 'AnalyzeRequest':
        if not self.website_url and not self.github_url:
            raise ValueError("At least one of website_url or github_url is required")
        return self

class AuditBreakdown(BaseModel):
    has_api: bool
    has_openapi_spec: bool
    has_llms_txt: bool
    has_structured_docs: bool
    has_api_key_auth: bool
    has_webhook_support: bool

class AuditScore(BaseModel):
    total: int = 100
    score: int
    breakdown: AuditBreakdown

class Artifacts(BaseModel):
    llms_txt: str
    audit_md: str
    mcp_server_ts: str
    openapi_yaml: str

class AnalyzeResponse(BaseModel):
    product_name: str
    product_summary: str
    artifacts: Artifacts
    audit_score: AuditScore

class ProductAnalysis(BaseModel):
    """Internal model — output of LLM parsing, input to artifact generator"""
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

class CoreAction(BaseModel):
    name: str
    description: str
    http_method: str
    endpoint: str
```

---

## Crawler Pattern (crawler.py)

```python
import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 10.0
MAX_BODY_CHARS = 6000

async def crawl_website(url: str) -> dict:
    """
    Fetch and parse a website URL.
    Returns a dict with: title, description, headings, links, body_text
    Raises HTTPException on fetch failure.
    """
    headers = {"User-Agent": "AgentReady/0.1 (+https://agentready.dev)"}

    try:
        async with httpx.AsyncClient(timeout=CRAWL_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail=f"Timed out connecting to {url}. The site may be too slow or blocking crawlers.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"The site returned {e.response.status_code}. Try the GitHub URL alone.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Could not reach {url}. Check the URL and try again.")

    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove noise
    for tag in soup(['script', 'style', 'nav', 'footer', 'noscript']):
        tag.decompose()

    return {
        "title": soup.find('title').get_text(strip=True) if soup.find('title') else "",
        "description": _get_meta_description(soup),
        "headings": [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:20]],
        "api_links": _find_api_links(soup, url),
        "body_text": soup.get_text(separator=' ', strip=True)[:MAX_BODY_CHARS],
    }
```

---

## GitHub Fetcher Pattern (github_fetcher.py)

```python
async def fetch_github_repo(github_url: str) -> dict:
    """
    Fetch README, file tree, and relevant source files from a public GitHub repo.
    Raises HTTPException if repo is not found or is private.
    """
    owner, repo = _parse_github_url(github_url)  # implement this helper
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AgentReady/0.1",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Repo metadata
        repo_resp = await client.get(base, headers=headers)
        if repo_resp.status_code == 404:
            raise HTTPException(status_code=400, detail="GitHub repo not found. Check the URL or make sure it's public.")
        if repo_resp.status_code == 403:
            raise HTTPException(status_code=400, detail="GitHub rate limit reached. Try again in an hour.")
        repo_data = repo_resp.json()

        # 2. README
        readme_text = await _fetch_readme(client, base, headers)

        # 3. File tree
        tree_resp = await client.get(f"{base}/git/trees/HEAD?recursive=1", headers=headers)
        file_tree = [f["path"] for f in tree_resp.json().get("tree", []) if f["type"] == "blob"]

        # 4. Prioritized source files
        source_files = await _fetch_source_files(client, base, headers, file_tree)

    return {
        "repo_name": repo_data.get("name", ""),
        "description": repo_data.get("description", ""),
        "language": repo_data.get("language", ""),
        "readme": readme_text[:4000],
        "file_tree": file_tree[:100],   # cap at 100 entries for the prompt
        "source_files": source_files,
    }

def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from any GitHub URL format."""
    # Strip protocol, trailing slashes, .git suffix, /tree/... paths
    # https://github.com/owner/repo → ("owner", "repo")
    # https://github.com/owner/repo.git → ("owner", "repo")
    # https://github.com/owner/repo/tree/main → ("owner", "repo")
    ...
```

---

## Groq LLM Call Pattern (llm_analyzer.py)

```python
from groq import AsyncGroq
import json
import logging

logger = logging.getLogger(__name__)
client = AsyncGroq()  # reads GROQ_API_KEY from env automatically

async def analyze_product(website_data: dict, github_data: dict) -> ProductAnalysis:
    """
    Send scraped data to Groq and parse the structured JSON response.
    Raises HTTPException if LLM call fails or JSON is unparseable.
    """
    user_prompt = build_analysis_prompt(website_data, github_data)  # from prompts.py

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},  # from prompts.py
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
    except Exception as e:
        logger.error("Groq API call failed: %s", str(e))
        raise HTTPException(status_code=500, detail="AI analysis failed. Please try again.")

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences (model sometimes ignores the instruction)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
        return ProductAnalysis(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("LLM response parsing failed. Raw: %s", raw[:500])
        raise HTTPException(status_code=500, detail="AI returned an unexpected format. Please try again.")
```

---

## Prompt Template (prompts.py)

```python
SYSTEM_PROMPT = """You are an expert at analyzing software products and APIs.
You will be given content scraped from a website and/or GitHub repository.
Return ONLY valid JSON. No explanation. No markdown. No code fences. Just JSON."""

def build_analysis_prompt(website_data: dict, github_data: dict) -> str:
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
```

---

## Running the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start dev server
uvicorn main:app --reload --port 8000

# Test a single endpoint
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/tiangolo/fastapi"}'
```

## requirements.txt

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
beautifulsoup4==4.12.3
groq==0.11.0
pydantic==2.9.2
python-dotenv==1.0.1
```

---

## Debugging Checklist

Before asking for help, check these:

```
[ ] Is the virtual environment activated? (which python should show venv path)
[ ] Is GROQ_API_KEY in .env and loaded? (add `print(os.getenv('GROQ_API_KEY')[:8])` temporarily)
[ ] Is the GitHub URL in the right format? Test: print owner/repo extraction
[ ] Did the LLM return non-JSON? Check logger output for "LLM response parsing failed"
[ ] Is it a CORS error? Check that FRONTEND_URL in .env matches the running frontend port
[ ] Is httpx raising TimeoutException? Increase CRAWL_TIMEOUT or test the URL manually
[ ] Is it a 422 from FastAPI? That means Pydantic validation failed — check the request body shape
```
