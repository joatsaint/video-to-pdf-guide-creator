# Video-to-PDF-Guide-Creator

**Convert any YouTube how-to video into a printable step-by-step guide in seconds.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-FF4B4B.svg)](https://streamlit.io)
[![Claude API](https://img.shields.io/badge/powered%20by-Claude%20API-orange.svg)](https://anthropic.com)

---

## What It Does

Paste a YouTube URL. Get a formatted, printable step-by-step guide.

No more pausing and rewinding. No more trying to remember what the video said.
The tool extracts the transcript, passes it to Claude AI, and returns a clean
guide you can print, save as PDF, or email to yourself.

**Built for:**
- DIY homeowners following repair or improvement tutorials
- Home cooks following recipe videos
- Small businesses converting their tutorial library into printable guides
- Anyone who learns better from reading than watching

---

## Live Demo

🔗 **[Launch the app → video-to-pdf-guide-creator.streamlit.app](https://video-to-pdf-guide-creator.streamlit.app/)**

---

## Features

**MVP (Current)**
- Paste any YouTube URL with a transcript
- Receive a formatted step-by-step guide with materials list and tips
- Copy guide to clipboard
- Email guide to yourself (builds opt-in list)
- Download as PDF

**Coming Next**
- User-generated guide library (public, searchable)
- Small business bulk conversion (up to 50 videos)
- White-label guides with business branding
- API access for agencies

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| AI | Anthropic Claude API (claude-haiku) |
| Transcript Fetch | youtube-transcript-api + Webshare proxy |
| PDF Generation | ReportLab or WeasyPrint |
| Email | SMTP / Mailchimp API |
| Hosting | Streamlit Cloud (MVP) → Vercel (Next.js) |
| Future | Next.js + PostgreSQL |

---

## Local Development

**Prerequisites:**
- Python 3.10+
- Anthropic API key
- Webshare proxy credentials (optional for local testing)

**Setup:**
```bash
git clone https://github.com/joatsaint/video-to-pdf-guide-creator.git
cd video-to-pdf-guide-creator
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
streamlit run app.py
```

---

## Project Documentation

| File | Purpose |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Architecture rules and module specs |
| [DECISIONS.md](DECISIONS.md) | Architectural Decision Records |
| [MASTER_PLAN.md](MASTER_PLAN.md) | Staged roadmap from MVP to revenue |
| [SPEC.md](SPEC.md) | Product specification and user flows |
| [USER_STORIES.md](USER_STORIES.md) | BA-format user stories |
| [PROMPT_ARCHITECTURE.md](PROMPT_ARCHITECTURE.md) | How Claude API was used to build this |

---

## Architecture

The app follows a simple three-stage pipeline:

```
YouTube URL
    ↓
Transcript Fetcher (youtube-transcript-api)
    ↓
Claude API (guide formatter prompt)
    ↓
PDF Generator + Email Capture
    ↓
User Guide Library (future)
```

All Claude API calls are isolated in `src/guide_generator.py`.
Switching AI providers requires changing one file. (See DECISIONS.md ADR-003)

---

## Built By

**Randy Skiles** — AI Automation Specialist
25+ years enterprise IT | Claude API | AWS Bedrock | MCP

- LinkedIn: [linkedin.com/in/randy-skiles](https://linkedin.com/in/randy-skiles)
- GitHub: [github.com/joatsaint](https://github.com/joatsaint)
- Related project: [enterprise-ai-pipeline](https://github.com/joatsaint/enterprise-ai-pipeline)

---

*This project is part of a portfolio demonstrating AI-assisted product development.*
*Built with Claude API and enterprise-grade documentation practices.*
