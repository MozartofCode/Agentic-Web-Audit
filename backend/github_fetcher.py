"""GitHub REST API integration (unauthenticated, public repos only)."""

import base64
import logging
import re

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

GITHUB_TIMEOUT = 10.0
MAX_SOURCE_FILES = 5
MAX_SOURCE_FILE_CHARS = 1000
README_CHARS = 4000
FILE_TREE_CAP = 100
SOURCE_DIR_PREFIXES = ("routes/", "api/", "controllers/")
TECH_STACK_FILES = ("package.json", "pyproject.toml")
SPEC_FILENAMES = ("openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json")


async def fetch_github_repo(github_url: str) -> dict:
    """
    Fetch README, file tree, and relevant source files from a public GitHub repo.

    Raises HTTPException if the repo is not found, private, or rate-limited.
    """
    owner, repo = _parse_github_url(github_url)
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AgentReady/0.1",
    }

    async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT, follow_redirects=True) as client:
        logger.info("Fetching GitHub repo %s/%s", owner, repo)
        repo_resp = await client.get(base, headers=headers)
        if repo_resp.status_code == 404:
            raise HTTPException(
                status_code=400,
                detail="GitHub repo not found. Check the URL or make sure it's public.",
            )
        if repo_resp.status_code == 403:
            raise HTTPException(
                status_code=429, detail="GitHub rate limit hit, try again in 1 hour."
            )
        repo_resp.raise_for_status()
        repo_data = repo_resp.json()

        readme_text = await _fetch_readme(client, base, headers)

        tree_resp = await client.get(f"{base}/git/trees/HEAD?recursive=1", headers=headers)
        file_tree: list[str] = []
        if tree_resp.status_code == 200:
            file_tree = [
                f["path"] for f in tree_resp.json().get("tree", []) if f.get("type") == "blob"
            ]

        source_files = await _fetch_source_files(client, base, headers, file_tree)

    return {
        "repo_name": repo_data.get("name", ""),
        "description": repo_data.get("description", ""),
        "language": repo_data.get("language", ""),
        "readme": readme_text[:README_CHARS],
        "file_tree": file_tree[:FILE_TREE_CAP],
        "source_files": source_files,
    }


def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from any common GitHub URL format."""
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if not match:
        raise HTTPException(status_code=400, detail="That doesn't look like a valid GitHub URL.")
    owner = match.group(1)
    repo = match.group(2)
    repo = re.sub(r"\.git$", "", repo)
    return owner, repo


async def _fetch_readme(client: httpx.AsyncClient, base: str, headers: dict) -> str:
    resp = await client.get(f"{base}/readme", headers=headers)
    if resp.status_code != 200:
        return ""
    content = resp.json().get("content", "")
    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""


async def _fetch_source_files(
    client: httpx.AsyncClient, base: str, headers: dict, file_tree: list[str]
) -> dict[str, str]:
    candidates = [
        path
        for path in file_tree
        if path.startswith(SOURCE_DIR_PREFIXES) or path in TECH_STACK_FILES or path in SPEC_FILENAMES
    ][:MAX_SOURCE_FILES]

    source_files: dict[str, str] = {}
    for path in candidates:
        resp = await client.get(f"{base}/contents/{path}", headers=headers)
        if resp.status_code != 200:
            continue
        content = resp.json().get("content", "")
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            continue
        source_files[path] = decoded[:MAX_SOURCE_FILE_CHARS]

    return source_files
