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
- Privacy + accuracy trust badges (mandatory)
- Soft depth shadows, proper border radius, neutral gray base
- Bottom Line summary — progressive disclosure
- Copy button morphs to Copied! for 2 seconds
- Actions always above guide content
- Mobile-first — all buttons use_container_width=True
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


# ── Custom CSS — ai-frontend-best-practices standard ──────────────────────────
st.markdown("""
<style>
    /* ── Base ── */
    .block-container { max-width: 720px; padding-top: 2rem; }

    /* ── Typography ── */
    .main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #1F3864;
        margin-bottom: 0;
        line-height: 1.2;
    }
    .subtitle {
        font-size: 1rem;
        color: #6B7280;
        margin-top: 0.25rem;
        margin-bottom: 0;
        line-height: 1.5;
    }

    /* ── Guide card — soft depth shadow, not harsh border ── */
    .guide-box {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.06);
        margin-top: 0.5rem;
    }

    /* ── Bottom Line summary card ── */
    .bottom-line {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        color: #0C4A6E;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    /* ── Trust badges ── */
    .trust-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin: 0.5rem 0;
    }
    .trust-badge-privacy {
        background: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        border-radius: 6px;
        padding: 0.2rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .trust-badge-accuracy {
        background: #FFFBEB;
        color: #92400E;
        border: 1px solid #FDE68A;
        border-radius: 6px;
        padding: 0.2rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* ── Success badge ── */
    .success-badge {
        background: #DCFCE7;
        color: #166534;
        border: 1px solid #BBF7D0;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    /* ── Skeleton screen animation ── */
    .skeleton {
        background: linear-gradient(90deg, #E5E7EB 25%, #F3F4F6 50%, #E5E7EB 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 6px;
        margin: 6px 0;
    }
    @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* ── Footer ── */
    .footer-text {
        font-size: 0.75rem;
        color: #9CA3AF;
        text-align: center;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Session state — consolidated init ─────────────────────────────────────────
defaults = {
    'guide_text': None,
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
def _extract_title(guide_text: str, url: str = '') -> str:
    """Extract PDF filename from guide. 4-level fallback."""
    match = re.search(r'^## (.+)$', guide_text, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        skip_phrases = ['cannot', 'unable', 'no guide', 'not a', 'honest']
        if not any(phrase in title.lower() for phrase in skip_phrases):
            title = re.sub(r'[^\w\s-]', '', title)
            title = re.sub(r'\s+', '-', title.strip()).lower()
            return title[:60]
    if url:
        try:
            import urllib.request, json
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            with urllib.request.urlopen(oembed_url, timeout=5) as response:
                data = json.loads(response.read())
                title = data.get('title', '')
                if title:
                    title = re.sub(r'[^\w\s-]', '', title)
                    title = re.sub(r'\s+', '-', title.strip()).lower()
                    return title[:60]
        except Exception:
            pass
    if url:
        vid_match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', url)
        if vid_match:
            return f"youtube-{vid_match.group(1)}"
    return 'step-by-step-guide'


def _extract_bottom_line(guide_text: str) -> str:
    """Extract the Summary section as the Bottom Line one-liner."""
    match = re.search(r'### Summary\s*\n(.+?)(?:\n\n|\Z)', guide_text, re.DOTALL)
    if match:
        summary = match.group(1).strip()
        # Take first sentence only
        first_sentence = re.split(r'(?<=[.!?])\s', summary)[0]
        return first_sentence[:200]
    return ''


def _skeleton_html(widths=None):
    """Return animated skeleton screen HTML."""
    if widths is None:
        widths = ['55%', '90%', '75%', '85%', '70%']
    lines = ''.join(
        f'<div class="skeleton" style="height:14px;width:{w}"></div>'
        for w in widths
    )
    return f'<div style="padding:0.5rem 0">{lines}</div>'

def validate_config() -> None:
    """Validate required environment variables are present."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file or Streamlit secrets."
        )
# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">📋 Video-to-PDF Guide Creator</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Paste any YouTube how-to video URL — get a '
    'printable step-by-step guide in seconds.</p>',
    unsafe_allow_html=True
)

# Trust badges — mandatory per ai-frontend-best-practices skill
st.markdown("""
<div class="trust-row">
  <span class="trust-badge-privacy">🔒 We don't store your video history. Data stays in your session.</span>
  <span class="trust-badge-accuracy">⚠️ AI-generated. Verify critical steps with the original video.</span>
</div>
""", unsafe_allow_html=True)

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
        '<span style="color:#9CA3AF;font-size:0.85rem;line-height:2.5rem;">'
        '⏱ Usually 10–30 seconds</span>',
        unsafe_allow_html=True
    )


# ── Pipeline ───────────────────────────────────────────────────────────────────
if generate_btn and url.strip():
    st.session_state.guide_text = None
    st.session_state.show_copy = False
    st.session_state.copy_clicked = False

    # Step 1 — fetch transcript with skeleton screen
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

    # Step 2 — generate guide with skeleton screen
    with st.status('Generating your guide with Claude AI...', expanded=True) as status:
        st.markdown(_skeleton_html(['60%', '90%', '75%', '85%', '50%', '70%']), unsafe_allow_html=True)
        try:
            guide_text = generate_guide(transcript)
            st.session_state.guide_text = guide_text
            st.session_state.guide_url = url.strip()
            st.session_state.guide_title = _extract_title(guide_text, url.strip())
            st.session_state.guide_bottom_line = _extract_bottom_line(guide_text)
            status.update(label='✅ Guide ready', state='complete', expanded=False)
        except ValueError as e:
            status.update(label='❌ Empty transcript', state='error')
            st.error(str(e))
            st.stop()
        except RuntimeError as e:
            status.update(label='❌ Guide generation failed', state='error')
            st.error(f'**Generation failed:** {e}')
            st.stop()


# ── Results page ───────────────────────────────────────────────────────────────
if st.session_state.guide_text:
    guide_text = st.session_state.guide_text
    guide_url  = st.session_state.guide_url
    pdf_filename = f"{st.session_state.guide_title}-step-by-step-guide.pdf"

    # ── Success badge + Bottom Line (progressive disclosure) ──────────────────
    st.markdown('<span class="success-badge">✅ Guide Ready</span>', unsafe_allow_html=True)

    if st.session_state.guide_bottom_line:
        st.markdown(
            f'<div class="bottom-line">💡 {st.session_state.guide_bottom_line}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Actions — always above content ────────────────────────────────────────
    st.markdown('### Save Your Guide')
    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        try:
            pdf_bytes = create_pdf(guide_text, source_url=guide_url)
            st.download_button(
                label='📥 Download PDF',
                data=pdf_bytes,
                file_name=pdf_filename,
                mime='application/pdf',
                use_container_width=True,
                help='Download your guide as a formatted PDF file',
            )
        except RuntimeError as e:
            logger.error("PDF creation failed: %s", e)
            st.warning(f'PDF unavailable: {e}')

    # Copy button — morphs to Copied! for 2 seconds
    with action_col2:
        copy_label = '✅ Copied!' if st.session_state.copy_clicked else '📋 Copy Text'
        if st.button(copy_label, use_container_width=True, help='Copy guide text to clipboard'):
            st.session_state.show_copy = True
            st.session_state.copy_clicked = True
            st.session_state.copy_time = time.time()

    # Reset copy button after 2 seconds
    if st.session_state.copy_clicked:
        if time.time() - st.session_state.copy_time > 2:
            st.session_state.copy_clicked = False
            st.rerun()

    with action_col3:
        if st.button('🔄 New Guide', use_container_width=True, help='Start over with a new URL'):
            for key in defaults:
                st.session_state[key] = defaults[key]
            st.rerun()

    # Show copy area when toggled
    if st.session_state.show_copy:
        st.code(guide_text, language=None)

    # ── Email capture — above guide content ───────────────────────────────────
    st.divider()
    st.markdown('### 📧 Email This Guide to Yourself')
    email_col1, email_col2 = st.columns([3, 1])
    with email_col1:
        email = st.text_input(
            'Email address',
            placeholder='you@example.com',
            label_visibility='collapsed',
            key='email_input',
            help='Enter your email to receive the guide as a PDF attachment',
        )
    with email_col2:
        send_btn = st.button(
            'Send',
            use_container_width=True,
            disabled=not email.strip(),
            help='Email the guide PDF to yourself'
        )

    if send_btn and email.strip():
        try:
            with st.spinner('Sending your guide...'):
                pdf_bytes = create_pdf(guide_text, source_url=guide_url)
                send_guide_email(
                    to_email=email.strip(),
                    pdf_bytes=pdf_bytes,
                    pdf_filename=pdf_filename,
                    guide_title=st.session_state.guide_title.replace('-', ' ').title(),
                )
            st.success(
                f'✅ Guide sent to **{email.strip()}**! '
                'Check your inbox — it may take a minute to arrive.'
            )
            logger.info("Guide emailed successfully to=%s", email.strip())
        except ValueError as e:
            st.error(f'**Invalid email:** {e}')
        except RuntimeError as e:
            st.error(f'**Could not send email:** {e}')

    st.caption(
        "By entering your email you'll also receive occasional tips "
        "on using AI tools to get more from online video content. "
        "Unsubscribe anytime."
    )

    # ── Guide content — always last ────────────────────────────────────────────
    st.divider()

    # Non-instructional video warning
    non_instructional_signals = [
        "cannot create a step-by-step guide",
        "no instructional",
        "no steps or procedures",
        "contains no instructional",
        "song lyrics",
        "i must be honest",
        "i cannot create",
    ]
    if any(signal in guide_text.lower() for signal in non_instructional_signals):
        st.warning(
            "⚠️ **This video doesn't contain how-to content.** "
            "Try a tutorial, recipe, DIY repair, or any video that walks "
            "through a process step by step."
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
