
# Checkpoint C4 — Driver Registry + Device Backup Settings

**Status:** Baseline implemented.

## Registry

Production keys:

```text
sangfor-nsf
mikrotik-routeros
ruijie-switch
```

All are metadata-only at C4.

Real SSH commands are intentionally NOT implemented before device PoC.

Development-only optional driver:

```text
mock-backup
```

enabled only when:

```text
ENABLE_MOCK_DRIVER=true
APP_ENV != production
```

## API

```text
GET /api/v1/drivers

GET    /api/v1/devices/{id}/backup-settings
PUT    /api/v1/devices/{id}/backup-settings
DELETE /api/v1/devices/{id}/backup-settings
```

## Save

Persists:

```text
driver_key
schedule_enabled
daily_time
retention_policy
updated_by
next_run_at
```

## Clear

Clears:

```text
driver_key
schedule_enabled
daily_time
next_run_at
last_dispatched_at
```

It does NOT delete:

```text
device
jobs
snapshots
config objects
history
```

Retention preference remains stored.

## Schedule Rules

- Daily only.
- `Asia/Jakarta`.
- 5-minute boundaries.
- one enabled device per time slot.
- driver required before schedule can be enabled.
- device must still be present in Zabbix source.

## C4 Validation Gate

1. `/drivers` returns stable keys.
2. Viewer can read but cannot modify settings.
3. Admin can manually assign a driver.
4. invalid driver key is rejected.
5. `01:03` is rejected for a 5-minute slot policy.
6. two enabled devices cannot both use `01:05`.
7. next_run_at is calculated in Asia/Jakarta.
8. Clear preserves historical data.
9. no vendor auto-assignment occurs.
10. no arbitrary command exists in API.

## C6 Reminder

C4 registration does not mean real vendor collection is complete.

C6 will replace the metadata-only implementations with verified Netmiko
collection routines after real-device PoC.
