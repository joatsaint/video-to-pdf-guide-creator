"""
app.py
Video-to-PDF-Guide-Creator — Main Streamlit Application
Converts YouTube how-to videos into printable step-by-step guides.

Enterprise standards applied (Tier 1):
- Startup validation of required environment variables
- Structured logging initialised at app start
- Graceful degradation — each feature fails independently
- Session state — guide persists across button clicks (no page reload)

UI standards applied (ai-frontend-best-practices skill):
- Skeleton screen loading states
- Privacy + accuracy trust badges (below action buttons)
- Soft depth shadows, proper border radius, neutral gray base
- Bottom Line summary — progressive disclosure
- Copy button morphs to Copied! for 2 seconds
- Actions always above guide content
- Mobile-first — all buttons use_container_width=True

Layout order (empty state):
  Title + Subtitle
  [spacer]
  URL Input
  Generate Button + timing note
  How it works expander
  [divider]
  Trust badges
  Footer

Layout order (guide ready):
  Success badge + Bottom Line
  Download / Copy / New Guide buttons
  Email section
  [divider]
  Trust badges
  Guide content
"""

import os
import re
import time
import logging
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────────────────────
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)

# ── Import pipeline modules ────────────────────────────────────────────────────
from src.transcript_fetcher import (
    fetch_transcript,
    InvalidURLError,
    NoTranscriptError,
    VideoUnavailableError,
    FetchError,
)
from src.guide_generator import generate_guide, validate_config
from src.pdf_creator import create_pdf
from src.email_sender import send_guide_email


# ── Startup validation ─────────────────────────────────────────────────────────
@st.cache_resource
def _startup_check():
    try:
        validate_config()
        logger.info("App startup validation passed")
        return True
    except EnvironmentError as exc:
        logger.critical("Startup validation failed: %s", exc)
        return str(exc)

startup_result = _startup_check()
if startup_result is not True:
    st.error(f"⚠️ **Configuration error:** {startup_result}")
    st.info("Add your `ANTHROPIC_API_KEY` to the `.env` file and restart the app.")
    st.stop()


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Video-to-PDF Guide Creator',
    page_icon='📋',
    layout='centered',
    initial_sidebar_state='collapsed',
)


# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Base layout ── */
    .block-container {
        max-width: 700px;
        padding-top: 3rem;
        padding-bottom: 3rem;
    }

    /* ── Header ── */
    .app-header {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #F9FAFB;
        margin-bottom: 0.4rem;
        line-height: 1.2;
        letter-spacing: -0.5px;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #9CA3AF;
        margin-top: 0;
        line-height: 1.6;
    }

    /* ── Input area ── */
    .input-section {
        margin-bottom: 0.5rem;
    }

    /* ── Timing hint ── */
    .timing-hint {
        color: #6B7280;
        font-size: 0.85rem;
        line-height: 2.6rem;
        padding-left: 0.5rem;
    }

    /* ── Guide card ── */
    .guide-box {
        background: #1E2330;
        border: 1px solid #2D3748;
        border-radius: 12px;
        padding: 1.75rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin-top: 0.5rem;
    }
    .guide-box h2 {
        color: #F9FAFB;
        font-size: 1.4rem;
        margin-top: 0;
    }
    .guide-box h3 {
        color: #E5E7EB;
        font-size: 1.05rem;
        margin-top: 1.25rem;
        border-bottom: 1px solid #2D3748;
        padding-bottom: 0.3rem;
    }
    .guide-box p, .guide-box li {
        color: #D1D5DB;
        font-size: 0.95rem;
        line-height: 1.7;
    }

    /* ── Step cards ── */
    .step-card {
        background: #252B3B;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 0.6rem 0;
    }
    .step-number {
        display: inline-block;
        background: #3B82F6;
        color: white;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 4px;
        padding: 0.1rem 0.45rem;
        margin-right: 0.5rem;
        vertical-align: middle;
    }
    .step-title {
        font-weight: 600;
        color: #F3F4F6;
        font-size: 0.97rem;
        vertical-align: middle;
    }
    .step-body {
        color: #9CA3AF;
        font-size: 0.9rem;
        margin-top: 0.4rem;
        line-height: 1.6;
    }
    .step-time {
        color: #6B7280;
        font-size: 0.78rem;
        margin-top: 0.3rem;
    }

    /* ── Bottom Line summary card ── */
    .bottom-line {
        background: #1E3A5F;
        border: 1px solid #2563EB;
        border-radius: 8px;
        padding: 0.85rem 1.1rem;
        font-size: 0.97rem;
        color: #BFDBFE;
        font-weight: 500;
        margin-bottom: 1.25rem;
    }

    /* ── Trust badges — subtle, below actions ── */
    .trust-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin: 1.25rem 0 0.5rem 0;
    }
    .trust-badge-privacy {
        background: transparent;
        color: #6B7280;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 0.2rem 0.65rem;
        font-size: 0.75rem;
    }
    .trust-badge-accuracy {
        background: transparent;
        color: #6B7280;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 0.2rem 0.65rem;
        font-size: 0.75rem;
    }

    /* ── Success badge ── */
    .success-badge {
        display: inline-block;
        background: #052E16;
        color: #86EFAC;
        border: 1px solid #166534;
        padding: 0.25rem 0.85rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    /* ── Section label ── */
    .section-label {
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6B7280;
        margin-bottom: 0.5rem;
        margin-top: 1.5rem;
    }

    /* ── Skeleton screen animation ── */
    .skeleton {
        background: linear-gradient(90deg, #1F2937 25%, #374151 50%, #1F2937 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 6px;
        margin: 8px 0;
    }
    @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* ── Tip chips ── */
    .tip-chip {
        display: inline-block;
        background: #1C2A1E;
        border: 1px solid #166534;
        color: #86EFAC;
        border-radius: 20px;
        padding: 0.25rem 0.75rem;
        font-size: 0.82rem;
        margin: 0.2rem 0.2rem 0.2rem 0;
    }

    /* ── Footer ── */
    .footer-text {
        font-size: 0.75rem;
        color: #4B5563;
        text-align: center;
        margin-top: 2.5rem;
    }
    .footer-text a { color: #6B7280; }
    .footer-text a:hover { color: #9CA3AF; }

    /* ── Divider spacing ── */
    hr { margin: 1.75rem 0 !important; border-color: #1F2937 !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state — consolidated init ─────────────────────────────────────────
defaults = {
    'guide_dict': None,
    'guide_url': '',
    'guide_title': 'step-by-step-guide',
    'guide_bottom_line': '',
    'show_copy': False,
    'copy_clicked': False,
    'copy_time': 0.0,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Helpers ────────────────────────────────────────────────────────────────────
def _slug(text: str, max_len: int = 60) -> str:
    """Convert title text to a URL/filename-safe slug."""
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'\s+', '-', text.strip()).lower()
    return text[:max_len]


def _title_from_url(url: str) -> str:
    """Fallback filename from YouTube video ID."""
    vid_match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', url)
    if vid_match:
        return f"youtube-{vid_match.group(1)}"
    return 'step-by-step-guide'


def _guide_to_markdown(guide: dict) -> str:
    """Convert guide dict to markdown string for copy/PDF."""
    lines = [f"## {guide.get('title', 'How-to Guide')}"]
    if guide.get('summary'):
        lines += ['', guide['summary']]
    if guide.get('time_required'):
        lines += ['', f"⏱ **Time required:** {guide['time_required']}"]
    if guide.get('tools'):
        lines += ['', '**You will need:**']
        for t in guide['tools']:
            lines.append(f"- {t}")
    if guide.get('steps'):
        lines += ['', '---', '']
        for i, step in enumerate(guide['steps'], 1):
            lines.append(f"### Step {i}: {step.get('title', '')}")
            if step.get('time'):
                lines.append(f"*{step['time']}*")
            if step.get('body'):
                lines.append(step['body'])
            lines.append('')
    if guide.get('tips'):
        lines += ['---', '**Tips:**']
        for t in guide['tips']:
            lines.append(f"- {t}")
    return '\n'.join(lines)


def _skeleton_html(widths=None):
    if widths is None:
        widths = ['55%', '90%', '75%', '85%', '70%']
    lines = ''.join(
        f'<div class="skeleton" style="height:13px;width:{w}"></div>'
        for w in widths
    )
    return f'<div style="padding:0.5rem 0">{lines}</div>'


def _render_guide(guide: dict):
    """Render the structured guide dict as styled HTML cards."""
    st.markdown(f'<div class="guide-box">', unsafe_allow_html=True)

    # Title
    st.markdown(f"## {guide.get('title', 'How-to Guide')}")

    # Meta row
    meta_parts = []
    if guide.get('time_required'):
        meta_parts.append(f"⏱ {guide['time_required']}")
    if guide.get('tools'):
        meta_parts.append(f"🔧 {len(guide['tools'])} items needed")
    if guide.get('steps'):
        meta_parts.append(f"📋 {len(guide['steps'])} steps")
    if meta_parts:
        st.caption(' · '.join(meta_parts))

    # Tools
    if guide.get('tools'):
        st.markdown('<p class="section-label">You will need</p>', unsafe_allow_html=True)
        tools_html = ''.join(f'<span class="tip-chip">🔧 {t}</span>' for t in guide['tools'])
        st.markdown(tools_html, unsafe_allow_html=True)

    # Steps
    if guide.get('steps'):
        st.markdown('<p class="section-label">Steps</p>', unsafe_allow_html=True)
        for i, step in enumerate(guide['steps'], 1):
            time_html = f'<div class="step-time">⏱ {step["time"]}</div>' if step.get('time') else ''
            st.markdown(f"""
            <div class="step-card">
                <span class="step-number">{i}</span>
                <span class="step-title">{step.get('title', '')}</span>
                <div class="step-body">{step.get('body', '')}</div>
                {time_html}
            </div>
            """, unsafe_allow_html=True)

    # Tips
    if guide.get('tips'):
        st.markdown('<p class="section-label">Tips</p>', unsafe_allow_html=True)
        tips_html = ''.join(f'<span class="tip-chip">💡 {t}</span>' for t in guide['tips'])
        st.markdown(tips_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── Page config must come before any st calls — already set above ──────────────

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <p class="main-title">📋 Video-to-PDF Guide Creator</p>
    <p class="subtitle">Paste any YouTube how-to video URL — get a printable<br>step-by-step guide in seconds.</p>
</div>
""", unsafe_allow_html=True)


# ── URL Input ──────────────────────────────────────────────────────────────────
url = st.text_input(
    'YouTube URL',
    placeholder='https://www.youtube.com/watch?v=...',
    help='Paste any YouTube video URL with captions enabled.',
    label_visibility='collapsed',
)

col1, col2 = st.columns([2, 5])
with col1:
    generate_btn = st.button(
        '✨ Generate Guide',
        type='primary',
        use_container_width=True,
        disabled=not url.strip(),
    )
with col2:
    st.markdown(
        '<span class="timing-hint">⏱ Usually 10–30 seconds</span>',
        unsafe_allow_html=True
    )

st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

# ── How it works — directly below input ───────────────────────────────────────
with st.expander('ℹ️ How it works'):
    st.markdown("""
1. **Paste** any YouTube URL with captions enabled
2. **We fetch** the video transcript automatically
3. **Claude AI** formats it into a clean step-by-step guide
4. **Download** as PDF, copy the text, or email it to yourself

**Works best with:** How-to videos, tutorials, cooking videos, DIY repairs,
fitness instruction, and any video that walks through a process step by step.

**Requires:** The video must have closed captions (CC) enabled.
Most tutorial videos do — look for the CC button on the video player.
    """)


# ── Pipeline ───────────────────────────────────────────────────────────────────
if generate_btn and url.strip():
    st.session_state.guide_dict = None
    st.session_state.show_copy = False
    st.session_state.copy_clicked = False

    # Step 1 — fetch transcript
    with st.status('Fetching video transcript...', expanded=True) as status:
        st.markdown(_skeleton_html(['40%', '80%', '65%']), unsafe_allow_html=True)
        try:
            use_proxy = bool(
                os.environ.get('WEBSHARE_PROXY_URL') or
                os.environ.get('WEBSHARE_PROXY_USERNAME')
            )
            transcript = fetch_transcript(url.strip(), use_proxy=use_proxy)
            status.update(
                label=f'✅ Transcript fetched ({len(transcript):,} characters)',
                state='complete',
                expanded=False
            )
        except InvalidURLError as e:
            status.update(label='❌ Invalid URL', state='error')
            st.error(f'**Invalid URL:** {e}')
            st.stop()
        except NoTranscriptError as e:
            status.update(label='❌ No transcript available', state='error')
            st.error(f'**No transcript found:** {e}')
            st.stop()
        except VideoUnavailableError as e:
            status.update(label='❌ Video unavailable', state='error')
            st.error(f'**Video unavailable:** {e}')
            st.stop()
        except FetchError as e:
            status.update(label='❌ Fetch failed', state='error')
            st.error(f'**Could not fetch transcript:** {e}')
            st.stop()

    # Step 2 — generate guide
    with st.status('Generating your guide with Claude AI...', expanded=True) as status:
        st.markdown(_skeleton_html(['60%', '90%', '75%', '85%', '50%', '70%']), unsafe_allow_html=True)
        try:
            guide_dict = generate_guide(transcript)
            st.session_state.guide_dict = guide_dict
            st.session_state.guide_url = url.strip()
            title_slug = _slug(guide_dict.get('title', '')) or _title_from_url(url.strip())
            st.session_state.guide_title = title_slug
            st.session_state.guide_bottom_line = guide_dict.get('summary', '')[:200]
            status.update(label='✅ Guide ready', state='complete', expanded=False)
        except ValueError as e:
            status.update(label='❌ Empty transcript', state='error')
            st.error(str(e))
            st.stop()
        except RuntimeError as e:
            status.update(label='❌ Guide generation failed', state='error')
            st.error(f'**Generation failed:** {e}')
            st.stop()
        except Exception as e:
            status.update(label='❌ Unexpected error', state='error')
            st.error(f'**Unexpected error:** {e}')
            st.stop()


# ── Results ────────────────────────────────────────────────────────────────────
if st.session_state.guide_dict:
    guide_dict   = st.session_state.guide_dict
    guide_url    = st.session_state.guide_url
    guide_md     = _guide_to_markdown(guide_dict)
    pdf_filename = f"{st.session_state.guide_title}-guide.pdf"

    # Success + Bottom Line
    st.markdown('<span class="success-badge">✅ Guide Ready</span>', unsafe_allow_html=True)
    if st.session_state.guide_bottom_line:
        st.markdown(
            f'<div class="bottom-line">💡 {st.session_state.guide_bottom_line}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Actions — always above content ────────────────────────────────────────
    st.markdown('<p class="section-label">Save your guide</p>', unsafe_allow_html=True)
    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        try:
            pdf_bytes = create_pdf(guide_md, source_url=guide_url)
            st.download_button(
                label='📥 Download PDF',
                data=pdf_bytes,
                file_name=pdf_filename,
                mime='application/pdf',
                use_container_width=True,
                help='Download your guide as a formatted PDF',
            )
        except RuntimeError as e:
            logger.error("PDF creation failed: %s", e)
            st.warning(f'PDF unavailable: {e}')

    with action_col2:
        copy_label = '✅ Copied!' if st.session_state.copy_clicked else '📋 Copy Text'
        if st.button(copy_label, use_container_width=True, help='Copy guide text to clipboard'):
            st.session_state.show_copy = True
            st.session_state.copy_clicked = True
            st.session_state.copy_time = time.time()

    with action_col3:
        if st.button('🔄 New Guide', use_container_width=True, help='Start over with a new URL'):
            for key in defaults:
                st.session_state[key] = defaults[key]
            st.rerun()

    if st.session_state.copy_clicked:
        if time.time() - st.session_state.copy_time > 2:
            st.session_state.copy_clicked = False
            st.rerun()

    if st.session_state.show_copy:
        st.code(guide_md, language=None)

    # ── Email capture ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-label">Email this guide to yourself</p>', unsafe_allow_html=True)
    email_col1, email_col2 = st.columns([3, 1])
    with email_col1:
        email = st.text_input(
            'Email address',
            placeholder='you@example.com',
            label_visibility='collapsed',
            key='email_input',
        )
    with email_col2:
        send_btn = st.button(
            'Send',
            use_container_width=True,
            disabled=not email.strip(),
        )

    if send_btn and email.strip():
        try:
            with st.spinner('Sending your guide...'):
                pdf_bytes = create_pdf(guide_md, source_url=guide_url)
                send_guide_email(
                    to_email=email.strip(),
                    pdf_bytes=pdf_bytes,
                    pdf_filename=pdf_filename,
                    guide_title=guide_dict.get('title', 'Your Guide'),
                )
            st.success(f'✅ Guide sent to **{email.strip()}**! Check your inbox.')
            logger.info("Guide emailed to=%s", email.strip())
        except ValueError as e:
            st.error(f'**Invalid email:** {e}')
        except RuntimeError as e:
            st.error(f'**Could not send email:** {e}')

    st.caption(
        "By entering your email you'll also receive occasional tips on using AI tools "
        "to get more from online video content. Unsubscribe anytime."
    )

    # ── Trust badges — below actions, subtle ──────────────────────────────────
    st.markdown("""
    <div class="trust-row">
      <span class="trust-badge-privacy">🔒 We don't store your video history</span>
      <span class="trust-badge-accuracy">⚠️ AI-generated — verify critical steps</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Guide content — always last ────────────────────────────────────────────
    _render_guide(guide_dict)


# ── Trust badges on empty state — subtle, below the fold ──────────────────────
if not st.session_state.guide_dict:
    st.divider()
    st.markdown("""
    <div class="trust-row">
      <span class="trust-badge-privacy">🔒 We don't store your video history</span>
      <span class="trust-badge-accuracy">⚠️ AI-generated — verify critical steps</span>
    </div>
    """, unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<p class="footer-text">Built by Randy Skiles · '
    '<a href="https://linkedin.com/in/randy-skiles" target="_blank">LinkedIn</a> · '
    '<a href="https://github.com/joatsaint/video-to-pdf-guide-creator" '
    'target="_blank">GitHub</a></p>',
    unsafe_allow_html=True
)
