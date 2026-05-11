"""
email_sender.py
Sends the generated guide PDF to the user via Gmail SMTP.
All email delivery logic is isolated in this module.

Enterprise standards applied (Tier 1):
- Input validation before sending
- Structured logging with timing
- Graceful error handling — specific messages per failure type
- Credentials from environment variables only — never hardcoded
"""

import os
import io
import time
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ── Logging ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAX_EMAIL_LENGTH = 254  # RFC 5321 maximum
MAX_PDF_SIZE_MB = 5


# ── Input validation ───────────────────────────────────────────────────────────
def _validate_email(email: str) -> str:
    """
    Validate and sanitize email address.

    Args:
        email: Raw email string from user input

    Returns:
        Cleaned email string

    Raises:
        ValueError: Email fails validation
    """
    email = email.strip().lower()

    if not email:
        raise ValueError("Email address cannot be empty.")

    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError("Email address is too long.")

    if '@' not in email or '.' not in email.split('@')[-1]:
        raise ValueError(
            "That doesn't look like a valid email address. "
            "Please check and try again."
        )

    return email


# ── Main public function ───────────────────────────────────────────────────────
def send_guide_email(
    to_email: str,
    pdf_bytes: bytes,
    pdf_filename: str,
    guide_title: str = 'Your Step-by-Step Guide',
) -> None:
    """
    Send the guide PDF to the user via Gmail SMTP.

    Args:
        to_email:    Recipient email address
        pdf_bytes:   PDF file as bytes from pdf_creator
        pdf_filename: Filename for the attachment
        guide_title: Title shown in email subject and body

    Raises:
        ValueError:  Invalid email address or missing credentials
        RuntimeError: SMTP delivery failed
    """
    start = time.perf_counter()

    # Validate inputs
    to_email = _validate_email(to_email)

    if not pdf_bytes:
        raise ValueError("PDF content is empty — cannot send email.")

    pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
    if pdf_size_mb > MAX_PDF_SIZE_MB:
        raise ValueError(
            f"PDF is too large to email ({pdf_size_mb:.1f}MB). "
            "Please use the download button instead."
        )

    # Load credentials from environment
    smtp_email = os.environ.get('SMTP_EMAIL', '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD', '').strip()

    if not smtp_email or not smtp_password:
        raise ValueError(
            "Email credentials not configured. "
            "Add SMTP_EMAIL and SMTP_PASSWORD to your .env file."
        )

    logger.info(
        "Sending guide email to=%s filename=%s size=%.1fKB",
        to_email, pdf_filename, len(pdf_bytes) / 1024
    )

    # Build email message
    msg = MIMEMultipart()
    msg['From'] = f'Video-to-PDF Guide Creator <{smtp_email}>'
    msg['To'] = to_email
    msg['Subject'] = f'Your Guide: {guide_title}'

    # Email body
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">

        <div style="background: #1F3864; padding: 24px; border-radius: 8px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem;">📋 Your Guide Is Ready</h1>
        </div>

        <div style="padding: 24px 0;">
            <p style="color: #374151; font-size: 1rem; line-height: 1.6;">
                Here is your step-by-step guide: <strong>{guide_title}</strong>
            </p>
            <p style="color: #374151; font-size: 1rem; line-height: 1.6;">
                The guide is attached as a PDF. You can print it, save it,
                or share it — no internet connection required.
            </p>
        </div>

        <div style="background: #FEF3C7; border: 1px solid #FDE68A; border-radius: 6px; padding: 12px 16px; margin: 16px 0;">
            <p style="color: #92400E; font-size: 0.85rem; margin: 0;">
                ⚠️ <strong>AI-generated content.</strong>
                Always verify critical steps with the original video.
            </p>
        </div>

        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 12px 16px; margin: 16px 0;">
            <p style="color: #166534; font-size: 0.85rem; margin: 0;">
                🔒 We do not store your video history or email address beyond this delivery.
            </p>
        </div>

        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;">

        <p style="color: #9CA3AF; font-size: 0.75rem; text-align: center;">
            Sent by Video-to-PDF Guide Creator ·
            <a href="https://video-to-pdf-guide-creator.streamlit.app" style="color: #2563EB;">
                video-to-pdf-guide-creator.streamlit.app
            </a>
            <br>
            You received this because you requested a guide.
            You will not receive further emails unless you request another guide.
        </p>

    </body>
    </html>
    """

    msg.attach(MIMEText(body_html, 'html'))

    # Attach PDF
    attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
    attachment.add_header(
        'Content-Disposition',
        'attachment',
        filename=pdf_filename
    )
    msg.attach(attachment)

    # Send via Gmail SMTP
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())

        elapsed = time.perf_counter() - start
        logger.info(
            "Email sent successfully to=%s elapsed=%.2fs",
            to_email, elapsed
        )

    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail authentication failed — check SMTP_EMAIL and SMTP_PASSWORD")
        raise RuntimeError(
            "Email authentication failed. "
            "Check that your Gmail App Password is correct in the settings."
        )
    except smtplib.SMTPRecipientsRefused:
        logger.error("Recipient refused: %s", to_email)
        raise RuntimeError(
            f"Could not deliver to {to_email}. "
            "Please check the email address and try again."
        )
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
        raise RuntimeError(
            "Email delivery failed. Please try again or use the PDF download."
        )
    except Exception as exc:
        logger.error("Unexpected email error: %s", exc, exc_info=True)
        raise RuntimeError(
            "Something went wrong sending your email. "
            "Please use the PDF download instead."
        )
