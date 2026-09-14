# Contributing to AgentReady

Thanks for considering a contribution. This is a small MVP, so the process is intentionally
lightweight.

## Before you start

1. Read [`CLAUDE.md`](CLAUDE.md) — it's the source of truth for architecture, coding standards,
   the `/analyze` API contract, and (importantly) a **"What NOT to Build"** list of features
   that are out of scope on purpose (accounts, database, private repos, billing, etc.). PRs
   adding any of those will be declined regardless of quality — open an issue first to discuss
   scope changes.
2. Check open issues and PRs so you're not duplicating work.
3. For anything non-trivial (new endpoint, new component, changed API contract), open an issue
   first to discuss the approach before writing code.

## Local setup

See the [README](README.md#getting-started) for backend/frontend setup. You'll need your own
free [Groq API key](https://console.groq.com/keys) — never commit a real key; `.env` files are
gitignored and `.env.example` is what gets committed.

## Coding standards

Full detail is in `CLAUDE.md`, summarized here:

**Backend (Python / FastAPI)**
- Async throughout — `httpx.AsyncClient`, never blocking calls or the `requests` library.
- Type hints on every function.
- Pydantic models for all request/response shapes crossing an API boundary — no raw dicts.
- Raise `HTTPException(status_code=..., detail="human readable message")` for user-facing
  errors; never hand-roll `{"error": ...}` responses.
- Use `logging`, not `print()`.
- Max line length 100.

**Frontend (React / Tailwind)**
- Functional components only, one component per file, filename matches component name.
- All `fetch` calls go through `src/api.js` — never call `fetch()` directly in a component.
- Only the color tokens and design values defined in `UI.md` / `src/index.css` — no default
  Tailwind colors (`bg-gray-900`, `text-blue-500`, etc.), no inline styles.
- `useState`/`useCallback` for local state — no new state libraries for this MVP.

## Before opening a PR

1. Test the change locally end-to-end (backend running, frontend hitting it) — this project has
   no automated test suite yet, so manual verification matters.
2. Run `npm run lint` in `frontend/` and fix anything it flags.
3. Make sure you haven't committed a `.env` file, an API key, or a `console.log`/`print()`
   debug statement.
4. Write a commit message that explains *why*, not just *what*.

## Reporting bugs / suggesting features

Open a GitHub issue. For bugs, include the URL you tested with (if not sensitive), what you
expected, and what happened instead — backend logs are especially useful since most failures
surface there first (crawl timeout, GitHub rate limit, LLM parse failure).
