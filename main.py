"""
FastAPI application that wraps the ADK Summarization Agent.

Endpoints
---------
GET  /            Health-check
POST /summarize   Run the agent and return a JSON summary
POST /chat        Generic single-turn chat with the agent
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from agent import create_summarization_agent

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Globals populated at startup ─────────────────────────────────────────────
_runner: Runner | None = None
_session_service: InMemorySessionService | None = None

APP_NAME = "text_summarization_agent"
USER_ID = "api_user"

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _runner, _session_service
    logger.info("Initialising ADK runner …")
    _session_service = InMemorySessionService()
    agent = create_summarization_agent()
    _runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=_session_service,
    )
    logger.info("ADK runner ready.")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Text Summarization Agent",
    description="ADK + Gemini powered text-summarization microservice.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────
class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Text to summarise (≥ 10 chars)")
    session_id: str | None = Field(None, description="Optional session ID for continuity")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class SummarizeResponse(BaseModel):
    summary: str
    key_points: list[str]
    word_count: int
    session_id: str
    elapsed_ms: float


class ChatResponse(BaseModel):
    response: str
    session_id: str
    elapsed_ms: float


# ── Helpers ───────────────────────────────────────────────────────────────────
def _strip_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    return text.strip()


async def _run_agent(user_message: str, session_id: str) -> str:
    """Send a message to the agent and collect the final text response."""
    await _session_service.create_session(  # type: ignore[union-attr]
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    final_text = ""
    async for event in _runner.run_async(  # type: ignore[union-attr]
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                p.text for p in event.content.parts if hasattr(p, "text")
            )
    return final_text


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "service": "text-summarization-agent",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    }


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}


@app.post("/summarize", response_model=SummarizeResponse, tags=["agent"])
async def summarize(req: SummarizeRequest):
    """Run the summarization agent on the provided text."""
    t0 = time.perf_counter()
    session_id = req.session_id or f"session_{int(time.time() * 1000)}"

    try:
        raw = await _run_agent(
            f"Please summarise the following text:\n\n{req.text}",
            session_id=session_id,
        )
    except Exception as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Parse JSON from model output
    try:
        parsed: dict[str, Any] = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        # Fallback: wrap raw text in a minimal structure
        parsed = {
            "summary": raw.strip(),
            "key_points": [],
            "word_count": len(req.text.split()),
        }

    elapsed = (time.perf_counter() - t0) * 1000
    return SummarizeResponse(
        summary=parsed.get("summary", ""),
        key_points=parsed.get("key_points", []),
        word_count=parsed.get("word_count", len(req.text.split())),
        session_id=session_id,
        elapsed_ms=round(elapsed, 2),
    )


@app.post("/chat", response_model=ChatResponse, tags=["agent"])
async def chat(req: ChatRequest):
    """Send any free-form message to the agent."""
    t0 = time.perf_counter()
    session_id = req.session_id or f"session_{int(time.time() * 1000)}"

    try:
        response = await _run_agent(req.message, session_id=session_id)
    except Exception as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = (time.perf_counter() - t0) * 1000
    return ChatResponse(
        response=response,
        session_id=session_id,
        elapsed_ms=round(elapsed, 2),
    )


# ── Entry-point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
