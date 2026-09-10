---
description: Stage changed files, write a conventional commit message, and push to GitHub. Use after finishing a feature or fix and after running /review. This command handles the full git workflow so commit messages are always clean and consistent.
---

# /commit — Git Commit & Push

You handle the full git commit workflow: check what changed, write a great commit message,
stage the right files, and push. You never commit `.env` files. You never write vague messages.

---

## Step-by-Step Workflow

Run these commands in order and show the user the output of each step.

### Step 1: Check status
```bash
git status
git diff --stat
```
Show the user a summary of what changed. Ask if this matches what they intended to commit.

### Step 2: Safety checks
```bash
# Make sure no .env files are staged or untracked in a way that could be committed
git status --short | grep "\.env"

# Make sure no API keys are in the diff
git diff | grep -i "gsk_\|api_key\|secret\|password\|token"
```

If either check finds something, **stop immediately** and tell the user. Do not proceed.

### Step 3: Review changed files
For each changed file, quickly scan for:
- `console.log()` or `print()` debug statements
- Hardcoded localhost URLs that should be env vars
- TODO comments that were meant to be resolved

List any issues found. Ask the user to confirm before proceeding.

### Step 4: Stage files
```bash
# Stage specific files (preferred over `git add .` — be intentional)
git add [list of files the user wants to commit]
```

Never use `git add .` without showing the user what it would include first.
If the user says "add everything", run `git status` first and confirm each file category:
- Source files: ✅ stage
- `.env` files: ❌ never stage
- `node_modules/`, `venv/`, `__pycache__/`: ❌ never stage (should be gitignored)
- Generated files (build artifacts, dist/): confirm with user

### Step 5: Write the commit message
Generate a commit message using **Conventional Commits** format:

```
<type>(<scope>): <short description in present tense, max 72 chars>

[optional body — what changed and why, not how]

[optional footer — closes issue, breaking change note]
```

**Types:**
| Type | When to use |
|---|---|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `style` | UI/CSS changes, no logic change |
| `refactor` | Code restructure, no behavior change |
| `docs` | README, comments, docstrings |
| `chore` | Dependencies, config, tooling |
| `test` | Adding or fixing tests |
| `perf` | Performance improvement |

**Scopes for this project:**
| Scope | What it covers |
|---|---|
| `crawler` | Website crawling logic |
| `github` | GitHub API fetcher |
| `llm` | Groq API and prompt logic |
| `artifacts` | Artifact generator (llms.txt, MCP, OpenAPI, audit) |
| `api` | FastAPI routes and models |
| `ui` | React components, CSS |
| `config` | Environment, CORS, app setup |
| `deps` | requirements.txt, package.json changes |

**Good commit message examples:**
```
feat(artifacts): generate MCP server TypeScript scaffold from core_actions

Add artifact_generator.generate_mcp_server() that takes a ProductAnalysis
and returns a TypeScript MCP server with one tool stub per detected action.
Each stub includes a JSON Schema inputSchema and a TODO comment body.
```
```
fix(crawler): handle websites that return 403 with a clear error message

Previously, a 403 response raised an unhandled httpx.HTTPStatusError.
Now raises HTTPException(400) with a message telling the user to try
their GitHub URL alone.
```
```
style(ui): apply dot grid background to landing hero section

Pure CSS implementation using background-image radial-gradient with
a radial mask. No library dependency. Respects prefers-reduced-motion.
```

**Bad commit messages (never write these):**
```
fix stuff
update code
wip
changes
asdfgh
```

### Step 6: Commit
```bash
git commit -m "<type>(<scope>): <subject>" -m "<body if needed>"
```

### Step 7: Push
```bash
git push origin main
```

If pushing to a branch other than main, confirm the branch name with the user first.

---

## Gitignore Reminder

Make sure these are in `.gitignore` before the first commit. If they're not, add them:

```
# Backend
backend/.env
backend/venv/
backend/__pycache__/
backend/*.pyc
backend/.pytest_cache/

# Frontend
frontend/.env
frontend/node_modules/
frontend/dist/
frontend/.vite/

# General
.DS_Store
*.log
```

---

## Common Git Situations

### "I made changes in the wrong branch"
```bash
git stash
git checkout -b correct-branch-name
git stash pop
```

### "I committed a .env file by mistake"
```bash
# Remove from tracking but keep the file locally
git rm --cached backend/.env
echo "backend/.env" >> .gitignore
git add .gitignore
git commit -m "chore(config): remove .env from tracking"
# THEN rotate the API key immediately — it may already be in git history
```

### "I need to undo my last commit (not pushed yet)"
```bash
git reset --soft HEAD~1   # keeps changes staged
```

### "I need to add a forgotten file to the last commit"
```bash
git add forgotten-file.py
git commit --amend --no-edit
```

---

## After Every Push

Say:
> "Pushed. Branch is up to date. Here's what was committed:"

Then show the one-line log of the last commit:
```bash
git log --oneline -1
```
