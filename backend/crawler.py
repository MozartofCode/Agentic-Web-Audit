"""Website fetching and HTML parsing (httpx + BeautifulSoup)."""

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 10.0
MAX_BODY_CHARS = 6000
API_LINK_KEYWORDS = ("/api", "/docs", "/swagger", "/openapi")


async def crawl_website(url: str) -> dict:
    """
    Fetch and parse a website URL.

    Returns a dict with: title, description, headings, api_links, body_text.
    Raises HTTPException on fetch failure.
    """
    headers = {"User-Agent": "AgentReady/0.1 (+https://agentready.dev)"}

    try:
        async with httpx.AsyncClient(timeout=CRAWL_TIMEOUT, follow_redirects=True) as client:
            logger.info("Crawling %s", url)
            response = await client.get(url, headers=headers)
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

    return {
        "title": soup.find("title").get_text(strip=True) if soup.find("title") else "",
        "description": _get_meta_description(soup),
        "headings": [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:20]],
        "api_links": _find_api_links(soup, url),
        "body_text": soup.get_text(separator=" ", strip=True)[:MAX_BODY_CHARS],
    }


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
