"""
Email Service for sending transactional emails (Password Reset, Notifications).
Uses standard Python smtplib with SSL/STARTTLS support.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
        use_ssl: bool | None = None,
        timeout: int | None = None,
    ) -> None:
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username or settings.smtp_user
        self.password = password or settings.smtp_password
        self.from_email = from_email or settings.smtp_from_email or self.username
        self.use_ssl = use_ssl if use_ssl is not None else settings.smtp_use_ssl
        self.timeout = timeout or settings.smtp_timeout_seconds

    def _create_smtp_connection(self) -> smtplib.SMTP:
        if self.use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=self.timeout)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            server.starttls(context=ssl.create_default_context())

        if self.username and self.password:
            server.login(self.username, self.password)
        return server

    def send_password_reset_email(
        self,
        *,
        to_email: str,
        username: str,
        reset_token: str,
    ) -> bool:
        """
        Sends password reset link to user. Link is valid for 15 minutes.
        """
        reset_link = f"{settings.app_base_url}/#reset-password?token={reset_token}"
        subject = f"[{settings.app_name}] Password Reset Request"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.app_name} <{self.from_email}>"
        msg["To"] = to_email

        # Plain-text version
        text_content = f"""Hello {username},

We received a request to reset your password for your {settings.app_name} account.

To reset your password, please open the following link:
{reset_link}

This link is valid for 15 minutes.
If you did not request this password reset, please ignore this email. Your account remains secure.

Best regards,
{settings.app_name} NOC Team
"""

        # HTML version
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #1e293b; border-radius: 16px; border: 1px solid #334155; padding: 32px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
    .brand {{ font-size: 18px; font-weight: 700; color: #38bdf8; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }}
    h2 {{ font-size: 20px; font-weight: 600; color: #ffffff; margin-top: 0; margin-bottom: 12px; }}
    p {{ font-size: 14px; line-height: 1.6; color: #cbd5e1; margin: 8px 0; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #0284c7, #2563eb); color: #ffffff !important; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; margin: 20px 0; }}
    .warning {{ font-size: 12px; color: #94a3b8; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #f59e0b; margin-top: 20px; }}
    .footer {{ font-size: 11px; color: #64748b; margin-top: 24px; text-align: center; }}
    .link-alt {{ font-size: 12px; color: #38bdf8; word-break: break-all; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">🛡️ {settings.app_name}</div>
    <h2>Account Password Reset</h2>
    <p>Hello <strong>{username}</strong>,</p>
    <p>We received a request to reset your password for your Network Backup account. Click the button below to set a new password:</p>
    <div style="text-align: center;">
      <a href="{reset_link}" class="btn" target="_blank">Reset Password</a>
    </div>
    <div class="warning">
      ⏱️ <strong>Notice:</strong> This recovery link is only valid for <strong>15 minutes</strong> from the time this email was sent.
    </div>
    <p style="margin-top: 20px; font-size: 12px; color: #94a3b8;">
      If the button above does not work, copy and paste the following link into your browser:<br>
      <a href="{reset_link}" class="link-alt">{reset_link}</a>
    </p>
    <div class="footer">
      If you did not request this reset, please ignore this email. Your password will not change.<br>
      © 2026 {settings.app_name} - NOC Infrastructure.
    </div>
  </div>
</body>
</html>
"""

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with self._create_smtp_connection() as server:
                server.send_message(msg)
            logger.info("Password reset email successfully sent to %s", to_email)
            return True
        except Exception as exc:
            logger.error("Failed to send password reset email to %s: %s", to_email, exc)
            raise


email_service = EmailService()
