# AgentReady — Claude Code Project Brain

You are building **AgentReady**: a free, no-login web tool that takes a public website URL
and/or a public GitHub repo URL, analyzes the product using AI, and generates four
agent-readiness artifacts: `llms.txt`, an audit report, an MCP server scaffold, and an
OpenAPI spec draft.

**Direction (Oct 2026, roadmap in progress):** reposition for *any* website owner as
"See your website the way ChatGPT, Claude and Perplexity see it" — a measured AI-visibility
and agent-usability score with evidence and copy-paste fixes. The API/MCP/OpenAPI artifacts
become a developer track shown when relevant. Rule of thumb: anything that can be measured
(robots.txt, llms.txt, JSON-LD, meta tags…) is checked deterministically in code; the LLM is
only for qualitative judgment, never for a pass/fail we can measure.

Read this file before doing anything. It is the source of truth for how this project is built.

---

## Project Architecture

```
agentready/
├── CLAUDE.md                  ← you are here
├── .claude/
│   └── commands/              ← slash commands (skills)
│       ├── idea.md
│       ├── ui.md
│       ├── backend.md
│       ├── review.md
│       ├── commit.md
│       └── readme.md
├── spec.md                    ← full product spec (READ THIS)
├── UI.md                      ← full UI/UX design spec (READ THIS for any frontend work)
├── backend/
│   ├── main.py                ← app, CORS, reports-store lifespan
│   ├── reports.py             ← routes: /analyze, /compare, /reports, /badge, /og, /share
│   ├── scan.py                ← the scan pipeline (crawl → checks → one LLM call → fix pack)
│   ├── store.py               ← reports store: Postgres (asyncpg) / in-memory / null
│   ├── delta.py               ← re-scan delta vs the previous report for a domain
│   ├── share_images.py        ← README badge SVG + 1200×630 OG card PNG (Pillow)
│   ├── leaderboard.py         ← GET /leaderboard + `python leaderboard.py` snapshot builder
│   ├── data/leaderboard.json  ← committed leaderboard snapshot
│   ├── migrations/            ← SQL for the reports table (apply by hand / Supabase)
│   ├── crawler.py             ← HTML/robots/llms.txt parsing helpers
│   ├── site_fetcher.py        ← SiteContext: one SSRF-safe fetch of everything checks need
│   ├── checks/                ← measured audit: one module per category, @check registry
│   ├── fix_pack.py            ← Fix-it pack v2: llms.txt, robots diff, JSON-LD, meta tags
│   ├── platform_detect.py     ← WordPress/Shopify/Webflow/Wix/Squarespace/Framer/Next.js
│   ├── platform_guides.py     ← "how to add this" steps per platform
│   ├── safety.py
│   ├── github_fetcher.py
│   ├── llm_analyzer.py
│   ├── artifact_generator.py
│   ├── models.py
│   ├── prompts.py
│   └── requirements.txt
├── cli/agentready.mjs          ← dependency-free Node CLI; `node --test` in cli/
├── action.yml                 ← GitHub Action wrapping the CLI
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── Header.jsx
    │   │   ├── LandingView.jsx
    │   │   ├── LoadingView.jsx
    │   │   ├── ResultsView.jsx
    │   │   ├── InputForm.jsx
    │   │   ├── ScoreHero.jsx / CategoryRings.jsx
    │   │   ├── TopFixes.jsx / AIPreviewCard.jsx
    │   │   ├── CrawlerMatrix.jsx
    │   │   ├── CheckList.jsx / CheckItem.jsx / CopyButton.jsx
    │   │   ├── ArtifactSection.jsx
    │   │   ├── ShareBar.jsx / ReportStatus.jsx   ← permalink, badge, re-scan, delta
    │   │   ├── CompareForm.jsx / CompareView.jsx
    │   │   └── ErrorBanner.jsx
    │   ├── api.js
    │   ├── routes.js              ← pathname router: /, /r/:id, /compare[/:a/:b]
    │   └── main.jsx
    ├── middleware.js              ← Vercel: link-preview bots on /r/:id get /share/:id
    ├── vercel.json                ← SPA rewrite
    ├── index.html
    ├── tailwind.config.js
    └── package.json
```

---

## Tech Stack (Non-Negotiable)

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React (Vite) | Not Next.js |
| Styling | Tailwind CSS | Follow UI.md tokens exactly |
| Backend | Python FastAPI | Async throughout |
| HTTP client | `httpx` (async) | Never `requests` |
| HTML parsing | `BeautifulSoup4` | |
| LLM | Groq API — `openai/gpt-oss-120b` | Temperature always `0.1` for structured output |
| GitHub data | GitHub REST API (unauthenticated) | Public repos only |
| Syntax highlighting | `react-syntax-highlighter` | Custom theme in UI.md |
| Deployment | Vercel (frontend), Render (backend) | Railway dropped its free tier; Render's free Web Service is the closest zero-cost equivalent (sleeps after 15 min idle) |

---

## Coding Standards

### Python (Backend)

- Use `async/await` everywhere. The entire backend is async. Never use blocking calls.
- Use `httpx.AsyncClient` inside async context managers:
  ```python
  async with httpx.AsyncClient(timeout=10.0) as client:
      response = await client.get(url)
  ```
- All functions have type hints. Always.
- Use Pydantic models for ALL request/response shapes — never raw dicts crossing API boundaries.
- Errors: raise `HTTPException(status_code=400, detail="human readable message")` for user
  errors. Never return `{"error": ...}` manually from route handlers.
- No `print()` statements. Use Python's `logging` module:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.info("Crawling %s", url)
  ```
- File-level docstrings on every module. Function docstrings on public functions.
- Max line length: 100 characters.

### JavaScript / React (Frontend)

- Functional components only. No class components.
- `useState` and `useCallback` for local state. No Redux, no Zustand, no Context for MVP.
- All `fetch` calls go through `src/api.js` — never call `fetch()` directly in a component.
- Never inline styles. All styling is Tailwind utility classes or CSS custom properties
  from the design token set in UI.md.
- No `console.log()` in committed code. Use `console.error()` only for genuine error paths.
- Component files: one component per file, file name matches component name exactly.
- Props that accept functions are named `on[Event]`: `onSubmit`, `onChange`, `onTabChange`.

### CSS / Tailwind

- Use ONLY the color tokens defined in `UI.md` and `tailwind.config.js`.
- Border radius is `8px` (`rounded`) everywhere. No exceptions.
- Never use Tailwind's default colors like `bg-gray-900` or `text-blue-500`.
  Use the custom tokens: `bg-bg-base`, `text-text-primary`, `text-accent`, etc.
- For the dot grid background and the pulse orb: write plain CSS in a `.css` file,
  not Tailwind. These require keyframes which Tailwind can't express cleanly.

---

## API Contract (Source of Truth)

### `POST /analyze`

Request:
```json
{
  "website_url": "https://example.com",   // nullable
  "github_url": "https://github.com/...", // nullable
  "refresh": false                        // true = skip the 24h cache (Re-scan)
  // At least one URL must be non-null
}
```

A scan of the same input (normalized URL) within 24h returns the saved report with
`cached: true` — no crawl, no LLM call. Fresh scans are saved when a store is configured.

Response (200):
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
    "breakdown": {
      "has_api": true,
      "has_openapi_spec": false,
      "has_llms_txt": false,
      "has_structured_docs": true,
      "has_api_key_auth": true,
      "has_webhook_support": false
    }
  },
  "audit": {                      // measured audit — what the results UI renders
    "overall": 64, "grade": "D",
    "critical_failures": [],      // failed critical checks cap overall at 49
    "categories": [{ "id": "crawler", "label": "...", "description": "...",
                     "score": 82, "passed": 4, "warned": 1, "failed": 0 }],  // null = all n/a
    "checks": [{ "id": "llms_txt", "category": "agent", "title": "...",
                 "status": "pass|warn|fail|na", "weight": 8, "evidence": "...",
                 "why": "...", "fix": "...", "fix_language": "markdown" }],
    "crawler_access": [{ "bot": "GPTBot", "owner": "OpenAI",
                         "purpose": "training|search|user",
                         "status": "allowed|partial|blocked", "detail": "..." }],
    "pages_scanned": ["https://example.com/", "https://example.com/pricing"],
    "top_fixes": [{ "check_id": "llms_txt", "title": "...", "category": "agent",
                    "status": "fail", "effort": "minutes|hour|dev", "points": 5,
                    "evidence": "...", "fix": "...", "fix_language": "markdown" }]
  },
  "ai_preview": {                 // LLM, qualitative only — never part of the score
    "summary": "2-3 sentences an assistant would say",
    "unknowns": [{ "fact": "Pricing", "fix": "State prices as text on /pricing" }],
    "questions": [{ "id": "price", "question": "How much does it cost?", "answered": true,
                    "answer": "...", "quote": "verbatim words from the page",
                    "source": "https://example.com/pricing",
                    "unverified": false, "note": "" }]   // blind-reader test, see below
  },
  "fix_pack": {
    "platform": { "id": "wordpress", "name": "WordPress", "evidence": "..." },  // nullable
    "developer_track": false,
    "files": [{ "id": "llms_txt|robots_txt|json_ld|meta_tags|openapi|mcp_server",
                "label": "...", "filename": "...", "language": "markdown|diff|html|...",
                "content": "...", "description": "...", "how_to": ["step"],
                "developer": false }]   // OpenAPI/MCP only on the developer track
  },
  "website_url": "https://example.com/",   // the scanned input (nullable)
  "github_url": null,
  "report_id": "qJ7Vh7JJ",        // null when no store is configured (DATABASE_URL unset)
  "created_at": "2026-10-18T16:02:11Z",
  "cached": false,                // true for a saved report (cache hit or GET /reports/{id})
  "delta": {                      // vs the previous report for the same domain; nullable
    "previous_report_id": "aB3dE5fG", "previous_overall": 58,
    "previous_created_at": "...", "points": 6,
    "now_passing": ["llms.txt is published"], "regressed": []
  }
}
```

`audit_score` is the legacy 6-check rubric (mostly LLM-judged); new UI work uses `audit`.
To add a check: write a function in the right `backend/checks/<category>.py` decorated with
`@check(...)` (set `effort="minutes"|"hour"|"dev"` — it ranks the fix in Top fixes, which
orders by weight × severity ÷ effort and shows the simulated "+N points"), returning
`Outcome(status, evidence, fix)`, and add a fixture case to `backend/tests/test_checks.py`
(a test fails if any check has no case).

Error (400):
```json
{ "detail": "Human-readable error message" }
```

### Other routes

| Route | Returns |
|---|---|
| `GET /reports/{id}` | the saved report (same shape as `/analyze`, `cached: true`); 404 unknown, 410 unreadable old format |
| `POST /compare` | `{"website_urls": [a, b]}` → `{"reports": [A, B]}`. Both scans run in parallel (one LLM call each, cache applies); counts as 2 against the rate limit |
| `GET /badge/{domain}.svg` | "AI-Ready · NN" badge from the domain's latest report (`www.` ignored); "not scanned" if none |
| `GET /og/{id}.png` | 1200×630 social card for a report |
| `GET /share/{id}` | HTML with Open Graph/Twitter tags for link-preview bots; redirects people to `FRONTEND_URL/r/{id}` |
| `GET /leaderboard` | ranked measured scores for the curated `LEADERBOARD_SITES`, plus headline stats and sites that blocked the scanner; served from `backend/data/leaderboard.json` |

**Blind-reader test** (`blind_reader.py`): `ai_preview.questions` is always the fixed
`BLIND_QUESTIONS` set (never LLM-chosen), answered from exactly the page text in
`prompts.prompt_texts()`. An answer counts only if its quote is found on a page we showed the
model (`quote_found`); otherwise `unverified` is set. Cloudflare-obfuscated emails never count
(`note` explains). Empty for GitHub-only scans. Keep it out of the score.

**Leaderboard:** `cd backend && python leaderboard.py` rescans every site in
`leaderboard.LEADERBOARD_SITES` (`--only a.com b.com` to rescan a few) and rewrites the snapshot.
It runs the deterministic audit only, with no LLM call, so it costs $0 in Groq usage. Commit the
updated JSON to publish it. Only curated sites are listed, never sites users scanned.

The frontend permalinks are `/r/:id` and `/compare/:idA/:idB`. Vercel serves the SPA for
every path (`vercel.json`); `frontend/middleware.js` sends link-preview bots on `/r/:id` to
`/share/:id` so shared links unfurl with the report's OG image.

### Reports store

`store.py` picks the backend from `DATABASE_URL`: unset → `NullReportStore` (nothing saved,
no permalinks/badges/deltas, scans still work); `memory://` → in-process store for local dev;
anything else → Postgres via asyncpg. The table is `backend/migrations/001_reports.sql`
(`id, url, domain, created_at, overall, payload jsonb`, RLS on with no policies). On Supabase
use the **pooler** connection string (Render has no IPv6); the pool runs with
`statement_cache_size=0` so the transaction pooler works. Database errors never fail a scan:
reads count as misses, a failed save returns the report without a `report_id`.

---

## Abuse Protection (public endpoint)

- Every outbound fetch of a user-supplied URL must go through `safety.assert_public_url` and
  use `event_hooks={"request": [check_outbound_request]}` so redirects are re-checked (SSRF).
- `POST /analyze` is rate-limited per IP via the `enforce_rate_limit` dependency
  (`RATE_LIMIT_PER_HOUR`, default 10); `POST /compare` uses `enforce_compare_rate_limit`,
  which costs 2.

## Tests

`cd backend && pip install -r requirements-dev.txt && pytest`. Tests must not import
`llm_analyzer` (it builds a Groq client at import time) or hit the network. Route tests
override the `get_scanner` / `get_store` dependencies in `reports.py` (see
`tests/test_reports.py`); `main` imports the pipeline lazily so this works.

---

## Environment Variables

### Backend (`.env` in `backend/`)
```
GROQ_API_KEY=gsk_...
FRONTEND_URL=http://localhost:5173
RATE_LIMIT_PER_HOUR=10   # optional
DATABASE_URL=            # optional: Postgres URL (Supabase pooler), or memory:// for local dev
PUBLIC_API_URL=          # optional: this API's public URL, for absolute og:image links
```

### Frontend (`.env` in `frontend/`)
```
VITE_API_URL=http://localhost:8000
```

On Vercel, `VITE_API_URL` is also read at runtime by `middleware.js`.

**Rules:**
- Never commit `.env` files. Always use `.env.example` with placeholder values.
- Never hardcode URLs — always read from `import.meta.env.VITE_API_URL` in React
  and `os.getenv()` in Python.

---

## App State Machine

The React app has exactly three visible states plus one error state. Manage with a single
`useState`:

```javascript
// In App.jsx
const [appState, setAppState] = useState('idle');     // 'idle' | 'loading' | 'done' | 'error'
const [results, setResults]   = useState(null);       // ResultsData | null
const [errorMsg, setErrorMsg] = useState('');         // string
```

State transitions:
```
idle  →  loading  →  done
                  →  error  →  idle (user edits URL and resubmits)
```

Alongside it, `route` (from `routes.js`, synced with `history.pushState`/`popstate`) picks
the view: `/` landing, `/r/:id` a saved report (loaded via `GET /reports/{id}`), `/compare`
the compare form and `/compare/:a/:b` a saved comparison. A finished scan pushes its
`/r/:id`, so the address bar is always the shareable link.

There is no back button in the loading state. If the user wants to cancel, they must
wait for the result and then click "New Analysis" in the header.

---

## LLM Usage Rules

1. **Model**: Always `openai/gpt-oss-120b` via Groq. Never change this without updating CLAUDE.md.
2. **Temperature**: Always `0.1` for structured JSON output calls.
3. **Max tokens**: `4000` for the main analysis call (it also returns the AI preview, and
   gpt-oss reasoning tokens count against the limit).
4. **System prompt**: Must instruct the model to return ONLY valid JSON, no markdown fences,
   no explanation.
5. **Parsing**: Wrap JSON parsing in try/except. If parsing fails, log the raw response and
   raise an HTTPException with a user-friendly message.
6. **Do not** make multiple LLM calls per analysis. One call, structured JSON response,
   generate all four artifacts from that single data structure.

---

## GitHub API Rules

- Base URL: `https://api.github.com/repos/{owner}/{repo}`
- No authentication in MVP — public repos only.
- Rate limit: 60 requests/hour unauthenticated. **Batch carefully.**
- Fetch at most **5 code files** beyond the README to stay within limits.
- Always set a `User-Agent` header: `User-Agent: AgentReady/0.1`
- Parse the GitHub URL to extract `owner` and `repo` before making any API calls.
  Handle URLs with trailing slashes, `.git` suffixes, and `/tree/main/` paths gracefully.

---

## File Download Behavior (Frontend)

Each artifact is downloaded via the Blob API. Use this exact pattern:

```javascript
function downloadFile(content, filename) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
```

Filenames per tab:
- Tab 1: `llms.txt`
- Tab 2: `audit-report.md`
- Tab 3: `mcp_server.ts`
- Tab 4: `openapi.yaml`

---

## CORS Configuration

FastAPI must allow requests from the frontend origin. In `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

---

## What NOT to Build (MVP Scope Guard)

If anyone (including me) suggests adding these, say no and reference this list:

- ❌ User authentication or accounts
- ❌ Database or persistence beyond a single reports store (scan results for permalinks,
  re-scan deltas, badges and caching — no user data, no accounts)
- ❌ Private GitHub repo support
- ❌ JavaScript SPA crawling (Playwright/Puppeteer)
- ❌ Multiple LLM calls per analysis
- ❌ Streaming responses
- ❌ Paid tiers or billing
- ❌ Email capture or newsletters
- ❌ Any analytics or tracking scripts
- ❌ Dark/light mode toggle (dark only)

---

## Slash Commands Available

Run these by typing `/command-name` in Claude Code:

| Command | When to Use |
|---|---|
| `/idea` | Brainstorm features, diagnose product decisions, explore "what if" |
| `/ui` | Design a new component, review a component against UI.md, generate Tailwind classes |
| `/backend` | Scaffold a new endpoint, write a new crawler function, debug a Python error |
| `/review` | Review any code file before committing |
| `/commit` | Stage, write a commit message, push to GitHub |
| `/readme` | Generate or update the README.md |

---

## Before Every Coding Session

1. Re-read this `CLAUDE.md` — take 30 seconds, it saves 30 minutes.
2. Check what state the codebase is in: `git status`, `git log --oneline -5`.
3. Know what you're building before writing a line: which file, which function, which state.
4. Run the backend: `cd backend && uvicorn main:app --reload`
5. Run the frontend: `cd frontend && npm run dev`

## Before Every Commit

1. Run `/review` on any file you changed.
2. Make sure no `.env` files are staged.
3. Make sure no `console.log` or `print()` debug statements are left in.
4. Run `/commit` to write a proper commit message.
