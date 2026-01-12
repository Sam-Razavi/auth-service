import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger(__name__)


async def _send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.SMTP_HOST:
        log.info("email_skipped", to=to, subject=subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER or None
    password = settings.SMTP_PASSWORD or None
    raw = msg.as_string()
    sender = settings.FROM_EMAIL

    def _send_sync() -> None:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.sendmail(sender, to, raw)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send_sync)


async def send_password_reset_email(email: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.APP_URL}/reset-password?token={token}"
    body = (
        "You requested a password reset.\n\n"
        f"Use this link to set a new password (valid for 1 hour):\n{link}\n\n"
        "If you did not request this, you can safely ignore this email."
    )
    await _send_email(email, "Reset your password", body)


async def send_verification_email(email: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.APP_URL}/auth/verify-email/{token}"
    body = (
        "Please verify your email address.\n\n"
        f"Click the link below (valid for 24 hours):\n{link}\n\n"
        "If you did not create an account, you can safely ignore this email."
    )
    await _send_email(email, "Verify your email address", body)
