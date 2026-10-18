"""FastAPI app init, CORS configuration, reports store lifecycle and route registration."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv

load_dotenv()  # must run before anything reads env (llm_analyzer reads GROQ_API_KEY on import)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from reports import router as reports_router
from store import create_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the reports store (a no-op store without DATABASE_URL) and close it on shutdown."""
    app.state.store = await create_store(os.getenv("DATABASE_URL"))
    try:
        yield
    finally:
        await app.state.store.close()


app = FastAPI(title="AgentReady API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.include_router(reports_router)


@app.get("/health")
async def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}
