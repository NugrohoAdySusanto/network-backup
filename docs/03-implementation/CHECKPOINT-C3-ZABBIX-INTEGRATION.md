
# Checkpoint C3 — Zabbix Integration

**Status:** Baseline implemented; requires validation against the real Zabbix instance.

## Scope

C3 adds:

```text
Zabbix JSON-RPC API client
Network Device Host Group sync
Host Inventory vendor/model mapping
primary management IP mapping
ICMP item availability normalization
~30-second periodic sync
live pre-backup availability query
source_present lifecycle
integration_status update
GET /api/v1/devices
GET /api/v1/devices/{id}
POST /api/v1/devices/sync-zabbix
```

## Source Mapping

```text
Zabbix hostid       -> devices.zabbix_host_id
Zabbix name/host    -> devices.hostname
main interface      -> devices.ip_address
Host Inventory      -> devices.vendor / devices.model
configured item key -> devices.availability_status
```

Default availability key:

```text
icmpping
```

Configuration:

```text
ZABBIX_AVAILABILITY_ITEM_KEY=icmpping
ZABBIX_AVAILABILITY_MAX_AGE_SECONDS=120
```

A stale/missing/unsupported item becomes:

```text
unknown
```

not `down`.

## Two-Layer Status

```text
Background:
every ~30 sec -> cached device status

Backup:
fresh item query immediately before execution
```

A cached UP value is never enough to start SSH.

## Missing Device Rule

Device no longer returned by Network Device group:

```text
source_present = false
availability_status = unknown
```

Device/history is not deleted.

## C3 Validation Gate

Validate on the real environment:

1. API token authenticates.
2. configured Network Device group is correct.
3. Host Inventory vendor/model fields match the real data.
4. management IP selection is correct.
5. `icmpping` exists for target hosts.
6. live UP/DOWN changes appear correctly.
7. stale/missing item maps to UNKNOWN.
8. removed host becomes `source_present=false`.
9. background Celery sync runs with browser closed.
10. no Zabbix secret reaches frontend/log output.

If your Zabbix version/API-token behavior differs, modify only
`integrations/zabbix_client.py`; preserve the service/API contract.
