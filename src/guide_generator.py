"""
guide_generator.py
ALL Claude API calls live here and ONLY here.
Converts transcript text into a formatted step-by-step guide.

Enterprise standards applied (Tier 1):
- Startup validation of required environment variables
- Structured logging with token usage tracking
- Retry with exponential backoff on transient API errors
- Request timeout enforcement
- Token cost logging for governance
"""

import os
import time
import logging
import anthropic

# ── Logging ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MODEL = os.environ.get('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')
MAX_TOKENS = int(os.environ.get('CLAUDE_MAX_TOKENS', '2000'))
MAX_TRANSCRIPT_CHARS = 12000
MAX_RETRY_ATTEMPTS = 2
RETRY_BASE_DELAY = 1.0
TOKEN_COST_ALERT_THRESHOLD = 1500  # warn if input exceeds this


# ── Startup validation ─────────────────────────────────────────────────────────
def validate_config() -> None:
    """
    Validate required environment variables at startup.
    Call this once when the app launches — fail fast, not at request time.

    Raises:
        EnvironmentError: Required configuration is missing
    """
    required = ['ANTHROPIC_API_KEY']
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Check your .env file."
        )
    logger.info(
        "Config validated — model=%s max_tokens=%d", MODEL, MAX_TOKENS
    )


# ── Prompt loading ─────────────────────────────────────────────────────────────
def _load_prompt() -> str:
    """Load prompt template from versioned file. Falls back to inline default."""
    prompt_path = os.path.join(
        os.path.dirname(__file__), '..', 'prompts', 'guide_prompt.txt'
    )
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
            logger.debug("Loaded prompt from %s", prompt_path)
            return template
    except FileNotFoundError:
        logger.warning(
            "guide_prompt.txt not found — using inline default prompt"
        )
        return _default_prompt()


def _default_prompt() -> str:
    return """You are a technical writer converting a YouTube video transcript into a clear, printable step-by-step guide.

TRANSCRIPT:
{transcript}

Create a step-by-step guide using ONLY information from the transcript above.
Do NOT add steps, materials, or tips not mentioned in the transcript.
Do NOT hallucinate. If the transcript doesn't mention a time estimate, omit that section.

Format your response EXACTLY as follows:

## [Descriptive Guide Title]

### What You'll Need
- [item]

### Time Required
[Estimate if mentioned, otherwise omit this section]

### Steps
1. **[Step Title]**
   [2-3 sentence description]

### Tips & Warnings
- [Pro tip or safety warning from the video]

### Summary
[One short paragraph recap]

Use plain, direct language. No motivational filler. No padding."""


# ── API call with retry ────────────────────────────────────────────────────────
def _call_api_with_retry(client: anthropic.Anthropic, prompt: str) -> anthropic.types.Message:
    """
    Call Claude API with exponential backoff retry on transient errors.

    Args:
        client: Authenticated Anthropic client
        prompt: Fully formatted prompt string

    Returns:
        Anthropic Message response object
    """
    last_exception = None

    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            if attempt > 0:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.info(
                    "API retry attempt %d — waiting %.1fs", attempt, delay
                )
                time.sleep(delay)

            return client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{'role': 'user', 'content': prompt}]
            )

        except anthropic.RateLimitError as exc:
            last_exception = exc
            logger.warning("Rate limit hit attempt %d: %s", attempt + 1, exc)

        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
        ):
            raise  # permanent — do not retry

        except Exception as exc:
            last_exception = exc
            logger.warning(
                "API error attempt %d: %s", attempt + 1, exc
            )

    raise last_exception


# ── Main public function ───────────────────────────────────────────────────────
def generate_guide(transcript: str) -> str:
    """
    Convert transcript text to a formatted step-by-step guide via Claude API.

    Args:
        transcript: Clean transcript text from transcript_fetcher

    Returns:
        Formatted guide as a markdown string

    Raises:
        ValueError:      Transcript is empty
        RuntimeError:    Claude API call failed
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty — cannot generate a guide.")

    start = time.perf_counter()

    # Truncate if needed
    truncated = False
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + '...[transcript truncated]'
        truncated = True
        logger.info("Transcript truncated to %d chars", MAX_TRANSCRIPT_CHARS)

    prompt_template = _load_prompt()
    prompt = prompt_template.replace('{transcript}', transcript)

    # Warn on large inputs
    estimated_input_tokens = len(prompt) // 4
    if estimated_input_tokens > TOKEN_COST_ALERT_THRESHOLD:
        logger.warning(
            "Large input estimated at ~%d tokens — cost may be elevated",
            estimated_input_tokens
        )

    try:
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not found. Check your .env file."
            )

        client = anthropic.Anthropic(api_key=api_key)
        message = _call_api_with_retry(client, prompt)

        # Log token usage for cost governance
        usage = message.usage
        elapsed = time.perf_counter() - start
        logger.info(
            "Guide generated — input_tokens=%d output_tokens=%d "
            "elapsed=%.2fs truncated=%s",
            usage.input_tokens, usage.output_tokens, elapsed, truncated
        )

        guide_text = message.content[0].text
        return guide_text.strip()

    except anthropic.APIConnectionError as exc:
        logger.error("API connection error: %s", exc)
        raise RuntimeError(
            "Could not connect to Claude API. "
            "Check your internet connection."
        )
    except anthropic.AuthenticationError as exc:
        logger.error("API authentication error: %s", exc)
        raise RuntimeError(
            "Invalid Anthropic API key. Check your .env file."
        )
    except anthropic.RateLimitError as exc:
        logger.error("Rate limit exceeded after retries: %s", exc)
        raise RuntimeError(
            "Claude API rate limit reached. "
            "Please wait a moment and try again."
        )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("Unexpected guide generation error: %s", exc, exc_info=True)
        raise RuntimeError(f"Guide generation failed: {exc}")
