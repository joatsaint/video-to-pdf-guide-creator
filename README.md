# video-to-pdf-guide-creator

Turn any YouTube how-to video into a clean, printable step-by-step guide.
Paste a URL → transcript is fetched → Claude structures it into steps → save as PDF, email to yourself, or copy as text.

**Live URL:** _set after first Streamlit deploy_

---

## Repo structure

```
.
├── streamlit_app.py            ← Streamlit entry point (UI + flow)
├── src/
│   ├── __init__.py
│   └── guide_generator.py      ← ADR-003: ALL LLM calls live here, nowhere else
├── prompts/
│   └── guide_prompt.txt        ← ADR-004: versioned prompt, loaded at runtime
├── requirements.txt
├── .streamlit/
│   └── config.toml             ← Dark theme to match the UI
├── index.html                  ← Design reference: standalone HTML prototype
├── app.jsx                     ← React source for the prototype
├── tweaks-panel.jsx            ← Tweaks panel for the prototype
├── SPEC.md
├── DECISIONS.md
├── CLAUDE.md
├── LICENSE
└── README.md
```

---

## Architecture (compliance with DECISIONS.md)

| ADR | Implementation |
|-----|---------------|
| **ADR-001** Streamlit MVP | `streamlit_app.py` is the deploy target. Pure-Python, no build step. |
| **ADR-002** Haiku model | `src/guide_generator.py` → `MODEL = "claude-haiku-4-5"`. Override via `GUIDE_MODEL` env var for A/B testing without code changes. |
| **ADR-003** Model-agnostic isolation | The `anthropic` SDK is imported in `src/guide_generator.py` ONLY. Switching to Bedrock, Gemini, or Ollama requires changing one file. |
| **ADR-004** Prompt as versioned file | `prompts/guide_prompt.txt` is loaded at call time. Edit and commit independently of code; git history is the change log. |
| **ADR-005** Email-first CTA | "Email this guide to me" is the primary (purple gradient) button on the result page. "Download PDF" is secondary. |

---

## Local dev

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # optional but recommended
streamlit run streamlit_app.py
```

Without an API key the app runs in **fallback mode** — heuristic sentence-chunking. Useful for local UI work; not production-quality.

## Deploy to streamlit.app

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. **Main file path:** `streamlit_app.py`
4. **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. **Deploy.** Subsequent pushes are picked up by hitting **Reboot** on the app page.

---

## UI / design system

Dark surface (`oklch(0.07 0.012 290)`) with a lavender accent (`#b794ff`) and CSS-only animated 3D-feeling blob shapes in the hero. Typography pairs **Bricolage Grotesque** (display, weight 700) with **Manrope** (body) and **JetBrains Mono** (URLs, eyebrows, metadata).

The HTML prototype in `index.html` is the design reference — open it locally to see the three hero layouts (Centered Spotlight / Split Console / Bottom Dock) toggleable via the Tweaks panel. Streamlit's widget styling is more constrained, so the deployed app uses the Centered Spotlight variant with CSS injection to mirror the visual language.

---

## Output format

Matches **SPEC.md** § Feature 2:

```json
{
  "title": "...",
  "summary": "...",
  "time_required": "...",
  "tools": ["..."],
  "steps": [{"title": "...", "body": "...", "time": "..."}],
  "tips": ["..."]
}
```

The PDF rendering (Letter size, ReportLab) follows the spec's clean numbered-step layout with the source URL + date in the footer.

---

## Roadmap

| Stage | Status | Items |
|-------|--------|-------|
| 1 — MVP | shipped | URL input · transcript fetch · Claude structure · PDF · email-via-mailto |
| 1.5 | next | Server-side email delivery (SMTP/SendGrid) · privacy policy page |
| 2 | planned | Per-IP rate limiting (SPEC.md req'd before wide promotion) · usage logging |
| 3 | planned | Guide history (anonymous local storage) |
| 4 | planned | Next.js rebuild + Postgres (per ADR-001) |

## License

MIT — see `LICENSE`.
