"""
transcript_fetcher.py
Fetches and cleans YouTube transcripts.
All YouTube API interactions are isolated in this module.

Enterprise standards applied (Tier 1):
- Input sanitization before any processing
- Structured logging with timing
- Retry with exponential backoff on transient failures
- Permanent failure detection (no retry on disabled/unavailable)
"""

import os
import re
import time
import random
import logging
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# ── Logging ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_URL_LENGTH = 200
MAX_RETRY_ATTEMPTS = 2
RETRY_BASE_DELAY = 1.0  # seconds, doubles each retry


# ── Custom exceptions ──────────────────────────────────────────────────────────
class InvalidURLError(Exception):
    pass

class NoTranscriptError(Exception):
    pass

class VideoUnavailableError(Exception):
    pass

class FetchError(Exception):
    pass


# ── Input sanitization ─────────────────────────────────────────────────────────
def _sanitize_url(url: str) -> str:
    """
    Sanitize and validate URL input before processing.

    Args:
        url: Raw URL string from user input

    Returns:
        Cleaned URL string

    Raises:
        InvalidURLError: URL fails basic sanity checks
    """
    url = url.strip()

    if len(url) > MAX_URL_LENGTH:
        raise InvalidURLError(
            f"URL is too long ({len(url)} characters). "
            "Please paste a standard YouTube URL."
        )

    if not url.startswith(('http://', 'https://')):
        raise InvalidURLError(
            "URL must start with http:// or https://. "
            "Please paste the full YouTube URL."
        )

    if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
        raise InvalidURLError(
            "This doesn't look like a YouTube URL. "
            "Please paste a link from youtube.com or youtu.be."
        )

    return url


# ── Video ID extraction ────────────────────────────────────────────────────────
def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from any standard URL format.

    Args:
        url: Sanitized YouTube URL string

    Returns:
        11-character video ID string

    Raises:
        InvalidURLError: Cannot extract video ID from URL
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise InvalidURLError(
        "Could not find a YouTube video ID in that URL. "
        "Please paste a link from youtube.com or youtu.be."
    )


# ── Transcript cleaning ────────────────────────────────────────────────────────
def clean_transcript(raw) -> str:
    """
    Convert raw transcript object to clean plain text.
    Handles both v1.2.4+ FetchedTranscript objects and legacy list format.

    Args:
        raw: FetchedTranscript object or list of segment dicts

    Returns:
        Clean plain text string
    """
    # v1.2.4+ returns a FetchedTranscript object — iterate to get segments
    try:
        text = ' '.join(snippet.text for snippet in raw)
    except AttributeError:
        # Fallback for legacy list format
        text = ' '.join(entry.get('text', '') for entry in raw)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Retry logic ────────────────────────────────────────────────────────────────
def _fetch_with_retry(video_id: str, proxies: dict | None) -> list:
    """
    Fetch transcript with exponential backoff retry on transient failures.
    Does NOT retry on permanent failures (disabled, unavailable).

    Args:
        video_id: YouTube video ID
        proxies:  Optional proxy configuration dict

    Returns:
        Raw transcript list from YouTubeTranscriptApi
    """
    last_exception = None

    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            if attempt > 0:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.info(
                    "Retry attempt %d for video_id=%s — waiting %.1fs",
                    attempt, video_id, delay
                )
                time.sleep(delay)

            api = YouTubeTranscriptApi()
            return api.fetch(video_id)

        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
            raise  # permanent failures — do not retry

        except Exception as exc:
            last_exception = exc
            logger.warning(
                "Attempt %d/%d failed for video_id=%s: %s",
                attempt + 1, MAX_RETRY_ATTEMPTS + 1, video_id, exc
            )

    raise last_exception


# ── Main public function ───────────────────────────────────────────────────────
def fetch_transcript(url: str, use_proxy: bool = False) -> str:
    """
    Fetch and return clean transcript text for a YouTube video.

    Args:
        url:       Any YouTube URL format
        use_proxy: Set True in cloud environments where YouTube blocks IPs

    Returns:
        Clean transcript as a plain text string

    Raises:
        InvalidURLError:       Not a recognisable YouTube URL
        NoTranscriptError:     Video has no captions/transcript
        VideoUnavailableError: Video is private or deleted
        FetchError:            Network or unexpected error
    """
    start = time.perf_counter()

    url = _sanitize_url(url)
    video_id = extract_video_id(url)

    logger.info("Fetching transcript for video_id=%s", video_id)

    proxies = None
    if use_proxy:
        proxy_url = os.environ.get('WEBSHARE_PROXY_URL', '')
        if proxy_url:
            proxies = {'http': proxy_url, 'https': proxy_url}

    time.sleep(random.uniform(1, 3))

    try:
        raw = _fetch_with_retry(video_id, proxies)
        text = clean_transcript(raw)

        if not text:
            raise NoTranscriptError(
                "This video's transcript appears to be empty. "
                "Try a different video."
            )

        elapsed = time.perf_counter() - start
        logger.info(
            "transcript fetched video_id=%s chars=%d elapsed=%.2fs",
            video_id, len(text), elapsed
        )
        return text

    except TranscriptsDisabled:
        logger.warning("TranscriptsDisabled video_id=%s", video_id)
        raise NoTranscriptError(
            "This video doesn't have captions or transcripts enabled. "
            "Try a video that has CC available."
        )
    except NoTranscriptFound:
        logger.warning("NoTranscriptFound video_id=%s", video_id)
        raise NoTranscriptError(
            "No transcript found for this video. "
            "Try a video with closed captions."
        )
    except VideoUnavailable:
        logger.warning("VideoUnavailable video_id=%s", video_id)
        raise VideoUnavailableError(
            "This video is private, deleted, or unavailable."
        )
    except (InvalidURLError, NoTranscriptError, VideoUnavailableError):
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error video_id=%s: %s", video_id, exc, exc_info=True
        )
        raise FetchError(f"Something went wrong fetching the transcript: {exc}")
