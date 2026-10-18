from __future__ import annotations

import logging
from typing import Any
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FeishuClient:
    """
    Feishu Custom Bot Webhook client for automated failure alerts.
    Dispatches interactive card messages with automatic text-fallback
    to ensure alerts are reliably delivered without crashing callers.
    """

    def __init__(self, webhook_url: str | None = None, timeout: float = 10.0) -> None:
        self.webhook_url = webhook_url if webhook_url is not None else settings.feishu_webhook_url
        self.timeout = timeout

    def send_backup_failure_alert(
        self,
        *,
        device_name: str,
        vendor: str,
        model: str,
        ip_address: str,
        driver_key: str,
        job_id: str,
        occurred_at: datetime | None,
        final_state: str,
        failure_stage: str,
        failure_reason: str,
        attempt_count: int,
        max_attempts: int,
        last_successful_backup: datetime | str | None,
    ) -> dict[str, Any]:
        """
        Sends a structured network backup failure alert to Feishu.
        Returns a dict containing {"success": bool, "status_code": int, "response": dict, "error": str | None}.
        """
        if not self.webhook_url:
            logger.warning("FEISHU_WEBHOOK_URL is not configured; skipping Feishu alert.")
            return {
                "success": False,
                "status_code": 0,
                "response": {},
                "error": "FEISHU_WEBHOOK_URL is empty",
            }

        # Convert timestamp to local timezone (Asia/Jakarta / WIB)
        tz_name = settings.app_timezone or "Asia/Jakarta"
        try:
            target_tz = ZoneInfo(tz_name)
        except Exception:
            target_tz = timezone.utc

        event_time = occurred_at or datetime.now(timezone.utc)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        local_time_str = event_time.astimezone(target_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

        if isinstance(last_successful_backup, datetime):
            if last_successful_backup.tzinfo is None:
                last_successful_backup = last_successful_backup.replace(tzinfo=timezone.utc)
            last_success_str = last_successful_backup.astimezone(target_tz).strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
        elif last_successful_backup:
            last_success_str = str(last_successful_backup)
        else:
            last_success_str = "None (No snapshot recorded)"

        # Prepare rich interactive card
        card_payload = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                },
                "header": {
                    "template": "red",
                    "title": {
                        "tag": "plain_text",
                        "content": "🚨 [ALERT] Network Backup Failed",
                    },
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Device:**\n{device_name}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**IP Address:**\n{ip_address}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Vendor / Model:**\n{vendor} / {model}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Driver:**\n{driver_key}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Final State:**\n`{final_state}`",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Failure Stage:**\n`{failure_stage}`",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Attempts:**\n{attempt_count} / {max_attempts}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**Last Successful:**\n{last_success_str}",
                                },
                            },
                        ],
                    },
                    {
                        "tag": "hr",
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Failure Reason:**\n{failure_reason}",
                        },
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"Job ID: {job_id} | Time: {local_time_str}",
                            }
                        ],
                    },
                ],
            },
        }

        # Fallback text payload
        plain_text_content = (
            f"🚨 [ALERT] Network Backup Failed\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Device: {device_name}\n"
            f"Vendor: {vendor}\n"
            f"Model: {model}\n"
            f"IP: {ip_address}\n"
            f"Driver: {driver_key}\n"
            f"Job ID: {job_id}\n"
            f"Time: {local_time_str}\n"
            f"Final State: {final_state}\n"
            f"Failure Stage: {failure_stage}\n"
            f"Failure Reason: {failure_reason}\n"
            f"Attempt Count: {attempt_count}/{max_attempts}\n"
            f"Last Successful Backup: {last_success_str}\n"
        )
        text_payload = {
            "msg_type": "text",
            "content": {
                "text": plain_text_content,
            },
        }

        return self._post_payload(card_payload, text_payload, identifier=f"job-{job_id}")


    def _post_payload(
        self,
        card_payload: dict[str, Any],
        text_payload: dict[str, Any],
        identifier: str,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.webhook_url, json=card_payload)
                if resp.is_success:
                    body = resp.json()
                    if body.get("code") == 0:
                        logger.info("Feishu card alert delivered successfully for %s", identifier)
                        return {
                            "success": True,
                            "status_code": resp.status_code,
                            "response": body,
                            "error": None,
                        }
                    else:
                        logger.warning(
                            "Feishu card rejected with code %s (%s). Attempting plain text fallback...",
                            body.get("code"),
                            body.get("msg"),
                        )
                else:
                    logger.warning(
                        "Feishu card HTTP %s: %s. Attempting plain text fallback...",
                        resp.status_code,
                        resp.text,
                    )

                # Fallback to plain text
                resp_fallback = client.post(self.webhook_url, json=text_payload)
                if resp_fallback.is_success and resp_fallback.json().get("code") == 0:
                    logger.info("Feishu plain text alert delivered successfully for %s", identifier)
                    return {
                        "success": True,
                        "status_code": resp_fallback.status_code,
                        "response": resp_fallback.json(),
                        "error": None,
                    }
                else:
                    err_msg = f"Feishu plain text also failed: HTTP {resp_fallback.status_code}: {resp_fallback.text}"
                    logger.error(err_msg)
                    return {
                        "success": False,
                        "status_code": resp_fallback.status_code,
                        "response": resp_fallback.json() if resp_fallback.text.startswith("{") else {},
                        "error": err_msg,
                    }

        except Exception as exc:
            err_msg = f"Exception communicating with Feishu webhook: {exc}"
            logger.error(err_msg)
            return {
                "success": False,
                "status_code": 0,
                "response": {},
                "error": err_msg,
            }
