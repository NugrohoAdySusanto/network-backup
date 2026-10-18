# PROJECT-FILES-CHECKLIST — What to Give the AI Agent

This is the complete active project-context set.

## 1. MUST INCLUDE AT PROJECT ROOT

```text
MASTERPLAN-AI-AGENT.md
AI-CONTEXT-MANIFEST.md
PROJECT-FILES-CHECKLIST.md
README.md
.env.example
.gitignore
docker-compose.yml
alembic.ini
```

## 2. MUST INCLUDE — PRODUCT DOCUMENTS

```text
docs/01-product/FEATURE-FINAL.md
docs/01-product/DESIGN-FINAL.md
docs/01-product/BRIEF-FRONTEND-FINAL.md
```

These explain what the application must do and how the UI should look.

## 3. MUST INCLUDE — ARCHITECTURE CONTRACTS

```text
docs/02-architecture/BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md
docs/02-architecture/DATABASE-SCHEMA-ERD-v1.0.md
docs/02-architecture/API-CONTRACT-v1.0.md
docs/02-architecture/BACKUP-DRIVER-CONTRACT-v1.0.md
```

These are the main technical contracts.

## 4. INCLUDE — CURRENT IMPLEMENTATION NOTES

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

They show what baseline code already exists.

## 5. MUST INCLUDE — CURRENT SOURCE

```text
backend/
frontend/
migrations/
nginx/
tests/
```

Also include:

```text
backend/requirements.txt
backend/requirements-dev.txt
backend/Dockerfile
```

## 6. INCLUDE — VISUAL REFERENCE

```text
docs/04-reference/mockup-original.html
docs/04-reference/server-original.js
```

`mockup-original.html` is the approved visual reference.

`server-original.js` is only historical reference; do not use it as the production backend.

## 7. DO NOT INCLUDE AS ACTIVE AUTHORITY

```text
FEATURE.md
DESIGN.md
brief-mockup.md
AGENTIC-AI-IMPLEMENTATION-PLAN-v1.0.md
old C0/C1/C2/C5 ZIP packages
mockup videos
frame images
contact sheets
temporary screenshots
```

These can be archived outside the project repository.

## 8. NEVER COMMIT

```text
.env
real passwords
Zabbix API token
SSH password
Ceph/S3 access key
Ceph/S3 secret
Ceph health token
Feishu webhook
private SSH keys
real exported device configurations
```

## 9. RECOMMENDED PROJECT TREE

```text
network-backup/
├── MASTERPLAN-AI-AGENT.md
├── AI-CONTEXT-MANIFEST.md
├── PROJECT-FILES-CHECKLIST.md
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── alembic.ini
│
├── docs/
│   ├── 01-product/
│   │   ├── FEATURE-FINAL.md
│   │   ├── DESIGN-FINAL.md
│   │   └── BRIEF-FRONTEND-FINAL.md
│   │
│   ├── 02-architecture/
│   │   ├── BACKEND-ARCHITECTURE-DATABASE-SCHEMA-v1.0.md
│   │   ├── DATABASE-SCHEMA-ERD-v1.0.md
│   │   ├── API-CONTRACT-v1.0.md
│   │   └── BACKUP-DRIVER-CONTRACT-v1.0.md
│   │
│   ├── 03-implementation/
│   │   ├── PROJECT-SCAFFOLD-v1.0.md
│   │   ├── DEPENDENCIES.md
│   │   ├── CHECKPOINT-C1-DATABASE-MODELS-ALEMBIC.md
│   │   ├── CHECKPOINT-C2-AUTHENTICATION-RBAC.md
│   │   ├── CHECKPOINT-C3-ZABBIX-INTEGRATION.md
│   │   ├── CHECKPOINT-C4-DRIVER-REGISTRY-SETTINGS.md
│   │   ├── CHECKPOINT-C5-QUEUE-JOB-STATE-MACHINE.md
│   │   ├── CHECKPOINT-C6-C10-PRODUCTION-DEPLOYMENT-DRIVERS.md
│   │   ├── CHECKPOINT-C15-REPORTING-CSV-PDF.md
│   │   ├── CHECKPOINT-C16-RUIJIE-SWITCH-SAVE-FLOW.md
│   │   ├── CHECKPOINT-C17-BACKUP-STATUS-HISTORY-FIREWALL-ANALYSIS.md
│   │   ├── CHECKPOINT-C18-FEISHU-WEBHOOK-ALERTING.md
│   │   ├── CHECKPOINT-C19-S3-AND-WORKER-MANAGEMENT.md
│   │   ├── CHECKPOINT-C20-V1-RELEASE-VERIFICATION-AND-V2-ROADMAP.md
│   │   └── CHECKPOINT-C21-AT-REST-PAYLOAD-ENCRYPTION.md
│   │
│   └── 04-reference/
│       ├── mockup-original.html
│       └── server-original.js
│
├── backend/
├── frontend/
├── migrations/
├── nginx/
└── tests/
```
