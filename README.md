# AgentReady

**See your website the way ChatGPT, Claude and Perplexity see it.** A free, no-login tool
that scans a public website (and optionally a public GitHub repo) and tells you how well AI
assistants and agents can read and use it — with the evidence behind every point and the
exact fixes to paste in.

- **Measured AI-readiness score** — ~30 deterministic checks across AI crawler access,
  readability without JavaScript, structured data, agent discovery (llms.txt), answerability
  and a developer track. Every check shows what was found, why it matters, and a fix.
- **How AI sees you** — what an assistant would likely say about your site, what it can't
  find out, and which common customer questions your pages answer.
- **Top 5 fixes** — ranked by impact and effort, with the estimated points each one is worth.
- **Fix-it pack** — `llms.txt`, a `robots.txt` patch, JSON-LD and meta tags, with steps for
  your platform (WordPress, Shopify, Webflow, …); plus an OpenAPI draft and MCP server
  scaffold for API products.
- **Share and track** — permalinks, an embeddable score badge, re-scan comparisons, and
  side-by-side compare with a competitor.
- **Leaderboard** — measured scores for ~55 well-known sites, with stats like how many
  publish an `llms.txt` or block AI answer bots (`/leaderboard`).
- **CLI and GitHub Action** — fail CI when your score drops (see below).

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

## CLI and GitHub Action

Scan from the terminal (Node 18+, no dependencies), pointing it at an AgentReady backend:

```bash
node cli/agentready.mjs https://example.com --api https://your-backend.example --min-score 70
```

It prints the score, category breakdown and top fixes, and exits `1` if the score is below
`--min-score` (`2` on errors). Run `node cli/agentready.mjs --help` for all options.

In GitHub Actions:

```yaml
- uses: MozartofCode/Agentic-Web-Audit@main
  with:
    url: https://example.com
    api-url: https://your-backend.example
    min-score: 70
```

The step writes a summary table to the job page and exposes `score`, `grade` and
`report-url` outputs.

## Project structure

```
.
├── CLAUDE.md              # architecture, coding standards, API contract — read this first
├── spec.md                # full product spec
├── UI.md                  # full UI/UX design spec (design tokens, component specs)
├── .claude/commands/      # slash-command playbooks used while building this with Claude Code
├── backend/               # FastAPI app — see backend/
├── frontend/              # React (Vite) app — see frontend/
├── cli/                   # dependency-free Node CLI (agentready)
└── action.yml             # GitHub Action wrapping the CLI
```

`CLAUDE.md` is the single source of truth for how this project is built: tech stack, coding
standards, the `/analyze` API contract, environment variables, and an explicit "what NOT to
build" scope guard for the MVP. Read it before making non-trivial changes.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup details, coding
standards, and how to submit a change. Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Scope

This is intentionally small. No accounts, no private-repo support, no paid tier, no tracking.
The only storage is a single table of public scan results, used for permalinks, badges and
re-scan comparisons. See the "What NOT to Build" section in [`CLAUDE.md`](CLAUDE.md) for the full list
and the reasoning — that list is enforced deliberately, not an oversight.

## License

[MIT](LICENSE)
