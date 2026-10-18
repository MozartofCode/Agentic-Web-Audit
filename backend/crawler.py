"""HTML, robots.txt and llms.txt parsing helpers shared by the site fetcher and the checks."""

from __future__ import annotations

from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

MAX_BODY_CHARS = 6000
API_LINK_KEYWORDS = ("/api", "/docs", "/swagger", "/openapi")

# AI crawlers and agents worth reporting on, by robots.txt user-agent token.
AI_BOTS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-User",
    "PerplexityBot",
    "Google-Extended",
    "Applebot-Extended",
    "CCBot",
)


def looks_like_llms_txt(text: str) -> bool:
    """An llms.txt file is markdown that starts with an H1 (per llmstxt.org)."""
    return text.lstrip().startswith("# ")


def blocked_ai_bots(robots_txt: str) -> list[str]:
    """Return the AI bots in AI_BOTS that robots.txt disallows from fetching the homepage."""
    parser = RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return [bot for bot in AI_BOTS if not parser.can_fetch(bot, "/")]


def get_meta_description(soup: BeautifulSoup) -> str:
    """Content of <meta name="description">, or ""."""
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def find_api_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Up to 10 absolute links that look like API docs or specs."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(keyword in href.lower() for keyword in API_LINK_KEYWORDS):
            links.append(urljoin(base_url, href))
    return list(dict.fromkeys(links))[:10]
