"""Alerting utilities for anomaly and governance notifications."""

from __future__ import annotations

import json
import logging
import os
import smtplib
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from typing import Optional

try:  # pragma: no cover - optional dependency
    import httpx
except Exception:  # pragma: no cover - fallback when httpx unavailable
    httpx = None  # type: ignore

from ..agents.event_bus import AgentEvent

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AlertResult:
    """Represents the outcome of dispatching an alert."""

    delivered: bool
    channel: str
    detail: str


class SlackWebhookNotifier:
    """Send alerts to Slack via webhook with graceful fallback."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url or os.getenv("AFOC_SLACK_WEBHOOK")

    def notify(self, message: str) -> AlertResult:
        if not self.webhook_url or httpx is None:
            LOGGER.info("Slack webhook unavailable, logging alert: %s", message)
            return AlertResult(False, "slack", "webhook unavailable")
        payload = {"text": message}
        with httpx.Client(timeout=10) as client:
            response = client.post(self.webhook_url, json=payload)
            if response.status_code >= 400:
                LOGGER.warning("Slack webhook returned %s", response.status_code)
                return AlertResult(False, "slack", f"status {response.status_code}")
        return AlertResult(True, "slack", "delivered")


class EmailNotifier:
    """Send alerts via SMTP with environment-configured credentials."""

    def __init__(self, smtp_host: Optional[str] = None, smtp_port: int = 587) -> None:
        self.smtp_host = smtp_host or os.getenv("AFOC_SMTP_HOST")
        self.smtp_port = smtp_port
        self.username = os.getenv("AFOC_SMTP_USER")
        self.password = os.getenv("AFOC_SMTP_PASSWORD")
        self.recipients = os.getenv("AFOC_ALERT_RECIPIENTS", "").split(",")

    def notify(self, subject: str, body: str) -> AlertResult:
        if not (self.smtp_host and self.username and self.password and any(self.recipients)):
            LOGGER.info("SMTP credentials missing, skipping email alert")
            return AlertResult(False, "email", "credentials unavailable")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.username
        message["To"] = ",".join(r.strip() for r in self.recipients if r.strip())
        message.set_content(body)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.send_message(message)
        except Exception as exc:  # pragma: no cover - network guard
            LOGGER.warning("Failed to send email alert: %s", exc)
            return AlertResult(False, "email", str(exc))
        return AlertResult(True, "email", "delivered")


class AlertDispatcher:
    """Dispatches alerts when critical agent events occur."""

    def __init__(
        self,
        slack_notifier: SlackWebhookNotifier | None = None,
        email_notifier: EmailNotifier | None = None,
    ) -> None:
        self.slack = slack_notifier or SlackWebhookNotifier()
        self.email = email_notifier or EmailNotifier()

    async def handle_event(self, event: AgentEvent) -> None:
        if event.type == "forecast.completed":
            await self._handle_forecast(event)
        elif event.type == "security.alert":
            await self._handle_security(event)

    async def _handle_forecast(self, event: AgentEvent) -> None:
        anomalies = event.payload.get("anomalies", [])
        diagnostics = event.payload.get("diagnostics", {})
        divergence = diagnostics.get("ensemble_divergence", 0.0)
        if len(anomalies) >= 3 or divergence > 0.25:
            message = (
                "Forecast anomalies detected: " f"indices={anomalies}, divergence={divergence:.2f}"
            )
            self._dispatch(message)

    async def _handle_security(self, event: AgentEvent) -> None:
        message = event.payload.get("message", "Security alert")
        severity = event.payload.get("severity", "info")
        formatted = f"Security alert ({severity}): {message}"
        self._dispatch(formatted)

    def _dispatch(self, message: str) -> None:
        results: list[AlertResult] = [
            self.slack.notify(message),
            self.email.notify("AFOC Alert", message),
        ]
        LOGGER.info(
            "Alert dispatched",
            extra={"results": [asdict(result) for result in results], "message": message},
        )

    def emit_json_summary(self) -> str:
        summary = {
            "slack_configured": bool(self.slack.webhook_url),
            "email_configured": bool(self.email.smtp_host and self.email.recipients),
        }
        return json.dumps(summary)
