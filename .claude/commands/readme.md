---
description: Generate or update the README.md for AgentReady. Use when setting up the repo for the first time, after a significant feature addition, or when the README is out of date. Produces a README that developers actually want to read.
---

# /readme — README Generator

You write READMEs that engineers read instead of skip.
Clean, structured, honest about what's missing, and useful from the first glance.

A great README answers five questions in order:
1. What is this? (one sentence)
2. What does it do for me? (one paragraph, maybe a screenshot)
3. How do I run it in 5 minutes? (exact commands, no assumptions)
4. How does it work? (brief architecture, for contributors)
5. What's next? (roadmap, contributing)

---

## The README to Generate

```markdown
# AgentReady

> Make your product native to AI agents — in under 15 seconds.

AgentReady takes your website URL and public GitHub repo, analyzes your product
with AI, and generates four files that make it usable by AI agents:

- **`llms.txt`** — a plain-text file describing your product to AI agents
- **`audit-report.md`** — a scored checklist of what's missing and how to fix it
- **`mcp_server.ts`** — a TypeScript MCP server scaffold your agents can call
- **`openapi.yaml`** — a machine-readable API spec inferred from your codebase

No login. No setup. Paste two URLs, get four files.

---

## Demo

[screenshot or GIF here — add before first public release]

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | Python + FastAPI |
| LLM | Groq API (Llama 3.3 70B) |
| Crawling | httpx + BeautifulSoup4 |
| GitHub data | GitHub REST API (unauthenticated) |

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GROQ_API_KEY

uvicorn main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`.
Test it:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/tiangolo/fastapi"}'
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# VITE_API_URL=http://localhost:8000 is already set

npm run dev
```

The app is now running at `http://localhost:5173`.

---

## Project Structure

```
agentready/
├── backend/
│   ├── main.py              # FastAPI app, routes
│   ├── crawler.py           # Website crawling
│   ├── github_fetcher.py    # GitHub REST API integration
│   ├── llm_analyzer.py      # Groq API call + parsing
│   ├── artifact_generator.py# Generates the 4 output files
│   ├── models.py            # Pydantic models
│   ├── prompts.py           # LLM prompt strings
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── api.js           # All fetch calls live here
        └── components/
            ├── LandingView.jsx
            ├── LoadingView.jsx
            ├── ResultsView.jsx
            ├── AuditScoreCard.jsx
            └── ArtifactSection.jsx
```

---

## How It Works

1. **Crawl** — The backend fetches the website with `httpx` and parses it with
   BeautifulSoup to extract title, headings, body text, and API-related links.

2. **Fetch GitHub** — The GitHub REST API (unauthenticated) is used to fetch the
   repo's README, file tree, and up to 5 relevant source files (route files,
   existing OpenAPI specs, package manifest).

3. **Analyze** — Everything is assembled into a single prompt and sent to
   Groq's Llama 3.3 70B model at `temperature=0.1`. The model returns a structured
   JSON object describing the product: its name, core actions, auth method, tech stack,
   and what's missing for agent-readiness.

4. **Generate** — The four artifacts are generated from the structured data using
   template functions in `artifact_generator.py`. No second LLM call — pure templates.

5. **Return** — The artifacts are returned to the React frontend, which displays them
   in a syntax-highlighted tabbed viewer with download buttons.

---

## API Reference

### `POST /analyze`

**Request:**
```json
{
  "website_url": "https://example.com",   // optional
  "github_url": "https://github.com/..."  // optional
}
```
At least one URL is required.

**Response:**
```json
{
  "product_name": "string",
  "product_summary": "string",
  "artifacts": {
    "llms_txt": "string",
    "audit_md": "string",
    "mcp_server_ts": "string",
    "openapi_yaml": "string"
  },
  "audit_score": {
    "total": 100,
    "score": 42,
    "breakdown": { ... }
  }
}
```

---

## Deployment

### Backend (Railway)

1. Push to GitHub
2. Create a new project on [Railway](https://railway.app)
3. Connect your GitHub repo
4. Set the root directory to `backend/`
5. Add environment variable: `GROQ_API_KEY=your_key`
6. Railway detects FastAPI automatically — it will run `uvicorn main:app`

### Frontend (Vercel)

1. Push to GitHub
2. Create a new project on [Vercel](https://vercel.com)
3. Set the root directory to `frontend/`
4. Add environment variable: `VITE_API_URL=https://your-railway-url.railway.app`
5. Vercel detects Vite automatically

---

## Limitations (MVP)

- **Public repos only** — private GitHub repos require OAuth (not yet implemented)
- **Static sites only** — JavaScript-heavy SPAs may not crawl correctly
- **One analysis at a time** — no history, no saved results
- **No auth** — everyone uses the same tool, nothing is saved

---

## Roadmap

- [ ] SPA support via Playwright
- [ ] Private repo support via GitHub OAuth
- [ ] Shareable result links
- [ ] Hosted MCP server deployment
- [ ] CLI: `npx agentready --url https://...`

---

## Contributing

This is an MVP built in 3 days. PRs welcome for bug fixes and the roadmap items above.

1. Fork the repo
2. Create a branch: `git checkout -b feat/your-feature`
3. Follow the coding standards in `CLAUDE.md`
4. Open a PR with a clear description of what changed and why

---

## License

MIT
```

---

## README Update Checklist

When updating an existing README (not writing from scratch), check:

```
[ ] Version numbers in prerequisites are still current
[ ] The "How It Works" section reflects the current architecture
[ ] All environment variable names match what's in .env.example
[ ] The API reference matches what's in models.py
[ ] The project structure tree matches the actual file structure
[ ] Any new limitations are listed
[ ] Any completed roadmap items are removed from the list
```

---

## Screenshot / GIF Note

Before the first public release, add a screenshot or demo GIF:
- Capture the full flow: landing → analysis loading → results with score
- GIF: ~10 seconds, shows typing in a URL, the loading animation, the score reveal
- Save as `docs/demo.gif` or `docs/screenshot.png`
- Replace the `[screenshot or GIF here]` placeholder in the README
- Use `![AgentReady demo](docs/demo.gif)` to embed it
