# CLAUDE.md
## Architecture Rules and Session Context — Video-to-PDF-Guide-Creator

**Version:** 1.0
**Last Updated:** May 2026
**Read this file at the start of every Claude Code session before writing any code.**

---

## Project Identity

**Name:** Video-to-PDF-Guide-Creator
**Purpose:** Convert YouTube how-to video transcripts into formatted,
printable step-by-step guides using Claude AI.
**Owner:** Randy Skiles
**GitHub:** github.com/joatsaint/video-to-pdf-guide-creator
**Stage:** MVP — Streamlit web app

---

## Non-Negotiable Architecture Rules

These rules apply to every session. Do not deviate without creating an ADR.

1. **Spec before code** — No module is built without a spec in this file first
2. **Model-agnostic** — All Claude API calls live in `src/guide_generator.py` only
3. **No secrets in code** — All API keys in `.env` only, never hardcoded
4. **Atomic writes** — All file operations use temp-file-then-rename pattern
5. **Graceful failure** — Every user-facing error shows a helpful message, never a stack trace
6. **Mobile-first UI** — Streamlit layout must work on phone screens
7. **One job per module** — Each file does one thing and does it completely
8. **Branch protection** — No direct pushes to master. All changes via PR. Tests must pass before merge.
9. **Cost alerts** — Set Anthropic console spend alerts at $5 and $10/month. Check before every session.
10. **Download before git** — Always copy generated files to repo folder BEFORE running git add. Never run git add on files that haven't been copied in.

---

## Project Structure

```
video-to-pdf-guide-creator/
├── app.py                    — Streamlit UI entry point
├── src/
│   ├── transcript_fetcher.py — Fetches YouTube transcript
│   ├── guide_generator.py    — Claude API calls (ALL LLM calls here only)
│   ├── pdf_creator.py        — PDF generation from guide text
│   └── email_sender.py       — Email delivery (future)
├── prompts/
│   └── guide_prompt.txt      — Claude prompt template (versioned separately)
├── tests/
│   ├── test_transcript.py
│   ├── test_guide.py
│   └── test_pdf.py
├── docs/
│   └── sample_guides/        — Example outputs for portfolio/demo
├── .env.example
├── requirements.txt
├── CLAUDE.md                 — This file
├── DECISIONS.md
├── MASTER_PLAN.md
├── SPEC.md
├── USER_STORIES.md
└── PROMPT_ARCHITECTURE.md
```

---

## Module Specs

### app.py — Streamlit UI Entry Point
**Purpose:** Main user interface. Renders the URL input, triggers the pipeline,
displays the guide, and handles email capture.

**Inputs:** YouTube URL (string from text input)
**Outputs:** Rendered guide in Streamlit UI

**UI Flow:**
1. Title and description
2. YouTube URL text input
3. "Generate Guide" button
4. Loading spinner while processing
5. Guide displayed in formatted text area
6. Download as PDF button
7. Email to self input + send button
8. Footer with attribution

**Error states (must all be handled):**
- Invalid URL format → "Please paste a valid YouTube URL"
- No transcript available → "This video doesn't have a transcript. Try another video."
- API error → "Something went wrong. Please try again in a moment."
- Empty transcript → "This video's transcript appears to be empty."

**Must NOT:**
- Show stack traces to users
- Block UI during processing (use st.spinner)
- Store user email without confirmation

---

### src/transcript_fetcher.py — YouTube Transcript Fetcher
**Purpose:** Accepts a YouTube URL, extracts the video ID, fetches the
transcript, and returns clean plain text.

**Inputs:** YouTube URL (string)
**Outputs:** Transcript text (string) OR raises TranscriptError

**Behavior:**
- Extract video ID from any YouTube URL format:
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - `https://www.youtube.com/shorts/VIDEO_ID`
- Fetch transcript using youtube-transcript-api
- Clean transcript: remove timestamps, merge lines, normalize whitespace
- Return plain text string

**Failure modes:**
- Invalid URL → raise `InvalidURLError` with message
- No transcript → raise `NoTranscriptError` with message
- Private/unavailable video → raise `VideoUnavailableError` with message
- Network error → raise `FetchError` with message

**Idempotent:** Yes — same URL always returns same transcript

---

### src/guide_generator.py — Claude API Guide Formatter
**Purpose:** Takes transcript text and returns a formatted step-by-step guide.
THIS IS THE ONLY FILE THAT MAKES CLAUDE API CALLS.

**Inputs:** Transcript text (string), optional title hint (string)
**Outputs:** Formatted guide (string in markdown)

**Guide format Claude must produce:**
```
## [Guide Title]

### What You'll Need
- [Materials/tools list]

### Time Required
[Estimated time]

### Steps
1. [Step title]
   [Step detail — 1-3 sentences]

2. [Step title]
   [Step detail — 1-3 sentences]

[Continue for all steps...]

### Tips & Warnings
- [Pro tip or safety warning]

### Summary
[One paragraph recap]
```

**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 2000
**Temperature:** 0 (deterministic output for consistency)

**Cost governance:**
- Haiku at ~$0.001 per guide generation
- Log token usage per request to `logs/usage.log`
- Alert if single request exceeds 1500 tokens input

**Must NOT:**
- Hardcode model name — use `MODEL` constant from config
- Make API calls anywhere else in the codebase
- Return raw API response — always return extracted text

---

### src/pdf_creator.py — PDF Generator
**Purpose:** Converts markdown guide text to a downloadable PDF.

**Inputs:** Guide text (string), optional title (string)
**Outputs:** PDF bytes (for Streamlit download button)

**PDF requirements:**
- Clean, printable formatting
- Title at top
- Numbered steps clearly formatted
- Materials list formatted as checklist
- Footer with source URL and generation date
- Letter size (8.5 x 11)

**Library:** ReportLab (preferred) or WeasyPrint
**Must NOT:** Write PDF to disk — return bytes only for Streamlit download

---

### prompts/guide_prompt.txt — Claude Prompt Template
**Purpose:** Versioned prompt template for guide generation.
Stored separately from code so it can be updated without code changes.

**Current prompt version:** 1.0
**Why versioned separately:** Prompt changes affect output quality.
Treating prompts as versioned artifacts (not inline strings) enables
A/B testing and rollback. See ADR-004.

---

## Session Startup Checklist

Before writing any code in a new session:
- [ ] Read this file completely
- [ ] Read DECISIONS.md for all active ADRs
- [ ] State the session goal as a single deliverable
- [ ] Confirm which module you're building against which spec
- [ ] Verify .env.example is current before touching credentials

---

## Testing Requirements

Every module must have a corresponding test file.
Tests must use mock objects — no real API calls in tests.
Tests must pass before any merge to master.

```bash
pytest tests/ -v
```

---

## Environment Variables Required

See `.env.example` for the full list.
Critical variables:
- `ANTHROPIC_API_KEY` — Claude API access
- `WEBSHARE_PROXY_URL` — Optional, for production transcript fetching
- `SMTP_EMAIL` — For email delivery feature
- `SMTP_PASSWORD` — For email delivery feature

---

*Version 1.0 — May 2026*
*Update this file whenever architecture changes or new modules are added*
*Never let CLAUDE.md fall behind the actual codebase*
