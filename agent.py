"""
Text Summarization Agent built with Google ADK + Gemini.
Exposes a /summarize endpoint that accepts text and returns a structured summary.
"""

import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# ── Tool definition ──────────────────────────────────────────────────────────

def summarize_text(text: str) -> dict:
    """
    Summarize the provided text.

    Args:
        text: The raw text to be summarized.

    Returns:
        A dict with keys: summary, key_points, word_count.
    """
    # This function is intentionally left as a stub — the agent itself
    # (powered by Gemini) will produce the structured output via its
    # system prompt + tool schema.  The return value here is only used
    # when the tool is called directly in unit tests.
    return {
        "summary": "",
        "key_points": [],
        "word_count": len(text.split()),
    }


# ── Agent definition ─────────────────────────────────────────────────────────

def create_summarization_agent() -> Agent:
    """Instantiate and return the ADK Summarization Agent."""

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    agent = Agent(
        name="text_summarization_agent",
        model=LiteLlm(model=f"google/{model_name}"),
        description=(
            "An AI agent that summarises text. "
            "Given any input text it returns a concise summary, "
            "a bullet-point list of key ideas, and the original word count."
        ),
        instruction=(
            "You are an expert text-summarization assistant. "
            "When the user provides text, respond ONLY with valid JSON "
            "(no markdown fences) in this exact shape:\n"
            "{\n"
            '  "summary": "<2-3 sentence summary>",\n'
            '  "key_points": ["<point 1>", "<point 2>", ...],\n'
            '  "word_count": <integer>\n'
            "}\n\n"
            "Rules:\n"
            "- summary must be 2-3 sentences, third-person neutral tone.\n"
            "- key_points must be 3-5 concise bullet strings.\n"
            "- word_count is the number of whitespace-separated tokens in the "
            "original input.\n"
            "- Return nothing outside the JSON object."
        ),
        tools=[summarize_text],
    )
    return agent


# ── Module-level singleton used by main.py ───────────────────────────────────
root_agent = create_summarization_agent()
