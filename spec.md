# AgentReady MVP — Technical Specification

## Overview

**AgentReady** is a free, no-login web tool that takes a public website URL and/or a public GitHub repository URL, analyzes the product, and generates a set of AI-agent-readiness artifacts. The goal is to help developers make their products natively usable by AI agents.

---

## Problem Statement

Most websites and APIs were built for human users. AI agents struggle to interact with them because there is no machine-readable description of what the product does or how to use it. AgentReady solves this by automatically analyzing a product and generating the files agents need.

---

## MVP Scope

### In Scope
- Accept a public website URL and/or public GitHub repo URL as input
- Crawl and parse the website (static/server-rendered only — no SPA support in MVP)
- Fetch and parse the GitHub repo (README, route files, existing OpenAPI files)
- Use Groq LLM API (Llama 3.3 70B) to analyze and generate outputs
- Generate 4 downloadable artifacts:
  1. `llms.txt` — plain markdown file describing the product for AI agents
  2. Agent-Readiness Audit Report — markdown report of what's missing and how to fix it
  3. MCP Server Scaffold — TypeScript MCP server stub the developer can fill in
  4. OpenAPI Spec Draft — YAML file inferred from codebase/docs
- Display all outputs in-browser with syntax highlighting
- Allow each file to be individually downloaded
- Show a loading/progress state during analysis

### Out of Scope (Post-MVP)
- Private GitHub repos (requires OAuth)
- JavaScript-heavy SPAs (requires Playwright/headless browser)
- User accounts, saved history, authentication
- Auto-deploying or hosting MCP servers
- Paid tiers or billing
- CLI tool

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite) |
| Backend | Python FastAPI |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Website crawling | `httpx` + `BeautifulSoup4` |
| GitHub ingestion | GitHub REST API (unauthenticated, public repos only) |
| Syntax highlighting | `react-syntax-highlighter` |
| Styling | Tailwind CSS |
| Deployment | Vercel (frontend) + Railway or Render (backend) |

---

## Architecture

```
User (Browser)
     │
     │  POST /analyze  { website_url, github_url }
     ▼
FastAPI Backend
     │
     ├── 1. Crawl website (httpx + BeautifulSoup)
     │        └── Extract: title, meta description, nav links,
     │                     main page text, /docs or /api links if found
     │
     ├── 2. Fetch GitHub repo (GitHub REST API)
     │        └── Extract: README.md, file tree,
     │                     route files (routes/, api/, controllers/),
     │                     any existing openapi.yaml / swagger.json
     │
     ├── 3. Build context string from crawled content
     │
     ├── 4. Call Groq API (single prompt, structured JSON response)
     │        └── Parse JSON → product_summary, actions[], auth_method,
     │                         tech_stack[], missing_agent_features[]
     │
     ├── 5. Generate artifacts from structured data
     │        ├── llms.txt         (template fill)
     │        ├── audit.md         (template fill)
     │        ├── mcp_server.ts    (code template fill)
     │        └── openapi.yaml     (template fill)
     │
     └── Return JSON { llms_txt, audit_md, mcp_ts, openapi_yaml }

React Frontend renders each artifact in a tabbed view with download buttons.
```

---

## API Design

### `POST /analyze`

**Request body:**
```json
{
  "website_url": "https://example.com",      // optional but at least one required
  "github_url": "https://github.com/org/repo" // optional but at least one required
}
```

**Response body:**
```json
{
  "product_name": "Acme API",
  "product_summary": "A REST API for managing invoices...",
  "artifacts": {
    "llms_txt": "# Acme API\n\n> ...",
    "audit_md": "# Agent-Readiness Audit\n\n...",
    "mcp_server_ts": "import { Server } from '@modelcontextprotocol/sdk'...",
    "openapi_yaml": "openapi: 3.0.0\ninfo:\n  title: Acme API..."
  },
  "audit_score": {
    "total": 100,
    "score": 42,
    "breakdown": {
      "has_api": true,
      "has_openapi_spec": false,
      "has_llms_txt": false,
      "has_structured_docs": true,
      "has_webhook_support": false,
      "has_api_key_auth": true
    }
  }
}
```

**Error responses:**
```json
{ "error": "Could not reach website. Check the URL and try again." }
{ "error": "GitHub repo not found or is private." }
{ "error": "At least one of website_url or github_url is required." }
```

---

## Backend Implementation

### Project Structure
```
backend/
├── main.py                  # FastAPI app, CORS, routes
├── crawler.py               # Website crawler (httpx + BeautifulSoup)
├── github_fetcher.py        # GitHub REST API integration
├── llm_analyzer.py          # Groq API call + response parsing
├── artifact_generator.py    # Generates the 4 output files from LLM data
├── models.py                # Pydantic models for request/response
├── prompts.py               # LLM system and user prompts
└── requirements.txt
```

### `crawler.py`
- Use `httpx` (async) to fetch the URL with a 10s timeout
- Parse with `BeautifulSoup4`
- Extract:
  - `<title>` tag
  - `<meta name="description">` content
  - All `<nav>` link text and hrefs
  - All `<h1>`, `<h2>`, `<h3>` tags
  - Any links containing `/api`, `/docs`, `/swagger`, `/openapi`
  - Body text (strip scripts/styles), truncated to 6000 characters
- If fetch fails (timeout, 4xx, 5xx), raise a clean error

### `github_fetcher.py`
- Use GitHub REST API (no auth token needed for public repos)
- Base URL: `https://api.github.com/repos/{owner}/{repo}`
- Fetch in this order:
  1. `GET /repos/{owner}/{repo}` — repo description
  2. `GET /repos/{owner}/{repo}/readme` — base64 decode the README (truncate to 4000 chars)
  3. `GET /repos/{owner}/{repo}/git/trees/HEAD?recursive=1` — full file tree
  4. From the file tree, identify and fetch (up to 5 files, 1000 chars each):
     - Any file named `openapi.yaml`, `openapi.json`, `swagger.yaml`, `swagger.json`
     - Files in `routes/`, `api/`, `controllers/` directories
     - `package.json` or `pyproject.toml` (for tech stack detection)
- If repo not found or private, raise a clean error

### `llm_analyzer.py`
- Single Groq API call using `groq` Python SDK
- Model: `llama-3.3-70b-versatile`
- Temperature: `0.1` (low for consistent structured output)
- Max tokens: `2000`
- Response format: JSON (instruct the model to return only JSON, no markdown)
- Parse response into a `ProductAnalysis` Pydantic model

**System prompt** (in `prompts.py`):
```
You are an expert at analyzing software products and APIs.
You will be given content scraped from a website and/or GitHub repository.
Your job is to analyze the product and return a structured JSON object.
Return ONLY valid JSON with no explanation, no markdown, no code fences.
```

**User prompt template:**
```
Analyze this product and return a JSON object with this exact structure:
{
  "product_name": "string — the name of the product",
  "product_description": "string — one sentence describing what it does",
  "product_category": "string — e.g. API, SaaS, developer tool, database, etc.",
  "core_actions": [
    {
      "name": "string — action name e.g. create_invoice",
      "description": "string — what this action does",
      "http_method": "string — GET/POST/PUT/PATCH/DELETE or UNKNOWN",
      "endpoint": "string — e.g. /invoices or UNKNOWN"
    }
  ],
  "auth_method": "string — one of: api_key, oauth2, jwt, basic_auth, none, unknown",
  "tech_stack": ["string — list of detected technologies"],
  "has_existing_openapi": true/false,
  "has_existing_docs": true/false,
  "webhook_support": true/false,
  "missing_agent_features": [
    "string — specific things missing that would make this product agent-unfriendly"
  ],
  "recommendations": [
    "string — specific actionable recommendations to make this product agent-native"
  ]
}

--- WEBSITE CONTENT ---
{website_content}

--- GITHUB README ---
{readme_content}

--- CODE/ROUTE FILES ---
{route_files_content}
```

### `artifact_generator.py`
Takes the `ProductAnalysis` object and generates the 4 artifacts as strings.

#### 1. `llms.txt` generator
Fill a markdown template with:
- Product name and description
- Core actions list (name, description, endpoint)
- Auth method explanation
- Links to docs if found
- Rate limits (if detected)

#### 2. `audit.md` generator
Generate a scored markdown report:
- **Score** out of 100 (calculated from `audit_score` breakdown)
- **What's working** — things the product already does well for agents
- **What's missing** — populated from `missing_agent_features`
- **Action items** — numbered list from `recommendations`
- **Priority fixes** — top 3 most impactful changes

Scoring rubric:
| Check | Points |
|---|---|
| Has any public API | 20 |
| Has OpenAPI/Swagger spec | 20 |
| Has `llms.txt` | 15 |
| Has structured docs (not just a wall of text) | 15 |
| Has API key or token auth (not just login UI) | 15 |
| Has webhook support | 15 |

#### 3. `mcp_server.ts` generator
Generate a TypeScript MCP server scaffold using `@modelcontextprotocol/sdk`.
- One `tool` definition per detected core action
- Each tool has: `name`, `description`, `inputSchema` (JSON Schema)
- Tool handler bodies are stubbed with `// TODO: implement`
- Include comments explaining what each section does
- Include a `README` comment block at the top explaining how to install and run

#### 4. `openapi.yaml` generator
Generate a minimal OpenAPI 3.0.0 YAML:
- `info`: product name, description, version `0.1.0`
- `servers`: inferred from website URL
- One path per detected core action
- Each path has the inferred HTTP method, a summary, and an empty response schema
- Mark everything that was inferred (not confirmed) with an `x-inferred: true` extension
- Add a top comment: `# ⚠️ This spec was auto-generated and requires human review`

---

## Frontend Implementation

### Project Structure
```
frontend/
├── src/
│   ├── App.jsx               # Root component
│   ├── components/
│   │   ├── InputForm.jsx     # URL inputs + submit button
│   │   ├── LoadingState.jsx  # Progress indicator during analysis
│   │   ├── AuditScore.jsx    # Visual score card with breakdown
│   │   ├── ArtifactTabs.jsx  # Tabbed view of the 4 outputs
│   │   ├── ArtifactViewer.jsx# Syntax-highlighted code + download button
│   │   └── ErrorBanner.jsx   # Error display
│   ├── api.js                # fetch wrapper for POST /analyze
│   └── main.jsx
├── index.html
├── tailwind.config.js
└── package.json
```

### UI Flow

```
[Landing]
  ↓
[Input Form]  — website URL field + GitHub URL field + "Analyze" button
  ↓ (submit)
[Loading State] — spinner + rotating status messages
  "Crawling website..."
  "Reading GitHub repo..."
  "Analyzing with AI..."
  "Generating artifacts..."
  ↓ (response received)
[Results Page]
  ├── Product name + summary banner
  ├── Audit Score card (big number + colored breakdown)
  └── Tabs: [llms.txt] [Audit Report] [MCP Server] [OpenAPI Spec]
       └── Each tab: syntax-highlighted code + "Download [filename]" button
```

### Key UI Rules
- Both URL fields are optional individually, but at least one must be filled before submit
- Show inline validation if both fields are empty on submit
- The "Analyze" button is disabled while loading
- Each artifact tab shows the raw text with syntax highlighting (`markdown` for `.txt`/`.md`, `typescript` for `.ts`, `yaml` for `.yaml`)
- Download button uses the `Blob` API to trigger a file download with the correct filename and extension
- Mobile responsive — stack tabs vertically on small screens

---

## Environment Variables

### Backend (`.env`)
```
GROQ_API_KEY=your_groq_api_key_here
FRONTEND_URL=http://localhost:5173   # for CORS
```

### Frontend (`.env`)
```
VITE_API_URL=http://localhost:8000
```

---

## Error Handling

| Scenario | Backend behavior | Frontend display |
|---|---|---|
| Website unreachable | 400 with message | Red banner with message |
| GitHub repo private/missing | 400 with message | Red banner with message |
| Both URLs empty | 422 validation error | Inline field error |
| Groq API failure | 500 with generic message | "Analysis failed, try again" |
| Website is SPA (no content extracted) | Return partial result with audit noting SPA detected | Warning banner above results |
| GitHub rate limit hit | 429 with message | "GitHub rate limit hit, try again in 1 hour" |

---

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx beautifulsoup4 groq python-dotenv pydantic
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm create vite@latest . -- --template react
npm install tailwindcss @tailwindcss/vite react-syntax-highlighter
npm run dev
```

---

## Build Order (Suggested 3-Day Plan)

### Day 1 — Backend Pipeline
- [ ] Set up FastAPI app with CORS
- [ ] Build `crawler.py` — fetch and parse a website
- [ ] Build `github_fetcher.py` — fetch README + route files
- [ ] Build `llm_analyzer.py` — Groq call + JSON parsing
- [ ] Test the pipeline end-to-end with a real repo (e.g. `github.com/tiangolo/fastapi`)

### Day 2 — Artifact Generation + API
- [ ] Build `artifact_generator.py` — all 4 generators
- [ ] Wire up `POST /analyze` endpoint
- [ ] Add error handling for all failure cases
- [ ] Test full API with `curl` or Postman

### Day 3 — Frontend + Polish
- [ ] Build `InputForm`, `LoadingState`, `AuditScore`, `ArtifactTabs`, `ArtifactViewer`
- [ ] Connect to backend API
- [ ] Test end-to-end in browser
- [ ] Deploy backend to Railway/Render, frontend to Vercel

---

## Future Roadmap (Post-MVP)

1. **SPA support** — add Playwright for JS-heavy sites
2. **Private repo support** — GitHub OAuth login
3. **User accounts** — save and revisit past analyses
4. **MCP server hosting** — auto-deploy the generated MCP server
5. **Shareable report links** — public URL for each analysis result
6. **Webhook integration** — connect to GitHub Actions to auto-regenerate on push
7. **Paid tier** — unlimited analyses, private repos, hosted MCP servers
8. **CLI tool** — `npx agentready analyze --url https://... --github https://...`

---

## Notes for the LLM Building This

- All Groq API calls use `llama-3.3-70b-versatile` unless otherwise specified
- Always set `temperature=0.1` and instruct the model to return only JSON for structured outputs
- The frontend and backend are separate projects. Do not mix them.
- Use `httpx.AsyncClient` (not `requests`) in the backend for async crawling
- GitHub API unauthenticated rate limit is 60 requests/hour — batch fetches carefully
- When a website cannot be crawled (SPA, timeout, etc.), proceed with only the GitHub content and note the limitation in the audit report
- All generated artifacts should include a header comment noting they were auto-generated and require human review
- Keep generated files clean and idiomatic — a developer will read and edit them
