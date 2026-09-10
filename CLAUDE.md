# AgentReady — Claude Code Project Brain

You are building **AgentReady**: a free, no-login web tool that takes a public website URL
and/or a public GitHub repo URL, analyzes the product using AI, and generates four
agent-readiness artifacts: `llms.txt`, an audit report, an MCP server scaffold, and an
OpenAPI spec draft.

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
│   ├── main.py
│   ├── crawler.py
│   ├── github_fetcher.py
│   ├── llm_analyzer.py
│   ├── artifact_generator.py
│   ├── models.py
│   ├── prompts.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── Header.jsx
    │   │   ├── LandingView.jsx
    │   │   ├── LoadingView.jsx
    │   │   ├── ResultsView.jsx
    │   │   ├── InputForm.jsx
    │   │   ├── AuditScoreCard.jsx
    │   │   ├── ArtifactSection.jsx
    │   │   └── ErrorBanner.jsx
    │   ├── api.js
    │   └── main.jsx
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
| LLM | Groq API — `llama-3.3-70b-versatile` | Temperature always `0.1` for structured output |
| GitHub data | GitHub REST API (unauthenticated) | Public repos only |
| Syntax highlighting | `react-syntax-highlighter` | Custom theme in UI.md |
| Deployment | Vercel (frontend), Railway (backend) | |

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
  "github_url": "https://github.com/..."  // nullable
  // At least one must be non-null
}
```

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
  }
}
```

Error (400):
```json
{ "detail": "Human-readable error message" }
```

---

## Environment Variables

### Backend (`.env` in `backend/`)
```
GROQ_API_KEY=gsk_...
FRONTEND_URL=http://localhost:5173
```

### Frontend (`.env` in `frontend/`)
```
VITE_API_URL=http://localhost:8000
```

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

There is no back button in the loading state. If the user wants to cancel, they must
wait for the result and then click "New Analysis" in the header.

---

## LLM Usage Rules

1. **Model**: Always `llama-3.3-70b-versatile` via Groq. Never change this without updating CLAUDE.md.
2. **Temperature**: Always `0.1` for structured JSON output calls.
3. **Max tokens**: `2000` for the main analysis call.
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
- ❌ Database or persistence of any kind
- ❌ Private GitHub repo support
- ❌ JavaScript SPA crawling (Playwright/Puppeteer)
- ❌ Multiple LLM calls per analysis
- ❌ Streaming responses
- ❌ Sharing/permalink features
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
