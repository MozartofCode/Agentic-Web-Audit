"""Groq API call and structured JSON response parsing (one call per analysis)."""

from __future__ import annotations

import json
import logging

from fastapi import HTTPException
from groq import AsyncGroq
from pydantic import ValidationError

from blind_reader import verify_preview
from models import ProductAnalysis
from prompts import SYSTEM_PROMPT, build_analysis_prompt, prompt_texts

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 0.1
MAX_TOKENS = 4000

client = AsyncGroq()


async def analyze_product(
    website_data: dict, github_data: dict, pages: list[dict] | None = None
) -> ProductAnalysis:
    """
    Send scraped data (homepage, key page excerpts, repo) to Groq in ONE call and parse the
    structured JSON response, including the "How AI sees you" preview.

    Raises HTTPException if the LLM call fails or the JSON is unparseable.
    """
    pages = pages or []
    user_prompt = build_analysis_prompt(website_data, github_data, pages)

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.error("Groq API call failed: %s", str(e))
        raise HTTPException(status_code=500, detail="AI analysis failed. Please try again.")

    raw = (response.choices[0].message.content or "").strip()

    try:
        analysis = ProductAnalysis(**json.loads(raw))
    except (json.JSONDecodeError, ValidationError, TypeError):
        logger.error("LLM response parsing failed. Raw: %s", raw[:500])
        raise HTTPException(
            status_code=500, detail="AI returned an unexpected format. Please try again."
        )

    texts = prompt_texts(website_data, pages)
    analysis.ai_preview = verify_preview(analysis.ai_preview.cleaned(), texts)
    return analysis
