# AgentReady

A free, no-login web tool that takes a public website URL and/or a public GitHub repo URL,
analyzes the product with AI, and generates the files that make it usable by AI agents:

- **`llms.txt`** — a plain-English description of the product for AI agents
- **Agent-Readiness Audit** — a scored report (out of 100) of what's missing and how to fix it
- **MCP Server Scaffold** — a TypeScript [MCP](https://modelcontextprotocol.io) server stub, one tool per detected action
- **OpenAPI Spec Draft** — a YAML spec inferred from the site/repo, marked for human review

Most products on the web were built for humans clicking around a UI. AgentReady scans what's
already there and generates a starting point for making it agent-native — nothing here should
be treated as final; every generated file says so and expects a human review pass.

## How it works

You give it a website URL, a GitHub repo URL, or both. The backend crawls the page (or pulls
the README, file tree, and a handful of relevant source files from GitHub), sends that content
to an LLM in a single call, and gets back a structured description of the product — its name,
its core actions/endpoints, how it authenticates, what's missing for agents. That structured
data is then run through plain template code (no further AI calls) to produce the four files
above and the audit score.

It intentionally reads a *sample* of the content, not the whole site or repo — see
[`CLAUDE.md`](CLAUDE.md) for the exact limits (crawl depth, file caps, character truncation)
and why they're there.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite) + Tailwind CSS |
| Backend | Python (FastAPI, fully async) |
| Crawling | `httpx` + `BeautifulSoup4` |
| GitHub data | GitHub REST API (unauthenticated, public repos only) |
| LLM | [Groq](https://groq.com) — `openai/gpt-oss-120b` |

## Getting started

You'll need a free [Groq API key](https://console.groq.com/keys).

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then fill in GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env      # defaults to http://localhost:8000, adjust if needed
npm run dev
```

Open `http://localhost:5173`, paste a website or GitHub URL, and analyze.

## Project structure

```
.
├── CLAUDE.md              # architecture, coding standards, API contract — read this first
├── spec.md                # full product spec
├── UI.md                  # full UI/UX design spec (design tokens, component specs)
├── .claude/commands/      # slash-command playbooks used while building this with Claude Code
├── backend/               # FastAPI app — see backend/
└── frontend/              # React (Vite) app — see frontend/
```

`CLAUDE.md` is the single source of truth for how this project is built: tech stack, coding
standards, the `/analyze` API contract, environment variables, and an explicit "what NOT to
build" scope guard for the MVP. Read it before making non-trivial changes.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup details, coding
standards, and how to submit a change. Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Scope

This is intentionally a minimal MVP. No accounts, no database, no private-repo support, no
paid tier. See the "What NOT to Build" section in [`CLAUDE.md`](CLAUDE.md) for the full list
and the reasoning — that list is enforced deliberately, not an oversight.

## License

[MIT](LICENSE)
