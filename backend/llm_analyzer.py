"""Groq API call and structured JSON response parsing."""

import json
import logging

from fastapi import HTTPException
from groq import AsyncGroq
from pydantic import ValidationError

from models import ProductAnalysis
from prompts import SYSTEM_PROMPT, build_analysis_prompt

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 0.1
MAX_TOKENS = 2000

client = AsyncGroq()


async def analyze_product(website_data: dict, github_data: dict) -> ProductAnalysis:
    """
    Send scraped data to Groq and parse the structured JSON response.

    Raises HTTPException if the LLM call fails or the JSON is unparseable.
    """
    user_prompt = build_analysis_prompt(website_data, github_data)

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
    except Exception as e:
        logger.error("Groq API call failed: %s", str(e))
        raise HTTPException(status_code=500, detail="AI analysis failed. Please try again.")

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
        return ProductAnalysis(**data)
    except (json.JSONDecodeError, ValidationError):
        logger.error("LLM response parsing failed. Raw: %s", raw[:500])
        raise HTTPException(
            status_code=500, detail="AI returned an unexpected format. Please try again."
        )
