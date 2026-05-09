"""
app.py
Video-to-PDF-Guide-Creator — Main Streamlit Application
Converts YouTube how-to videos into printable step-by-step guides.

Enterprise standards applied (Tier 1):
- Startup validation of required environment variables
- Structured logging initialised at app start
- Graceful degradation — each feature fails independently
- Session state — guide persists across button clicks (no page reload)
"""

import os
import re
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
    .main-title { font-size:2.2rem; font-weight:800; color:#1F3864; margin-bottom:0; }
    .subtitle { font-size:1.1rem; color:#595959; margin-top:0.2rem; margin-bottom:1.5rem; }
    .guide-box { background-color:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:1.5rem; margin-top:1rem; }
    .success-badge { background-color:#E2EFDA; color:#375623; padding:0.3rem 0.8rem; border-radius:4px; font-size:0.85rem; font-weight:600; }
    .footer-text { font-size:0.75rem; color:#A0AEC0; text-align:center; margin-top:2rem; }
    .copy-area textarea { font-family: monospace; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────
# Persists guide across button clicks so page does not reload to blank state
if 'guide_text' not in st.session_state:
    st.session_state.guide_text = None
if 'guide_url' not in st.session_state:
    st.session_state.guide_url = ''
if 'guide_title' not in st.session_state:
    st.session_state.guide_title = 'step-by-step-guide'
if 'show_copy' not in st.session_state:
    st.session_state.show_copy = False


# ── Helper — extract title from guide for PDF filename ────────────────────────
def _extract_title(guide_text: str, url: str = '') -> str:
    """
    Extract title from guide markdown for use as PDF filename.
    Priority:
    1. ## heading from guide text
    2. Video title from YouTube oEmbed API (no API key needed)
    3. Sanitized video ID from URL
    4. Default fallback
    """
    # Priority 1 — extract ## heading from guide
    match = re.search(r'^## (.+)$', guide_text, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        # Skip if it looks like an error or refusal
        skip_phrases = ['cannot', 'unable', 'no guide', 'not a', 'honest']
        if not any(phrase in title.lower() for phrase in skip_phrases):
            title = re.sub(r'[^\w\s-]', '', title)
            title = re.sub(r'\s+', '-', title.strip()).lower()
            return title[:60]

    # Priority 2 — fetch video title from YouTube oEmbed (free, no API key)
    if url:
        try:
            import urllib.request
            import json
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            with urllib.request.urlopen(oembed_url, timeout=5) as response:
                data = json.loads(response.read())
                title = data.get('title', '')
                if title:
                    title = re.sub(r'[^\w\s-]', '', title)
                    title = re.sub(r'\s+', '-', title.strip()).lower()
                    return title[:60]
        except Exception:
            pass  # fall through to next option

    # Priority 3 — extract video ID from URL as last resort
    if url:
        vid_match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', url)
        if vid_match:
            return f"youtube-{vid_match.group(1)}"

    # Priority 4 — default
    return 'step-by-step-guide'


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">📋 Video-to-PDF Guide Creator</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Paste any YouTube how-to video URL and get a '
    'printable step-by-step guide in seconds.</p>',
    unsafe_allow_html=True
)
st.divider()


# ── URL Input ──────────────────────────────────────────────────────────────────
url = st.text_input(
    'YouTube URL',
    placeholder='https://www.youtube.com/watch?v=...',
    help='Paste any YouTube video URL. The video must have captions enabled.',
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
        '<span style="color:#888;font-size:0.85rem;line-height:2.5rem;">'
        '⏱ Usually takes 10–30 seconds</span>',
        unsafe_allow_html=True
    )


# ── Pipeline — only runs when Generate is clicked ─────────────────────────────
if generate_btn and url.strip():
    # Clear previous guide
    st.session_state.guide_text = None
    st.session_state.show_copy = False

    # Step 1 — fetch transcript
    with st.status('Fetching video transcript...', expanded=False) as status:
        try:
            use_proxy = bool(os.environ.get('WEBSHARE_PROXY_URL'))
            transcript = fetch_transcript(url.strip(), use_proxy=use_proxy)
            status.update(
                label=f'✅ Transcript fetched ({len(transcript):,} characters)',
                state='complete'
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
    with st.status('Generating your guide with Claude AI...', expanded=False) as status:
        try:
            guide_text = generate_guide(transcript)
            # Store in session state so it survives button clicks
            st.session_state.guide_text = guide_text
            st.session_state.guide_url = url.strip()
            st.session_state.guide_title = _extract_title(guide_text, url.strip())
            status.update(label='✅ Guide generated', state='complete')
        except ValueError as e:
            status.update(label='❌ Empty transcript', state='error')
            st.error(str(e))
            st.stop()
        except RuntimeError as e:
            status.update(label='❌ Guide generation failed', state='error')
            st.error(f'**Generation failed:** {e}')
            st.stop()


# ── Display guide — reads from session state, persists across button clicks ───
if st.session_state.guide_text:
    guide_text = st.session_state.guide_text
    guide_url = st.session_state.guide_url
    pdf_filename = f"{st.session_state.guide_title}-step-by-step-guide.pdf"

    st.markdown('<span class="success-badge">✅ Guide Ready</span>', unsafe_allow_html=True)

    # ── Actions — shown ABOVE guide so user sees them without scrolling ────────
    st.markdown('### Save Your Guide')
    action_col1, action_col2, action_col3 = st.columns(3)

    # PDF download — uses download_button which does NOT reload the page
    with action_col1:
        try:
            pdf_bytes = create_pdf(guide_text, source_url=guide_url)
            st.download_button(
                label='📥 Download PDF',
                data=pdf_bytes,
                file_name=pdf_filename,
                mime='application/pdf',
                use_container_width=True,
            )
        except RuntimeError as e:
            logger.error("PDF creation failed: %s", e)
            st.warning(f'PDF unavailable: {e}')

    # Copy text — toggle st.code() which has native copy button built in
    with action_col2:
        if st.button('📋 Copy Text', use_container_width=True):
            st.session_state.show_copy = not st.session_state.show_copy

    # Clear / start over
    with action_col3:
        if st.button('🔄 New Guide', use_container_width=True):
            st.session_state.guide_text = None
            st.session_state.show_copy = False
            st.rerun()

    # ── Email capture — above guide so visible without scrolling ─────────────
    st.divider()
    st.markdown('### 📧 Email This Guide to Yourself')
    email_col1, email_col2 = st.columns([3, 1])
    with email_col1:
        email = st.text_input(
            'Email address',
            placeholder='you@example.com',
            label_visibility='collapsed',
            key='email_input',
        )
    with email_col2:
        if st.button('Send', use_container_width=True, disabled=not email.strip()):
            st.info('📬 Email delivery coming soon! Use PDF download above for now.')

    st.caption(
        "By entering your email you'll also receive occasional tips "
        "on using AI tools to get more from online video content. "
        "Unsubscribe anytime."
    )

    # Show copy text area when toggled — st.code has native copy button
    if st.session_state.show_copy:
        st.code(guide_text, language=None)

    # ── Guide text — shown below all actions ───────────────────────────────────
    st.divider()

    # Detect non-instructional content and display appropriate UI
    non_instructional_signals = [
        "cannot create a step-by-step guide",
        "no instructional",
        "no steps or procedures",
        "contains no instructional",
        "song lyrics",
        "i must be honest",
        "i cannot create",
    ]
    is_non_instructional = any(
        signal in guide_text.lower() for signal in non_instructional_signals
    )

    if is_non_instructional:
        st.warning(
            "⚠️ **This video doesn't contain how-to content.** "
            "Try a tutorial, recipe, DIY repair, or any video that walks "
            "through a process step by step. The guide below explains what was found."
        )

    st.markdown('<div class="guide-box">', unsafe_allow_html=True)
    st.markdown(guide_text)
    st.markdown('</div>', unsafe_allow_html=True)


# ── How it works ───────────────────────────────────────────────────────────────
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


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<p class="footer-text">Built by Randy Skiles · '
    '<a href="https://linkedin.com/in/randy-skiles" target="_blank">LinkedIn</a> · '
    '<a href="https://github.com/joatsaint/video-to-pdf-guide-creator" '
    'target="_blank">GitHub</a></p>',
    unsafe_allow_html=True
)
