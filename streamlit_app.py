"""
video-to-pdf-guide-creator
A Streamlit app that turns YouTube videos into step-by-step PDF guides.

Deployment notes:
  • Set OPENAI_API_KEY or ANTHROPIC_API_KEY in Streamlit secrets for AI structuring.
  • Without an API key the app falls back to a chunked rule-based summary so it still works.
"""

import io
import re
import textwrap
from datetime import datetime

import streamlit as st

# Architectural-decision-compliant guide generator (ADR-003 isolation).
from src.guide_generator import (
    generate_guide,
    generate_guide_fallback,
    has_llm_configured,
    GuideGenerationError,
)

# ---- Optional deps (graceful fallbacks) -------------------------------------
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    HAS_YT = True
except ImportError:
    HAS_YT = False

try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem,
        HRFlowable, Table, TableStyle
    )
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


# =============================================================================
# PAGE CONFIG + CSS
# =============================================================================
st.set_page_config(
    page_title="video → pdf · guide creator",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700;12..96,800&family=Manrope:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: oklch(0.07 0.012 290);
  --bg-1: oklch(0.10 0.015 292);
  --bg-2: oklch(0.13 0.02 295);
  --line: oklch(0.22 0.02 295 / 0.5);
  --line-strong: oklch(0.35 0.03 295 / 0.7);
  --fg: oklch(0.97 0.005 290);
  --fg-dim: oklch(0.78 0.012 290);
  --muted: oklch(0.58 0.018 290);
  --accent: #b794ff;
  --accent-deep: oklch(0.45 0.22 295);
}

/* Whole-app dark background with atmospheric gradients */
html, body, [data-testid="stAppViewContainer"], .main, .block-container, [data-testid="stHeader"] {
  background: var(--bg) !important;
  color: var(--fg) !important;
  font-family: 'Manrope', sans-serif !important;
}
[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(ellipse 1100px 700px at 75% -10%, oklch(0.45 0.22 295 / 0.22), transparent 60%),
    radial-gradient(ellipse 900px 600px at 10% 110%, oklch(0.45 0.22 295 / 0.16), transparent 55%);
  pointer-events: none; z-index: 0;
}
[data-testid="stAppViewContainer"]::after {
  content: '';
  position: fixed; inset: 0;
  background-image: radial-gradient(circle at 1px 1px, oklch(1 0 0 / 0.025) 1px, transparent 0);
  background-size: 28px 28px;
  pointer-events: none; z-index: 0;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 40%, #000 30%, transparent 80%);
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

.block-container {
  max-width: 1100px !important;
  padding-top: 2rem !important;
  position: relative;
  z-index: 1;
}

/* Headings */
h1, h2, h3, h4 {
  font-family: 'Bricolage Grotesque', sans-serif !important;
  color: var(--fg) !important;
  letter-spacing: -0.025em !important;
}
p, label, span, div { color: var(--fg-dim); }

/* Custom HTML blocks */
.brand-row {
  display: flex; align-items: center; gap: 10px;
  padding-bottom: 28px;
}
.brand-mark {
  display: inline-flex; width: 28px; height: 28px;
  background: radial-gradient(circle at 30% 30%, #b8f0e8, #b794ff 55%, #5d2db8 100%);
  clip-path: polygon(50% 0%, 60% 35%, 100% 50%, 60% 65%, 50% 100%, 40% 65%, 0% 50%, 40% 35%);
}
.brand-text {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 15px;
  color: var(--fg);
}
.brand-faint { color: var(--muted); font-weight: 500; }

.eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--fg-dim);
  padding: 6px 12px 6px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: oklch(1 0 0 / 0.015);
  margin-bottom: 24px;
}
.eyebrow-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.5 } }

.display {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: clamp(48px, 8vw, 96px) !important;
  line-height: 0.95 !important;
  letter-spacing: -0.045em !important;
  margin: 0 0 18px 0 !important;
  color: var(--fg) !important;
  text-wrap: balance;
}
.accent-grad {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.hero-sub {
  font-size: 17px !important;
  color: var(--fg-dim) !important;
  line-height: 1.55 !important;
  max-width: 560px;
  margin: 0 0 32px 0 !important;
}

/* CSS-only blob cluster (re-creates the React version) */
.blob-cluster {
  position: relative;
  width: 100%; max-width: 420px;
  height: 240px;
  margin: 0 auto 8px;
  pointer-events: none;
}
.bb {
  position: absolute;
  border-radius: 50%;
  filter: blur(0.5px);
}
.bb.b1 {
  width: 38%; height: 60%; top: 18%; left: 12%;
  background: radial-gradient(ellipse 80% 80% at 30% 25%, oklch(0.95 0.06 195), oklch(0.75 0.12 200) 50%, oklch(0.4 0.18 295));
  box-shadow: 0 30px 60px -20px oklch(0.3 0.2 295 / 0.6);
  animation: floatA 8s ease-in-out infinite;
}
.bb.b2 {
  width: 32%; height: 52%; top: 28%; left: 38%;
  background: radial-gradient(ellipse 70% 70% at 35% 30%, oklch(0.9 0.08 195), oklch(0.7 0.14 220) 55%, oklch(0.5 0.22 300));
  box-shadow: 0 40px 80px -20px oklch(0.3 0.22 295 / 0.6);
  animation: floatB 10s ease-in-out infinite;
}
.bb.b3 {
  width: 30%; height: 48%; top: 38%; left: 25%;
  background: radial-gradient(ellipse 75% 75% at 40% 35%, oklch(0.88 0.08 320), oklch(0.65 0.2 305) 55%, oklch(0.35 0.22 290));
  box-shadow: 0 30px 70px -15px oklch(0.3 0.22 295 / 0.7);
  animation: floatC 9s ease-in-out infinite;
}
.bb.b4 {
  width: 18%; height: 30%; top: 12%; left: 5%;
  background: radial-gradient(ellipse 70% 70% at 35% 30%, oklch(0.92 0.06 195), oklch(0.7 0.14 250) 60%, oklch(0.45 0.22 295));
  animation: floatA 8s ease-in-out infinite;
}
@keyframes floatA { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-12px) } }
@keyframes floatB { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-8px) translateX(6px) } }
@keyframes floatC { 0%,100% { transform: translateY(0) } 50% { transform: translateY(10px) } }

.hero-trust {
  display: flex; gap: 12px; margin-top: 20px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.04em;
  color: var(--muted);
}
.hero-trust .sep { color: var(--line-strong); }

/* Streamlit input styling */
.stTextInput > div > div {
  background: oklch(0.13 0.018 295 / 0.7) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 999px !important;
  padding: 4px 6px 4px 22px !important;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.stTextInput > div > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 4px oklch(0.78 0.16 300 / 0.12) !important;
}
.stTextInput input {
  background: transparent !important;
  color: var(--fg) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 14.5px !important;
  padding: 14px 8px !important;
  border: none !important;
}
.stTextInput label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
  margin-bottom: 8px !important;
}

/* Primary button → accent gradient pill */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%) !important;
  color: #150e22 !important;
  font-weight: 600 !important;
  font-family: 'Manrope', sans-serif !important;
  border-radius: 999px !important;
  padding: 12px 28px !important;
  border: none !important;
  font-size: 14px !important;
  letter-spacing: -0.005em !important;
  box-shadow: 0 8px 24px -8px oklch(0.45 0.22 295) !important;
  transition: transform 0.18s, box-shadow 0.18s !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 12px 32px -10px oklch(0.45 0.22 295) !important;
}
.stButton > button[kind="primary"]:disabled {
  background: oklch(0.2 0.02 295) !important;
  color: var(--muted) !important;
  box-shadow: none !important;
}

/* Secondary buttons → ghost pills */
.stButton > button:not([kind="primary"]) {
  background: oklch(0.13 0.018 295 / 0.6) !important;
  color: var(--fg-dim) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
  padding: 10px 18px !important;
  font-family: 'Manrope', sans-serif !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  transition: all 0.18s !important;
}
.stButton > button:not([kind="primary"]):hover {
  background: oklch(0.18 0.02 295) !important;
  color: var(--fg) !important;
  border-color: var(--line-strong) !important;
}

/* Download button */
.stDownloadButton > button {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%) !important;
  color: #150e22 !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
  padding: 10px 22px !important;
  border: none !important;
  font-size: 13.5px !important;
  font-family: 'Manrope', sans-serif !important;
  box-shadow: 0 8px 24px -8px oklch(0.45 0.22 295) !important;
}

/* Alerts */
[data-testid="stAlert"] {
  background: oklch(0.13 0.02 295 / 0.7) !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 14px !important;
  color: var(--fg-dim) !important;
}

/* Spinner */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* Guide document container */
.guide-doc {
  background: oklch(0.99 0.005 290);
  color: oklch(0.18 0.012 290);
  border-radius: 22px;
  padding: 48px 56px;
  margin: 30px 0;
  box-shadow: 0 40px 80px -30px oklch(0 0 0 / 0.5), 0 0 0 1px var(--line);
  position: relative;
  overflow: hidden;
}
.guide-doc::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 6px;
  background: linear-gradient(90deg, var(--accent), var(--accent-deep), oklch(0.85 0.1 195));
}
.guide-doc h2, .guide-doc h3 { color: oklch(0.15 0.015 290) !important; }
.guide-doc p, .guide-doc li, .guide-doc span, .guide-doc div { color: oklch(0.25 0.012 290); }
.doc-meta {
  display: flex; justify-content: space-between; align-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px; letter-spacing: 0.05em; text-transform: uppercase;
  color: oklch(0.45 0.012 290);
  padding-bottom: 16px; margin-bottom: 22px;
  border-bottom: 1px solid oklch(0.9 0.005 290);
}
.doc-stamp {
  background: oklch(0.96 0.015 295);
  padding: 4px 10px; border-radius: 999px;
  color: oklch(0.45 0.12 295);
}
.doc-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 38px !important;
  line-height: 1.05;
  letter-spacing: -0.03em;
  margin: 0 0 14px !important;
  color: oklch(0.15 0.015 290) !important;
}
.doc-summary {
  font-size: 15px; line-height: 1.55;
  color: oklch(0.35 0.012 290);
  max-width: 640px;
  margin-bottom: 30px;
}
.step-block {
  display: grid;
  grid-template-columns: 56px 1fr;
  gap: 16px;
  padding: 20px 0;
  border-bottom: 1px solid oklch(0.92 0.005 290);
}
.step-block:last-of-type { border-bottom: none; }
.step-num {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 32px;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1;
}
.step-title-row {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin-bottom: 6px;
}
.step-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 19px;
  letter-spacing: -0.02em;
  color: oklch(0.15 0.015 290);
}
.step-text {
  font-size: 14px; line-height: 1.6;
  color: oklch(0.3 0.012 290);
}

/* How it works strip */
.how-strip {
  margin-top: 60px; padding-top: 30px;
  border-top: 1px solid var(--line);
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line);
  border-radius: 14px;
  overflow: hidden;
}
.how-cell { background: oklch(0.09 0.015 295); padding: 24px; }
.how-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 0.06em;
  color: var(--accent);
}
.how-t {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600; font-size: 20px;
  letter-spacing: -0.02em; color: var(--fg);
  margin: 10px 0 6px;
}
.how-b { font-size: 13.5px; color: var(--fg-dim); line-height: 1.5; }

/* Footer */
.footer-row {
  margin-top: 60px;
  padding: 24px 0;
  border-top: 1px solid var(--line);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted);
  display: flex; justify-content: space-between;
}

/* Hide Streamlit's "Press Enter to apply" caption */
.stTextInput div[data-baseweb] + div { display: none; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# =============================================================================
# CORE LOGIC
# =============================================================================
YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([\w-]{11})"
)

def extract_video_id(url: str) -> str | None:
    if not url:
        return None
    m = YT_ID_RE.search(url.strip())
    return m.group(1) if m else None


def fetch_transcript(video_id: str) -> str:
    """Returns the full transcript as one string, or raises a user-friendly error."""
    if not HAS_YT:
        raise RuntimeError(
            "youtube-transcript-api not installed. Add it to requirements.txt."
        )
    try:
        entries = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"]
        )
    except (TranscriptsDisabled, NoTranscriptFound):
        # Try any available language as a last resort
        try:
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            entries = None
            for t in transcripts:
                entries = t.fetch()
                break
            if entries is None:
                raise RuntimeError(
                    "This video doesn't have a transcript. Try a different video."
                )
        except Exception as e:
            raise RuntimeError(
                "This video doesn't have a transcript. Try a different video."
            ) from e
    text = " ".join(e["text"] for e in entries)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise RuntimeError("This video's transcript appears to be empty.")
    return text


def generate_guide_with_fallback(transcript: str) -> dict:
    """Try the LLM path; fall back to rule-based if no key or call fails."""
    if not has_llm_configured():
        return generate_guide_fallback(transcript)
    try:
        return generate_guide(transcript)
    except GuideGenerationError as e:
        st.warning(f"AI structuring failed, using fallback summary: {e}")
        return generate_guide_fallback(transcript)


# ----- PDF generation --------------------------------------------------------
def build_pdf(guide: dict, video_url: str) -> bytes:
    if not HAS_PDF:
        return b""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    accent = colors.HexColor("#7c4dff")

    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=24, leading=28,
        textColor=colors.HexColor("#1a1224"), spaceAfter=10,
    )
    meta_style = ParagraphStyle(
        "meta", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#666"),
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "body", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5, leading=15,
        textColor=colors.HexColor("#333"), spaceAfter=6,
    )
    step_num_style = ParagraphStyle(
        "stepnum", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=18,
        textColor=accent, leading=20,
    )
    step_title_style = ParagraphStyle(
        "steptitle", parent=styles["Heading3"],
        fontName="Helvetica-Bold", fontSize=13,
        textColor=colors.HexColor("#1a1224"),
        leading=16, spaceAfter=4,
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=9.5,
        textColor=colors.HexColor("#555"),
        spaceBefore=10, spaceAfter=6,
        letterSpacing=1,
    )

    story = []
    # Top accent bar
    story.append(HRFlowable(width="100%", thickness=4, color=accent, spaceAfter=14))
    story.append(Paragraph(
        f"GENERATED GUIDE &nbsp;&nbsp;·&nbsp;&nbsp; {datetime.now().strftime('%b %d, %Y')}",
        meta_style
    ))
    story.append(Paragraph(guide.get("title", "How-to Guide"), title_style))
    if guide.get("summary"):
        story.append(Paragraph(guide["summary"], body_style))
    if guide.get("time_required"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f'<font color="#7c4dff"><b>⏱ Time required:</b></font> {guide["time_required"]}',
            body_style,
        ))
    story.append(Spacer(1, 12))

    if guide.get("tools"):
        story.append(Paragraph("WHAT YOU'LL NEED", section_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(t, body_style), bulletColor=accent) for t in guide["tools"]],
            bulletType="bullet", leftIndent=14,
        ))
        story.append(Spacer(1, 10))

    story.append(Paragraph(f"STEPS &nbsp;·&nbsp; {len(guide.get('steps', []))} TOTAL", section_style))
    for i, step in enumerate(guide.get("steps", []), 1):
        tbl_data = [[
            Paragraph(f"{i:02d}", step_num_style),
            [
                Paragraph(step.get("title", f"Step {i}"), step_title_style),
                Paragraph(step.get("body", ""), body_style),
            ]
        ]]
        if step.get("time"):
            tbl_data[0][1].insert(1, Paragraph(
                f'<font color="#888" size="8">⏱ {step["time"]}</font>', body_style
            ))
        tbl = Table(tbl_data, colWidths=[0.5 * inch, 6 * inch])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(tbl)

    if guide.get("tips"):
        story.append(Spacer(1, 6))
        story.append(Paragraph("TIPS & NOTES", section_style))
        story.append(ListFlowable(
            [ListItem(Paragraph(t, body_style), bulletColor=accent) for t in guide["tips"]],
            bulletType="bullet", leftIndent=14,
        ))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#ddd")))
    story.append(Paragraph(
        f'Source: <a href="{video_url}" color="#7c4dff">{video_url}</a>',
        meta_style
    ))
    story.append(Paragraph(
        "Generated by video-to-pdf-guide-creator",
        ParagraphStyle("foot", parent=meta_style, fontSize=8, textColor=colors.HexColor("#999"))
    ))

    doc.build(story)
    return buf.getvalue()


def guide_to_text(guide: dict, video_url: str) -> str:
    lines = [
        guide.get("title", "How-to Guide"),
        "=" * 60,
        guide.get("summary", ""),
        "",
    ]
    if guide.get("tools"):
        lines += ["WHAT YOU'LL NEED:"] + [f"  • {t}" for t in guide["tools"]] + [""]
    lines.append("STEPS:")
    for i, s in enumerate(guide.get("steps", []), 1):
        t = f"  ({s['time']})" if s.get("time") else ""
        lines.append(f"\n{i:02d}. {s.get('title','')}{t}")
        lines.append(f"    {s.get('body','')}")
    if guide.get("tips"):
        lines += ["", "TIPS:"] + [f"  ✦ {t}" for t in guide["tips"]]
    lines += ["", f"Source: {video_url}", "Generated by video-to-pdf-guide-creator"]
    return "\n".join(lines)


# =============================================================================
# UI
# =============================================================================
if "guide" not in st.session_state:
    st.session_state.guide = None
if "video_url" not in st.session_state:
    st.session_state.video_url = ""

# Brand row
st.markdown(
    """
    <div class="brand-row">
      <span class="brand-mark"></span>
      <span class="brand-text">video <span class="brand-faint">→</span> pdf <span class="brand-faint">· guide creator</span></span>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- HERO ---
if st.session_state.guide is None:
    st.markdown(
        """
        <div style="text-align:center; display:flex; flex-direction:column; align-items:center; padding: 8px 0 12px;">
          <div class="blob-cluster">
            <div class="bb b1"></div>
            <div class="bb b2"></div>
            <div class="bb b3"></div>
            <div class="bb b4"></div>
          </div>
          <span class="eyebrow"><span class="eyebrow-dot"></span>YouTube → printable how-to guide</span>
          <h1 class="display">Turn any video<br/><span class="accent-grad">into a guide.</span></h1>
          <p class="hero-sub" style="text-align:center; margin-left:auto; margin-right:auto;">
            Paste a YouTube URL. We pull the transcript, distill the steps, and hand you a clean printable PDF in seconds.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Input + submit
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        url = st.text_input(
            "youtube link",
            value=st.session_state.video_url,
            placeholder="https://youtube.com/watch?v=...",
            label_visibility="collapsed",
            key="url_input",
        )
        st.session_state.video_url = url
        video_id = extract_video_id(url)
        c_a, c_b = st.columns([1, 1])
        with c_a:
            generate = st.button(
                "✦  Generate guide",
                type="primary",
                disabled=not bool(video_id),
                use_container_width=True,
            )
        with c_b:
            sample = st.button(
                "Try a sample video",
                use_container_width=True,
            )

    if sample:
        st.session_state.video_url = "https://youtu.be/dQw4w9WgXcQ"
        st.session_state._run_sample = True
        st.rerun()

    if generate or st.session_state.get("_run_sample"):
        running_sample = st.session_state.pop("_run_sample", False)
        with st.status("Reading the video…", expanded=True) as status:
            try:
                if running_sample:
                    st.write("📼 Using a built-in sample (sourdough how-to)")
                    guide = {
                        "title": "How to Make a Perfect Sourdough Loaf at Home",
                        "summary": "A complete walkthrough of mixing, bulk ferment, shaping, cold proof, and baking sourdough in a Dutch oven.",
                        "time_required": "24 hours (mostly hands-off)",
                        "tools": ["Active sourdough starter", "Dutch oven", "Bench scraper", "Banneton or bowl + tea towel", "Kitchen scale"],
                        "steps": [
                            {"title": "Feed your starter the night before", "body": "Mix 50g starter, 50g flour, 50g water. Cover loosely and leave at room temperature for 8-12 hours until doubled and bubbly.", "time": "12h ahead"},
                            {"title": "Mix the dough", "body": "Combine 500g bread flour with 350g water. Rest 30 min (autolyse). Add 100g active starter and 10g salt. Squeeze together until incorporated.", "time": "9:00 AM"},
                            {"title": "Bulk ferment with stretch & folds", "body": "Every 30 min for the first 2 hours, perform a set of 4 stretch-and-folds. Let rest until dough has risen ~50%.", "time": "4-6 hours"},
                            {"title": "Pre-shape and bench rest", "body": "Turn dough onto a lightly floured surface. Shape into a loose round using a bench scraper. Cover and rest 20 minutes.", "time": "20 min"},
                            {"title": "Final shape and cold proof", "body": "Shape tightly into a boule or batard. Place seam-side up in a floured banneton. Cover and refrigerate overnight.", "time": "8-16 hours"},
                            {"title": "Bake in a Dutch oven", "body": "Preheat Dutch oven at 500°F for 1 hour. Score the dough, transfer in, cover and bake 20 min. Remove lid, drop to 450°F, bake 20-25 min more.", "time": "45 min"},
                        ],
                        "tips": [
                            "If dough feels slack, add 25g less water next time.",
                            "Score with a sharp blade at a shallow angle for the best ear.",
                            "Cool fully (1+ hour) before slicing or the crumb will be gummy.",
                        ],
                    }
                    st.session_state.video_url = "https://youtu.be/sample-sourdough"
                else:
                    st.write("📼 Fetching video metadata…")
                    vid_id = extract_video_id(st.session_state.video_url)
                    st.write("📝 Downloading transcript…")
                    transcript = fetch_transcript(vid_id)
                    st.write(f"✓ Got transcript ({len(transcript):,} chars)")
                    st.write("🧠 Analyzing content & structuring guide…")
                    guide = generate_guide_with_fallback(transcript)
                    st.write("📄 Rendering preview…")

                st.session_state.guide = guide
                status.update(label="Done.", state="complete", expanded=False)
                st.rerun()
            except Exception as e:
                status.update(label=f"Something went wrong: {e}", state="error")
                st.error(
                    "Couldn't generate a guide for that video. "
                    "Make sure the video has captions (auto-generated or manual) and the link is correct."
                )

    # How it works strip
    st.markdown(
        """
        <div class="how-strip">
          <div class="how-cell">
            <div class="how-num">01</div>
            <div class="how-t">Paste a link</div>
            <div class="how-b">Any YouTube video with captions.</div>
          </div>
          <div class="how-cell">
            <div class="how-num">02</div>
            <div class="how-t">We read the transcript</div>
            <div class="how-b">And distill it into clear steps.</div>
          </div>
          <div class="how-cell">
            <div class="how-num">03</div>
            <div class="how-t">You get a PDF guide</div>
            <div class="how-b">Copy, save, or email it to yourself.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- RESULT ---
else:
    guide = st.session_state.guide
    video_url = st.session_state.video_url

    # Action bar — email-first per ADR-005 (primary CTA), download secondary
    cact1, _, cact_email, cact_pdf, cact_copy = st.columns([1.4, 0.4, 1.4, 1.2, 1.0])
    with cact1:
        if st.button("← New guide"):
            st.session_state.guide = None
            st.session_state.video_url = ""
            st.rerun()
    with cact_email:
        email_clicked = st.button(
            "✉  Email this guide to me",
            type="primary",
            use_container_width=True,
            key="email_btn_top",
        )
        if email_clicked:
            st.session_state._show_email = True
    with cact_pdf:
        if HAS_PDF:
            pdf_bytes = build_pdf(guide, video_url)
            st.download_button(
                "↓ Download PDF",
                pdf_bytes,
                file_name=f"{re.sub(r'[^a-zA-Z0-9 _-]', '', guide.get('title', 'guide'))[:50]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("Install `reportlab` for PDF export.")
    with cact_copy:
        plain = guide_to_text(guide, video_url)
        st.download_button(
            "📋 .txt",
            plain,
            file_name="guide.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # Email capture expander — opens when the primary CTA is clicked
    show_email = st.session_state.get("_show_email", False)
    with st.expander("✉ Email this guide to yourself", expanded=show_email):
        st.markdown(
            "<div style='font-family:Manrope,sans-serif;font-size:13.5px;color:var(--fg-dim);line-height:1.55;margin-bottom:12px;'>"
            "Enter your email and we'll open your mail client with the guide pre-filled. "
            "<span style='color:var(--muted);font-size:12px;'>I'll also send you occasional tips on using AI tools to get more out of online video content. Unsubscribe anytime.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        email_to = st.text_input(
            "Your email address",
            placeholder="you@email.com",
            label_visibility="collapsed",
            key="email_input",
        )
        if email_to:
            from urllib.parse import quote
            subject = quote(f"Your guide: {guide.get('title','How-to')}")
            body = quote(guide_to_text(guide, video_url))
            mail_link = f"mailto:{email_to}?subject={subject}&body={body}"
            st.markdown(
                f'<a href="{mail_link}" style="display:inline-block; padding:10px 22px; '
                'background:linear-gradient(135deg,#b794ff,#5d2db8); color:#150e22; '
                'border-radius:999px; text-decoration:none; font-weight:600; '
                'font-family:Manrope,sans-serif; font-size:13.5px;">Open mail client →</a>',
                unsafe_allow_html=True,
            )

    # Document — guide structure follows SPEC.md output format
    time_required = guide.get("time_required", "")
    time_required_html = (
        f'<div style="display:inline-flex;align-items:center;gap:6px;font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:0.05em;text-transform:uppercase;color:oklch(0.45 0.12 295);background:oklch(0.96 0.015 295);padding:6px 14px;border-radius:999px;margin-bottom:18px;">⏱ Time required: {time_required}</div>'
        if time_required else ""
    )

    steps_html = ""
    for i, s in enumerate(guide.get("steps", []), 1):
        time_html = f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:0.05em;text-transform:uppercase;color:oklch(0.5 0.012 290);background:oklch(0.95 0.005 290);padding:3px 8px;border-radius:999px;">{s["time"]}</span>' if s.get("time") else ""
        steps_html += f"""
        <div class="step-block">
          <div class="step-num">{i:02d}</div>
          <div>
            <div class="step-title-row">
              <div class="step-title">{s.get('title','')}</div>
              {time_html}
            </div>
            <div class="step-text">{s.get('body','')}</div>
          </div>
        </div>
        """

    tools_html = ""
    if guide.get("tools"):
        items = "".join(f"<li>{t}</li>" for t in guide["tools"])
        tools_html = f"""
        <div style="background:oklch(0.97 0.008 290); border:1px solid oklch(0.92 0.005 290); border-radius:14px; padding:18px 22px; margin: 20px 0 24px;">
          <div style="font-family:JetBrains Mono,monospace;font-size:10.5px;letter-spacing:0.05em;text-transform:uppercase;color:oklch(0.45 0.012 290);margin-bottom:10px;">What you'll need</div>
          <ul style="margin:0; padding-left: 18px; color: oklch(0.25 0.012 290);">{items}</ul>
        </div>
        """

    tips_html = ""
    if guide.get("tips"):
        items = "".join(f"<li>{t}</li>" for t in guide["tips"])
        tips_html = f"""
        <div style="background:oklch(0.96 0.012 295); border:1px solid oklch(0.88 0.02 295); border-radius:14px; padding:18px 22px; margin-top:20px;">
          <div style="font-family:JetBrains Mono,monospace;font-size:10.5px;letter-spacing:0.05em;text-transform:uppercase;color:oklch(0.45 0.012 290);margin-bottom:10px;">Tips &amp; notes</div>
          <ul style="margin:0; padding-left: 18px; color: oklch(0.25 0.012 290);">{items}</ul>
        </div>
        """

    n_steps = len(guide.get("steps", []))
    st.markdown(
        f"""
        <div class="guide-doc">
          <div class="doc-meta">
            <span>▶ {video_url[:60]}{'…' if len(video_url) > 60 else ''}</span>
            <span class="doc-stamp">✦ AI-distilled guide</span>
          </div>
          <h1 class="doc-title">{guide.get('title', 'How-to Guide')}</h1>
          <p class="doc-summary">{guide.get('summary', '')}</p>
          {time_required_html}
          {tools_html}
          <div style="font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:oklch(0.4 0.012 290);margin: 28px 0 4px;">
            {n_steps} STEPS
          </div>
          {steps_html}
          {tips_html}
          <div style="margin-top:28px;padding-top:16px;border-top:1px solid oklch(0.92 0.005 290);font-family:JetBrains Mono,monospace;font-size:10.5px;letter-spacing:0.05em;text-transform:uppercase;color:oklch(0.55 0.012 290);">
            ✦ Generated by video-to-pdf-guide-creator
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Footer
st.markdown(
    """
    <div class="footer-row">
      <div>© 2026 · video-to-pdf-guide-creator</div>
      <div>Streamlit hosted · MIT licensed</div>
    </div>
    """,
    unsafe_allow_html=True,
)
