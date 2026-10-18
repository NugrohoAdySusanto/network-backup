from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.integrations.feishu_client import FeishuClient
from app.models.backup_job import BackupJob
from app.models.device import Device
from app.models.integration_status import IntegrationStatus
from app.models.snapshot import Snapshot
from app.services.notification_service import NotificationService


def test_feishu_client_card_success() -> None:
    client = FeishuClient(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/mock-hook")
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"code": 0, "msg": "success"}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = client.send_backup_failure_alert(
            device_name="MKK-HQ_Router",
            vendor="MikroTik",
            model="CCR1016-12G",
            ip_address="10.11.0.2",
            driver_key="mikrotik-routeros",
            job_id="b9999999-0000-0000-0000-000000000001",
            occurred_at=datetime(2026, 10, 6, 1, 0, 0, tzinfo=timezone.utc),
            final_state="FAILED",
            failure_stage="CONNECTING",
            failure_reason="SSH authentication failed (password incorrect).",
            attempt_count=1,
            max_attempts=3,
            last_successful_backup=None,
        )

        assert res["success"] is True
        assert res["status_code"] == 200
        assert mock_post.call_count == 1
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["msg_type"] == "interactive"
        assert payload["card"]["header"]["template"] == "red"
        elements = payload["card"]["elements"]
        fields = elements[0]["fields"]
        field_contents = [f["text"]["content"] for f in fields]
        assert any("MKK-HQ_Router" in c for c in field_contents)
        assert any("10.11.0.2" in c for c in field_contents)
        assert any("mikrotik-routeros" in c for c in field_contents)
        assert any("CONNECTING" in c for c in field_contents)


def test_feishu_client_card_failure_fallback_text() -> None:
    client = FeishuClient(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/mock-hook")

    # First call (card) fails with rejection code 19001, second call (text) succeeds
    resp_card = MagicMock()
    resp_card.is_success = True
    resp_card.status_code = 200
    resp_card.json.return_value = {"code": 19001, "msg": "card format rejected"}

    resp_text = MagicMock()
    resp_text.is_success = True
    resp_text.status_code = 200
    resp_text.json.return_value = {"code": 0, "msg": "success"}

    with patch("httpx.Client.post", side_effect=[resp_card, resp_text]) as mock_post:
        res = client.send_backup_failure_alert(
            device_name="MKK-HQ_Router",
            vendor="MikroTik",
            model="CCR1016-12G",
            ip_address="10.11.0.2",
            driver_key="mikrotik-routeros",
            job_id="b9999999-0000-0000-0000-000000000001",
            occurred_at=datetime.now(timezone.utc),
            final_state="FAILED",
            failure_stage="CONNECTING",
            failure_reason="Authentication failed",
            attempt_count=1,
            max_attempts=3,
            last_successful_backup=None,
        )

        assert res["success"] is True
        assert mock_post.call_count == 2
        fallback_call_kwargs = mock_post.call_args_list[1][1]
        assert fallback_call_kwargs["json"]["msg_type"] == "text"


def test_feishu_client_empty_webhook() -> None:
    client = FeishuClient(webhook_url="")
    res = client.send_backup_failure_alert(
        device_name="Test",
        vendor="Test",
        model="Test",
        ip_address="1.1.1.1",
        driver_key="test",
        job_id="test",
        occurred_at=None,
        final_state="FAILED",
        failure_stage="QUEUED",
        failure_reason="Test error",
        attempt_count=1,
        max_attempts=3,
        last_successful_backup=None,
    )
    assert res["success"] is False
    assert "empty" in res["error"]


def test_notification_service_orchestration() -> None:
    mock_db = MagicMock()

    device = Device(
        id=24,
        hostname="MKK-HQ_Router",
        ip_address="10.11.0.2",
        vendor="MikroTik",
        model="CCR1016-12G",
        host_group="Network",
        zabbix_host_id="10500",
        availability_status="up",
        source_present=True,
    )

    job_id = uuid.uuid4()
    job = BackupJob(
        id=job_id,
        device_id=24,
        driver_key="mikrotik-routeros",
        trigger_type="manual",
        state="FAILED",
        failure_stage="CONNECTING",
        failure_code="AUTHENTICATION_FAILED",
        failure_message="SSH authentication failed for MKK-HQ_Router",
        attempt_count=1,
        max_attempts=3,
        finished_at=datetime.now(timezone.utc),
    )

    # Mock scalar returns for job, device, last_snapshot, integration_status
    mock_db.scalar.side_effect = [
        job,       # BackupJob lookup
        device,    # Device lookup
        None,      # last Snapshot lookup
        None,      # existing IntegrationStatus lookup
    ]

    mock_client = MagicMock(spec=FeishuClient)
    mock_client.send_backup_failure_alert.return_value = {
        "success": True,
        "status_code": 200,
        "response": {"code": 0, "msg": "success"},
        "error": None,
    }

    service = NotificationService(mock_db, client=mock_client)
    res = service.send_backup_failure_alert(job_id)

    assert res["success"] is True
    assert mock_client.send_backup_failure_alert.called
    assert mock_db.commit.called
    assert mock_db.add.called

