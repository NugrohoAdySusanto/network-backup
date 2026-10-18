# AI-CONTEXT-MANIFEST — Network Backup Dashboard

**Version:** 2.0  
**Purpose:** Tell the AI coding agent what is authoritative and what to read first.

---

# 1. Start Here

Read:

```text
1. AI-CONTEXT-MANIFEST.md
2. MASTERPLAN-AI-AGENT.md
```

Then follow the reading order below.

---

# 2. Mandatory Reading Order

## Product

```text
docs/01-product/FEATURE-FINAL.md
docs/01-product/DESIGN-FINAL.md
docs/01-product/BRIEF-FRONTEND-FINAL.md
```

## Architecture

```text
docs/02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md
docs/02-architecture/DATABASE-SCHEMA-ERD-v1.0.md
docs/02-architecture/API-CONTRACT-v1.0.md
docs/02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md
```

## Existing implementation notes

```text
docs/03-implementation/PROJECT-SCAFFOLD-v1.0.md
docs/03-implementation/DEPENDENCIES.md
docs/03-implementation/CHECKPOINT-C1-DATABASE-MODELS-ALEMBIC.md
docs/03-implementation/CHECKPOINT-C2-AUTHENTICATION-RBAC.md
docs/03-implementation/CHECKPOINT-C3-ZABBIX-INTEGRATION.md
docs/03-implementation/CHECKPOINT-C4-DRIVER-REGISTRY-SETTINGS.md
docs/03-implementation/CHECKPOINT-C5-QUEUE-JOB-STATE-MACHINE.md
docs/03-implementation/CHECKPOINT-C6-C10-PRODUCTION-DEPLOYMENT-DRIVERS.md
docs/03-implementation/CHECKPOINT-C15-REPORTING-CSV-PDF.md
docs/03-implementation/CHECKPOINT-C16-RUIJIE-SWITCH-SAVE-FLOW.md
docs/03-implementation/CHECKPOINT-C17-BACKUP-STATUS-HISTORY-FIREWALL-ANALYSIS.md
docs/03-implementation/CHECKPOINT-C18-FEISHU-WEBHOOK-ALERTING.md
docs/03-implementation/CHECKPOINT-C19-S3-AND-WORKER-MANAGEMENT.md
docs/03-implementation/CHECKPOINT-C20-V1-RELEASE-VERIFICATION-AND-V2-ROADMAP.md
docs/03-implementation/CHECKPOINT-C21-AT-REST-PAYLOAD-ENCRYPTION.md
```

## Visual reference

```text
docs/04-reference/mockup-original.html
docs/04-reference/server-original.js
```

Then inspect current source code.

---

# 3. Current Build Priority

Do not follow old checkpoint numbers as the main priority.

The active build priority is:

```text
PHASE 1
Web + Backend + DB + API + Auth + Zabbix + Frontend integration

PHASE 2
Backup engine

PHASE 3
Formal testing / hardening / TA evidence
```

Minimal smoke checks are allowed during coding.

---

# 4. Files Not Authoritative

Do not use old drafts as implementation authority:

```text
FEATURE.md
DESIGN.md
brief-mockup.md
AGENTIC-AI-IMPLEMENTATION-PLAN-v1.0.md
old scaffold ZIPs
mockup video frames/contact sheets
```

If they are present elsewhere, ignore them unless explicitly asked to investigate history.

---

# 5. Do Not Modify Without Approval

```text
MASTERPLAN-AI-AGENT.md
docs/01-product/*
docs/02-architecture/*
```

You may fix source implementation defects, but do not redefine contracts silently.

---

# 6. Conflict Rule

If source code disagrees with an authoritative document:

```text
prefer the authoritative document
report the discrepancy
fix code if the fix does not change the approved contract
```

If two authoritative documents conflict:

```text
stop
report both
wait for resolution
```

---

# 7. First Coding Goal

The first coding goal is not "backup."

It is:

```text
REAL WEB APPLICATION USING REAL ZABBIX DATA
```

Target first milestone:

```text
real login
real PostgreSQL
real Redis session
real Zabbix devices
real status
real driver/schedule settings
approved frontend connected to API
Admin/Viewer behavior
```
