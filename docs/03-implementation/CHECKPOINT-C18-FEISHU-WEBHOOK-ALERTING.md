# CHECKPOINT C18 — Feishu Webhook Alerting & MikroTik Failure Live Verification

**Execution Date:** 2026-10-06  
**Status:** COMPLETE (Production Verified)

---

## 1. Objective & Scope

Implement automated alerting to Feishu via Custom Bot Webhook (`FEISHU_WEBHOOK_URL`) upon terminal backup failures and skips, compliant with **Phase 2J** of [MASTERPLAN-AI-AGENT.md](../../MASTERPLAN-AI-AGENT.md) and Section 21 of [BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md](../../docs/02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md).

Validate the system end-to-end against live physical network hardware (`MKK-HQ_Router`, MikroTik CCR1016-12G at `10.11.0.2:22345`) by simulating an incorrect password authentication failure (`AUTHENTICATION_FAILED`) and confirming delivery to Feishu.

---

## 2. Technical Architecture & Component Implementation

### 2.1 Feishu Webhook Integration Client (`FeishuClient`)
* **File:** `backend/app/integrations/feishu_client.py`
* **Transport:** HTTP POST via `httpx.Client` with configurable timeout (default 10.0s).
* **Message Format:**
  * **Primary:** Rich Interactive Card (`msg_type: "interactive"`) with red header banner (`template: "red"`) and structured markdown fields.
  * **Fallback:** Plain Text (`msg_type: "text"`) triggered automatically if card formatting is rejected or unparseable.
* **Payload Fields (12 Contractual Fields):**
  1. `Device Name`: Hostname from device record (e.g., `MKK-HQ_Router`).
  2. `Device IP`: IP address without CIDR suffix (e.g., `10.11.0.2`).
  3. `Vendor`: Device vendor (e.g., `MikroTik`).
  4. `Model`: Device model (e.g., `CCR1016-12G`).
  5. `Driver`: Driver key used (e.g., `mikrotik-routeros`).
  6. `Job ID`: UUID string of the failed backup job.
  7. `Timestamp`: Localized in `Asia/Jakarta` (WIB) timezone format.
  8. `Final State`: Terminal state (`FAILED`, `SKIPPED_DEVICE_DOWN`, `SKIPPED_STATUS_UNKNOWN`).
  9. `Failure Stage`: Pipeline stage (`QUEUED`, `PRECHECKING_ZABBIX`, `CONNECTING`, `COLLECTING`, `NORMALIZING`, `VALIDATING`, `UPLOADING`, `VERIFYING`).
  10. `Failure Reason`: Descriptive error message or failure code.
  11. `Attempt Count`: Current attempt count vs maximum allowed attempts (e.g., `1 / 3`).
  12. `Last Successful Backup`: Timestamp of the most recent retained snapshot in WIB, or `None`.

### 2.2 Notification Orchestration Service (`NotificationService`)
* **File:** `backend/app/services/notification_service.py`
* **Responsibilities:**
  1. Loads `BackupJob` and associated `Device` from the PostgreSQL database.
  2. Queries the latest retained snapshot from `Snapshot` table for historical context.
  3. Dispatches the alert through `FeishuClient`.
  4. Records the operational status into `integration_status` table (`name = 'feishu_webhook'`) including timestamp, delivery status (`OK` / `ERROR`), and raw payload responses for auditability.
  5. Enforces defensive error handling: failure to communicate with Feishu never crashes the calling Celery worker or API process.

### 2.3 State-Machine Integration
* **File:** `backend/app/services/backup_execution_service.py`
* Added centralized `_fail_job(...)` helper to orchestrate transition + notification in one place.
* Hooked across all terminal unsuccessful states:
  * `DEVICE_NOT_FOUND`
  * `CONCURRENT_BACKUP`
  * `SKIPPED_DEVICE_DOWN`
  * `SKIPPED_STATUS_UNKNOWN`
  * `DRIVER_NOT_ASSIGNED` / `DRIVER_NOT_FOUND`
  * `CONNECTING`: `AUTHENTICATION_FAILED`, `CONNECTION_TIMEOUT`, `SSH_TRANSPORT_ERROR`, `SSH_UNKNOWN_ERROR`
  * `COLLECTING`: `COMMAND_TIMEOUT`, `COMMAND_FAILED`, `COLLECTION_ERROR`
  * `NORMALIZING`: `NORMALIZATION_FAILED`, `NORMALIZATION_ERROR`
  * `VALIDATING`: `INVALID_CONFIG`, `VALIDATION_ERROR`
  * `UPLOADING`: `S3_UPLOAD_FAILED`
  * `VERIFYING`: `OBJECT_NOT_FOUND_IN_STORAGE`, `S3_VERIFICATION_FAILED`
* Also hooked into `BackupJobService.mark_enqueue_failure` for early queue failures.

---

## 3. Automated Unit Testing

* **File:** `tests/unit/test_notifications.py`
* **Test Cases:**
  1. `test_feishu_client_card_success`: Asserts card payload structure and header colors.
  2. `test_feishu_client_card_failure_fallback_text`: Asserts automatic plain text fallback when card format is rejected by the bot API.
  3. `test_feishu_client_empty_webhook`: Asserts graceful handling when `FEISHU_WEBHOOK_URL` is unconfigured.
  4. `test_notification_service_orchestration`: Asserts database integration, context gathering, and `integration_status` recording.
* **Test Run Result:** **29/29 passed** across the entire suite (`pytest tests/unit`).

---

## 4. Live Verification Against Physical Hardware (`MKK-HQ_Router`)

### 4.1 Target Specification
* **Hostname:** `MKK-HQ_Router` (Device ID 24)
* **IP Address:** `10.11.0.2:22345`
* **Vendor & Model:** MikroTik CCR1016-12G
* **Driver:** `mikrotik-routeros`
* **Authentication Account:** `backupadmin`

### 4.2 Test Execution (Incorrect Password Simulation)
1. **Trigger:** Created manual backup job `2c1e94aa-fdd4-4a83-b4ac-15ef37a507f2`.
2. **Execution:** Dispatched with invalid password `IncorrectPasswordTest123!`.
3. **Driver Response:** Netmiko SSH transport caught authentication rejection from RouterOS and raised `DriverAuthenticationError: SSH authentication failed for MKK-HQ_Router (10.11.0.2:22345)`.
4. **Job State Machine:**
   * `state`: `FAILED`
   * `failure_stage`: `CONNECTING`
   * `failure_code`: `AUTHENTICATION_FAILED`
   * `failure_message`: `SSH authentication failed for MKK-HQ_Router (10.11.0.2:22345)`
   * `attempt_count`: `1`
5. **Feishu Bot Response:**
   * Endpoint: `https://open.feishu.cn/open-apis/bot/v2/hook/a45ec63a-92ce-45f5-9c89-f61c9ddc6116`
   * HTTP Status: `200 OK`
   * Payload: `{"StatusCode": 0, "StatusMessage": "success", "code": 0, "msg": "success"}`
6. **Integration Status Record:**
   * Table: `integration_status`
   * Name: `feishu_webhook`
   * Status: `OK`
   * Summary: `Alert delivered for MKK-HQ_Router`
   * Last Checked: `2026-10-05 18:26:58.985794+00:00`
7. **Frontend Status Verification:**
   * Table row for `MKK-HQ_Router` automatically displays a **Failed** badge with red glowing dot.
   * Hover tooltip displays detailed failure reason (`SSH authentication failed for MKK-HQ_Router (10.11.0.2:22345)`).
   * Clicking the badge opens the backup history dialog showing the exact execution failure log.
