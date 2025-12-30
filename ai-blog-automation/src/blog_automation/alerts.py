"""Alert system for the AI Blog Automation Platform.

Handles sending alerts for critical errors, warnings, and notifications
to various channels (email, Slack, logging).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests

from blog_automation.errors import Severity
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class AlertConfig:
    """Alert configuration from environment variables."""

    def __init__(self):
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.alert_email = os.getenv("ALERT_EMAIL")
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "alerts@blog-automation.local")

    @property
    def slack_enabled(self) -> bool:
        return bool(self.slack_webhook_url)

    @property
    def email_enabled(self) -> bool:
        return bool(self.alert_email and self.smtp_host)


_config: AlertConfig | None = None


def get_alert_config() -> AlertConfig:
    """Get or create alert configuration."""
    global _config
    if _config is None:
        _config = AlertConfig()
    return _config


def send_alert(
    error_code: str,
    message: str,
    severity: str | Severity,
    context: dict[str, Any] | None = None,
) -> bool:
    """Send an alert through configured channels.

    Args:
        error_code: Unique error code
        message: Alert message
        severity: Alert severity level
        context: Additional context

    Returns:
        True if alert was sent successfully
    """
    severity_str = severity.value if isinstance(severity, Severity) else severity
    context = context or {}

    # Always log the alert
    log_data = {
        "error_code": error_code,
        "severity": severity_str,
        "context": context,
    }

    if severity_str == Severity.CRITICAL.value:
        logger.critical(message, **log_data)
    elif severity_str == Severity.ERROR.value:
        logger.error(message, **log_data)
    else:
        logger.warning(message, **log_data)

    config = get_alert_config()
    success = True

    # Send to Slack for critical/error
    if config.slack_enabled and severity_str in [
        Severity.CRITICAL.value,
        Severity.ERROR.value,
    ]:
        try:
            _send_slack_alert(error_code, message, severity_str, context)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            success = False

    # Send email for critical only
    if config.email_enabled and severity_str == Severity.CRITICAL.value:
        try:
            _send_email_alert(error_code, message, severity_str, context)
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            success = False

    return success


def _send_slack_alert(
    error_code: str,
    message: str,
    severity: str,
    context: dict[str, Any],
) -> None:
    """Send alert to Slack webhook."""
    config = get_alert_config()
    if not config.slack_webhook_url:
        return

    color = {
        Severity.CRITICAL.value: "#FF0000",
        Severity.ERROR.value: "#FFA500",
        Severity.WARNING.value: "#FFFF00",
    }.get(severity, "#808080")

    emoji = {
        Severity.CRITICAL.value: "🚨",
        Severity.ERROR.value: "❌",
        Severity.WARNING.value: "⚠️",
    }.get(severity, "ℹ️")

    payload = {
        "attachments": [
            {
                "color": color,
                "title": f"{emoji} [{error_code}] {severity.upper()}",
                "text": message,
                "fields": [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in context.items()
                ],
                "footer": "AI Blog Automation",
            }
        ]
    }

    response = requests.post(
        config.slack_webhook_url,
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    logger.debug("Slack alert sent successfully")


def _send_email_alert(
    error_code: str,
    message: str,
    severity: str,
    context: dict[str, Any],
) -> None:
    """Send alert via email."""
    config = get_alert_config()
    if not config.email_enabled:
        return

    subject = f"[{severity.upper()}] AI Blog Automation Alert: {error_code}"

    context_str = "\n".join(f"  {k}: {v}" for k, v in context.items())
    body = f"""
AI Blog Automation Alert

Error Code: {error_code}
Severity: {severity.upper()}
Message: {message}

Context:
{context_str}

---
This is an automated alert from the AI Blog Automation Platform.
"""

    msg = MIMEMultipart()
    msg["From"] = config.from_email
    msg["To"] = config.alert_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
        server.starttls()
        if config.smtp_username and config.smtp_password:
            server.login(config.smtp_username, config.smtp_password)
        server.send_message(msg)

    logger.debug("Email alert sent successfully")


def send_notification(
    title: str,
    message: str,
    channel: str = "slack",
) -> bool:
    """Send a general notification (non-error).

    Args:
        title: Notification title
        message: Notification message
        channel: Channel to send to (slack, email)

    Returns:
        True if notification was sent
    """
    config = get_alert_config()

    if channel == "slack" and config.slack_enabled:
        try:
            payload = {
                "attachments": [
                    {
                        "color": "#36a64f",
                        "title": title,
                        "text": message,
                        "footer": "AI Blog Automation",
                    }
                ]
            }
            response = requests.post(
                config.slack_webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    logger.info(f"Notification: {title} - {message}")
    return True
