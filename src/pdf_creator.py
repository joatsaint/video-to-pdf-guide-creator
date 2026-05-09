"""
pdf_creator.py
Converts markdown guide text to PDF bytes.
Returns bytes only — never writes to disk.

Enterprise standards applied (Tier 1):
- Structured logging with timing
- Input validation and length limits
- Graceful error messages — no stack traces to caller
"""

import io
import re
import time
import logging
from datetime import date
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── Logging ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_GUIDE_CHARS = 50000   # ~12 pages — sanity limit
MAX_URL_LENGTH = 200


# ── Input validation ───────────────────────────────────────────────────────────
def _validate_inputs(guide_text: str, source_url: str) -> tuple[str, str]:
    """
    Validate and sanitize inputs before PDF generation.

    Args:
        guide_text: Markdown guide text from guide_generator
        source_url: Original YouTube URL for footer

    Returns:
        Tuple of (sanitized guide_text, sanitized source_url)

    Raises:
        ValueError: guide_text is empty or invalid
    """
    if not guide_text or not guide_text.strip():
        raise ValueError("Guide text is empty — cannot create PDF.")

    # Truncate if absurdly long (safety limit)
    if len(guide_text) > MAX_GUIDE_CHARS:
        logger.warning(
            "Guide text truncated from %d to %d chars for PDF",
            len(guide_text), MAX_GUIDE_CHARS
        )
        guide_text = guide_text[:MAX_GUIDE_CHARS]

    # Sanitize URL for footer — strip to safe length
    source_url = source_url.strip()[:MAX_URL_LENGTH] if source_url else ''

    return guide_text, source_url


# ── Styles ─────────────────────────────────────────────────────────────────────
def _build_styles() -> dict:
    """Build and return ReportLab paragraph styles."""
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'GuideTitle',
            parent=base['Heading1'],
            fontSize=20,
            spaceAfter=6,
            textColor=colors.HexColor('#1F3864'),
            fontName='Helvetica-Bold',
        ),
        'h2': ParagraphStyle(
            'GuideH2',
            parent=base['Heading2'],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=4,
            textColor=colors.HexColor('#2E75B6'),
            fontName='Helvetica-Bold',
        ),
        'body': ParagraphStyle(
            'GuideBody',
            parent=base['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=6,
            fontName='Helvetica',
        ),
        'step': ParagraphStyle(
            'GuideStep',
            parent=base['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=4,
            leftIndent=20,
            fontName='Helvetica',
        ),
        'bullet': ParagraphStyle(
            'GuideBullet',
            parent=base['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=3,
            leftIndent=20,
            bulletIndent=8,
            fontName='Helvetica',
        ),
        'footer': ParagraphStyle(
            'GuideFooter',
            parent=base['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName='Helvetica',
        ),
    }


# ── Markdown parser ────────────────────────────────────────────────────────────
def _parse_guide(text: str, styles: dict) -> list:
    """
    Convert markdown guide text to ReportLab flowables.

    Args:
        text:   Markdown formatted guide text
        styles: Dict of ParagraphStyle objects

    Returns:
        List of ReportLab flowable objects
    """
    flowables = []
    lines = text.split('\n')

    for line in lines:
        line = line.rstrip()

        if not line:
            flowables.append(Spacer(1, 6))
            continue

        if line.startswith('## '):
            content = line[3:].strip()
            flowables.append(Paragraph(content, styles['title']))
            flowables.append(HRFlowable(
                width='100%', thickness=2,
                color=colors.HexColor('#2E75B6'), spaceAfter=8
            ))

        elif line.startswith('### '):
            content = line[4:].strip()
            flowables.append(Paragraph(content, styles['h2']))

        elif re.match(r'^\d+\.\s', line):
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            flowables.append(Paragraph(content, styles['step']))

        elif line.startswith('- '):
            content = line[2:].strip()
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            flowables.append(Paragraph(f'• {content}', styles['bullet']))

        elif line.startswith('   ') and flowables:
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line.strip())
            flowables.append(Paragraph(content, styles['step']))

        else:
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            flowables.append(Paragraph(content, styles['body']))

    return flowables


# ── Main public function ───────────────────────────────────────────────────────
def create_pdf(guide_text: str, source_url: str = '') -> bytes:
    """
    Convert markdown guide text to PDF bytes.

    Args:
        guide_text: Formatted guide markdown from guide_generator
        source_url: Original YouTube URL for footer attribution

    Returns:
        PDF as bytes — pass directly to Streamlit download_button

    Raises:
        ValueError:  guide_text is empty or invalid
        RuntimeError: PDF generation failed
    """
    start = time.perf_counter()

    # Validate and sanitize inputs
    guide_text, source_url = _validate_inputs(guide_text, source_url)

    logger.info(
        "Creating PDF guide_chars=%d source_url=%s",
        len(guide_text), source_url[:50] if source_url else 'none'
    )

    buffer = io.BytesIO()
    styles = _build_styles()

    try:
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        story = _parse_guide(guide_text, styles)

        # Footer
        story.append(Spacer(1, 20))
        story.append(HRFlowable(
            width='100%', thickness=0.5, color=colors.lightgrey
        ))
        story.append(Spacer(1, 6))

        footer_parts = [f'Generated {date.today().strftime("%B %d, %Y")}']
        if source_url:
            footer_parts.append(f'Source: {source_url}')
        footer_parts.append('video-to-pdf-guide-creator')

        story.append(Paragraph(' | '.join(footer_parts), styles['footer']))

        doc.build(story)
        pdf_bytes = buffer.getvalue()

        elapsed = time.perf_counter() - start
        logger.info(
            "PDF created size=%d bytes elapsed=%.2fs",
            len(pdf_bytes), elapsed
        )

        return pdf_bytes

    except Exception as exc:
        logger.error("PDF creation failed: %s", exc, exc_info=True)
        raise RuntimeError(
            "PDF generation failed. Your guide is still available above — "
            "please copy the text manually."
        )
