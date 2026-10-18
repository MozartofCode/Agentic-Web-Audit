"""Website fetching and HTML parsing (httpx + BeautifulSoup)."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from safety import assert_public_url, check_outbound_request

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 10.0
MAX_BODY_CHARS = 6000
MAX_ROBOTS_CHARS = 50_000
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


async def crawl_website(url: str) -> dict:
    """
    Fetch and parse a website URL, plus its /robots.txt and /llms.txt.

    Returns a dict with: title, description, headings, api_links, body_text,
    has_llms_txt, blocked_ai_bots.
    Raises HTTPException on fetch failure or if the URL points to a private network.
    """
    await assert_public_url(url)
    headers = {"User-Agent": "AgentReady/0.1 (+https://agentready.dev)"}

    try:
        async with httpx.AsyncClient(
            timeout=CRAWL_TIMEOUT,
            follow_redirects=True,
            headers=headers,
            event_hooks={"request": [check_outbound_request]},
        ) as client:
            logger.info("Crawling %s", url)
            response, robots_resp, llms_resp = await asyncio.gather(
                client.get(url),
                _fetch_optional(client, urljoin(url, "/robots.txt")),
                _fetch_optional(client, urljoin(url, "/llms.txt")),
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=400,
            detail=f"Timed out connecting to {url}. The site may be too slow or blocking crawlers.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail=f"The site returned {e.response.status_code}. Try the GitHub URL alone.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=400, detail=f"Could not reach {url}. Check the URL and try again."
        )

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()

    robots_txt = _text_if_plain(robots_resp)

    return {
        "title": soup.find("title").get_text(strip=True) if soup.find("title") else "",
        "description": _get_meta_description(soup),
        "headings": [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:20]],
        "api_links": _find_api_links(soup, url),
        "body_text": soup.get_text(separator=" ", strip=True)[:MAX_BODY_CHARS],
        "has_llms_txt": looks_like_llms_txt(_text_if_plain(llms_resp)),
        "blocked_ai_bots": blocked_ai_bots(robots_txt) if robots_txt else [],
    }


async def _fetch_optional(client: httpx.AsyncClient, url: str) -> Optional[httpx.Response]:
    """GET a well-known file; any failure just means 'not there'."""
    try:
        return await client.get(url)
    except (httpx.HTTPError, HTTPException):
        return None


def _text_if_plain(response: Optional[httpx.Response]) -> str:
    """
    Body of a successful non-HTML response, else "".

    SPAs and catch-all routes answer every path with 200 + index.html, so a 200
    alone doesn't prove a /robots.txt or /llms.txt file exists.
    """
    if response is None or response.status_code != 200:
        return ""
    if "html" in response.headers.get("content-type", "").lower():
        return ""
    return response.text[:MAX_ROBOTS_CHARS]


def looks_like_llms_txt(text: str) -> bool:
    """An llms.txt file is markdown that starts with an H1 (per llmstxt.org)."""
    return text.lstrip().startswith("# ")


def blocked_ai_bots(robots_txt: str) -> list[str]:
    """Return the AI bots in AI_BOTS that robots.txt disallows from fetching the homepage."""
    parser = RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return [bot for bot in AI_BOTS if not parser.can_fetch(bot, "/")]


def _get_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def _find_api_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(keyword in href.lower() for keyword in API_LINK_KEYWORDS):
            links.append(urljoin(base_url, href))
    return list(dict.fromkeys(links))[:10]
