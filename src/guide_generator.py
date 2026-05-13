"""
src/guide_generator.py

ADR-003: All LLM API calls live in this file. No other module should import
the anthropic SDK directly. To switch providers, change this file only.

ADR-002: Uses claude-haiku-4-5 for guide generation. Upgrade to Sonnet
requires updating the MODEL constant and re-testing on a sample set.

ADR-004: The prompt is loaded from prompts/guide_prompt.txt at call time,
versioned separately from code.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

# Default model per ADR-002. Override with GUIDE_MODEL env var for A/B testing.
MODEL = os.environ.get("GUIDE_MODEL", "claude-haiku-4-5")

# Prompt path resolved relative to repo root.
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "guide_prompt.txt"

# How much transcript to send. Haiku 4.5 has a large context window but
# guide quality plateaus past ~12k chars and cost grows linearly.
MAX_TRANSCRIPT_CHARS = 14000


class GuideGenerationError(Exception):
    """Raised when guide generation fails for a recoverable reason."""


def _load_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise GuideGenerationError(
            f"Prompt file missing at {PROMPT_PATH}. Did you commit prompts/?"
        )
    return PROMPT_PATH.read_text(encoding="utf-8")


def _get_api_key() -> Optional[str]:
    """Pull the Anthropic key from Streamlit secrets or env. Returns None
    if neither is configured — caller should fall back to rule-based."""
    # st.secrets when available
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def has_llm_configured() -> bool:
    return bool(_get_api_key())


def _strip_fences(text: str) -> str:
    """Tolerate models that wrap JSON in ```json ... ``` despite instructions."""
    return re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.M)


def generate_guide(transcript: str) -> dict:
    """Send the transcript to Claude and return a structured guide dict.

    Raises GuideGenerationError if the API call fails or returns malformed JSON.
    """
    api_key = _get_api_key()
    if not api_key:
        raise GuideGenerationError("ANTHROPIC_API_KEY not configured.")

    try:
        import anthropic
    except ImportError as e:
        raise GuideGenerationError(
            "anthropic SDK not installed. Add `anthropic` to requirements.txt."
        ) from e

    prompt = _load_prompt().replace("{transcript}", transcript[:MAX_TRANSCRIPT_CHARS])

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise GuideGenerationError(f"Claude API call failed: {e}") from e

    raw = resp.content[0].text if resp.content else ""
    try:
        guide = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise GuideGenerationError(
            f"Claude returned non-JSON output. First 200 chars: {raw[:200]!r}"
        ) from e

    return _normalize(guide)


def _normalize(guide: dict) -> dict:
    """Defensive normalization — ensure every field exists with the right type
    so downstream renderers don't need to guard."""
    return {
        "title": str(guide.get("title") or "How-to Guide").strip(),
        "summary": str(guide.get("summary") or "").strip(),
        "time_required": str(guide.get("time_required") or "").strip(),
        "tools": [str(t).strip() for t in (guide.get("tools") or []) if str(t).strip()],
        "steps": [
            {
                "title": str(s.get("title") or f"Step {i+1}").strip(),
                "body": str(s.get("body") or "").strip(),
                "time": str(s.get("time") or "").strip(),
            }
            for i, s in enumerate(guide.get("steps") or [])
        ],
        "tips": [str(t).strip() for t in (guide.get("tips") or []) if str(t).strip()],
    }

def validate_config() -> None:
    """Validate required environment variables are present."""
    if not _get_api_key():
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file or Streamlit secrets."
        )
# -----------------------------------------------------------------------------
# Rule-based fallback. Used only when no API key is configured (e.g. local
# dev before secrets are set). Not for production traffic.
# -----------------------------------------------------------------------------
def generate_guide_fallback(transcript: str) -> dict:
    import textwrap
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript) if len(s.strip()) > 8]
    n_steps = min(8, max(4, len(sentences) // 18))
    chunk = max(1, len(sentences) // n_steps) if n_steps else 1
    steps = []
    for i in range(n_steps):
        block = " ".join(sentences[i * chunk : (i + 1) * chunk]).strip()
        if not block:
            continue
        first = re.split(r"[.!?]", block, maxsplit=1)[0]
        steps.append({
            "title": textwrap.shorten(first.strip().capitalize(), width=70, placeholder="…") or f"Step {i+1}",
            "body": textwrap.shorten(block, width=320, placeholder="…"),
            "time": "",
        })
    return _normalize({
        "title": "How-to Guide (fallback mode)",
        "summary": textwrap.shorten(transcript, width=280, placeholder="…"),
        "time_required": "",
        "tools": [],
        "steps": steps,
        "tips": ["⚠ Configure ANTHROPIC_API_KEY in Streamlit secrets for AI-quality guides."],
    })
