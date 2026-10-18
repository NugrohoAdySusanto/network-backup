# Checkpoint C1 — SQLAlchemy Models + Alembic Migration

**Status:** Implemented baseline  
**Source of Truth:** `DATABASE-SCHEMA-ERD-v1.0.md`

## What C1 Adds

SQLAlchemy models for:

```text
users
devices
device_backup_settings
backup_jobs
config_objects
snapshots
snapshot_retention_marks
integration_status
```

Alembic migrations:

```text
001_users
002_devices
003_settings
004_jobs
005_objects
006_snapshots
007_marks
008_integrations
009_indexes
```

The migration chain intentionally does **not** seed bootstrap users yet.
Bootstrap/demo accounts belong to C2 Authentication & RBAC because passwords
must first be hashed with Argon2id.

## Important Model Decisions

### User deletion

UI may say `Delete`, but C2 must implement it as:

```text
users.is_active = false
```

Historical foreign keys remain valid.

### Device removal from Zabbix

Never hard-delete the device.

```text
source_present = false
```

### Job / Snapshot / Object separation

```text
backup_jobs
= operational execution history

snapshots
= logical backup versions

config_objects
= physical Ceph S3 objects
```

Do not merge these concepts.

### Schedule slots

Database enforces a partial unique index:

```text
one enabled device per daily_time
```

Application/API must additionally enforce 5-minute slot alignment and produce
human-friendly error messages.

### Hashes

```text
backup_jobs.content_sha256
config_objects.content_sha256
= normalized configuration fingerprint

config_objects.object_sha256
= raw object bytes checksum
```

### Retention

Current protection reasons live in:

```text
snapshot_retention_marks
```

`LATEST_GOOD` is mandatory in C11 retention logic.

## How to Validate C1

From project root:

```bash
cp .env.example .env
# edit DATABASE_URL/POSTGRES values

docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic current
docker compose run --rm api alembic history
```

Run tests:

```bash
docker compose run --rm api pytest -q
```

Optional schema inspection:

```bash
docker compose exec postgres       psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"

docker compose exec postgres       psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"       -c "\d device_backup_settings"
```

## Rollback Test

On a disposable development database only:

```bash
docker compose run --rm api alembic downgrade base
docker compose run --rm api alembic upgrade head
```

Never perform this rollback test on a production database.

## C1 Gate

C1 is accepted only if:

1. all nine migrations apply from an empty PostgreSQL database;
2. `alembic current` reports `009_indexes`;
3. all eight expected tables exist;
4. indexes and check constraints exist;
5. duplicate enabled `daily_time` is rejected;
6. invalid role/status/retention values are rejected;
7. unit tests pass;
8. an upgrade/downgrade cycle works on a disposable DB;
9. `alembic check` produces no unexpected schema diff after models are loaded.

## Agentic AI Instruction

The coding agent may review/refactor implementation details, but must not alter
the frozen schema semantics without approval.

If the agent believes a schema change is required, it must:

```text
1. explain the issue;
2. identify impacted architecture/API/feature docs;
3. propose the migration;
4. wait for approval before changing the schema.
```
