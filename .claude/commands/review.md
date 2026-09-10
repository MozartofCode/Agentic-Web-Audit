---
description: Review any code file before committing. Use when you've finished writing a feature and want a thorough quality check before it goes into git. Run this on every file you changed. Covers correctness, style, security, and design system compliance.
---

# /review — Code Review

You are a senior engineer doing a thorough pre-commit code review.
You are not trying to find something wrong — you are trying to ship quality code.
Be direct, specific, and prioritize issues by severity.

---

## How to Run This Review

The user will paste a file or say "review [filename]". You will:

1. Read the file carefully
2. Run through every checklist section that applies (Python or React/JS)
3. Output a structured review with: Critical → Warnings → Suggestions → Approved items
4. Give a verdict: **APPROVE** / **REQUEST CHANGES**

If there are no critical or warning issues: APPROVE and move on.
If there are critical issues: list them and stop — do not suggest minor things until criticals are fixed.

---

## Severity Levels

| Level | Meaning | Block commit? |
|---|---|---|
| 🔴 CRITICAL | Bug, security issue, breaks the app, violates a hard rule in CLAUDE.md | YES |
| 🟡 WARNING | Bad practice, tech debt, violates a soft convention, will cause problems later | Discuss |
| 🔵 SUGGESTION | Style, readability, small improvement, optional | NO |
| ✅ APPROVED | This is done well — worth calling out | N/A |

---

## Python Review Checklist

### Correctness
```
[ ] Every async function uses `await` properly — no blocking calls inside async functions
[ ] httpx calls use `AsyncClient` context manager, not `httpx.get()` directly
[ ] `raise_for_status()` is called on all HTTP responses
[ ] All try/except blocks catch specific exceptions, not bare `except:`
[ ] JSON parsing is in a try/except with a meaningful error message
[ ] No hardcoded API keys, URLs, or secrets in code
[ ] Environment variables are read with `os.getenv()` and have fallbacks or clear errors if missing
```

### FastAPI Specific
```
[ ] Route handler functions are `async def`, not `def`
[ ] Request body uses a Pydantic model, not `dict` or `Body(...)`
[ ] Errors raise `HTTPException`, not `return {"error": ...}`
[ ] Response model is declared on the route decorator: `response_model=AnalyzeResponse`
[ ] No business logic directly in `main.py` — it belongs in a module
```

### Code Quality
```
[ ] All functions have type hints on parameters and return type
[ ] No `print()` statements — use `logger.info()`, `logger.error()`, etc.
[ ] No dead code (commented-out blocks, unused imports, unused variables)
[ ] Function names are verbs: `crawl_website()`, `fetch_github_repo()`, `analyze_product()`
[ ] Constants are UPPER_SNAKE_CASE at module level, not magic values inline
[ ] Line length ≤ 100 characters
[ ] `requirements.txt` is updated if a new package was imported
```

### Security
```
[ ] No user input is interpolated directly into shell commands or SQL
[ ] URLs from user input are validated by Pydantic `HttpUrl` before use
[ ] No sensitive data (API keys, user URLs) is logged at INFO level
[ ] CORS allows_origins does not include `["*"]` — it must reference FRONTEND_URL
```

---

## React / JavaScript Review Checklist

### Correctness
```
[ ] No `console.log()` — remove before committing
[ ] `fetch()` calls only exist in `src/api.js`, never inside components
[ ] All state mutations go through `useState` setters — no direct mutation
[ ] `useEffect` dependencies array is correct and complete
[ ] No missing `key` prop on list-rendered elements
[ ] Async errors in `api.js` are caught and returned as `{ error: "..." }` — never unhandled
```

### React Patterns
```
[ ] Functional components only — no class components
[ ] Props named `on[Event]` for callback props: `onSubmit`, `onTabChange`
[ ] One component per file, filename matches component name
[ ] No prop drilling more than 2 levels deep (for MVP this is fine — note if it happens)
[ ] Loading and error states are handled in every component that fetches data
```

### Design System Compliance
```
[ ] No Tailwind default color classes: `bg-gray-*`, `text-blue-*`, etc.
[ ] Only custom tokens used: `bg-bg-surface`, `text-text-primary`, `text-accent`, etc.
[ ] Border radius is `rounded` (8px) — no `rounded-xl`, `rounded-2xl`
[ ] No inline `style={{}}` except for CSS custom property values
[ ] No box shadow classes (`shadow-md`, etc.) — only the focus ring shadow is allowed
[ ] Hover states use `transition-colors duration-[100ms]` not `transition-all`
[ ] No animation classes that aren't in the UI.md spec
[ ] Mobile: nothing overflows at `max-w-sm` (375px)
```

### Accessibility
```
[ ] All `<input>` elements have associated `<label>` elements (not just placeholders)
[ ] Icon-only buttons have `aria-label`
[ ] Error messages use `role="alert"`
[ ] Loading state uses `role="status"` and `aria-live="polite"`
[ ] Interactive elements are reachable by Tab key
```

---

## Review Output Format

```
## Review: [filename]

### 🔴 Critical Issues

1. [File: line X] `httpx.get()` is used synchronously inside an async function.
   This will block the event loop and make the server non-concurrent.
   Fix: use `async with httpx.AsyncClient() as client: await client.get()`

### 🟡 Warnings

1. [Line 45] `except Exception` is too broad. If Groq raises a rate limit error,
   it'll be swallowed and the user gets a generic 500.
   Fix: catch `groq.RateLimitError` specifically and return a 429 with a message.

### 🔵 Suggestions

1. [Line 78] The URL parsing logic is complex enough to deserve its own function
   `_parse_github_url()` with a docstring. Currently it's inline in `fetch_github_repo()`.

### ✅ Approved

- Pydantic models are comprehensive and well-named
- Logging is correctly configured with `logger = logging.getLogger(__name__)`
- The CORS middleware setup matches the spec in CLAUDE.md

### Verdict: REQUEST CHANGES
Fix the 1 critical issue and the 1 warning before committing.
```

---

## Things That Are Always CRITICAL (Zero Tolerance)

1. Hardcoded API key, token, or secret anywhere in code
2. Committed `.env` file
3. `console.log()` or `print()` in committed code (remove, don't comment out)
4. Synchronous HTTP call inside an async function
5. `allow_origins=["*"]` in CORS config
6. User input passed directly to `eval()`, subprocess, or SQL string interpolation
7. Missing error handling on any network call
8. A component that renders a blank/broken state when `results` is null or undefined
