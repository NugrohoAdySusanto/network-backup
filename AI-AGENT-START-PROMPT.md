# AI-AGENT-START-PROMPT

Copy/paste this instruction to the coding agent after opening the project repository.

---

You are continuing an existing designed project, not creating a new architecture.

First read:

1. `AI-CONTEXT-MANIFEST.md`
2. `MASTERPLAN-AI-AGENT.md`
3. all authoritative documents in the reading order defined there.

Do not redesign the application.

Your immediate priority is **PHASE 1 — build the real web application platform**:

- make the Dockerized FastAPI/PostgreSQL/Redis/Nginx stack usable;
- preserve the approved SQLAlchemy/Alembic database schema;
- complete real backend authentication and Admin/Viewer RBAC;
- complete real Zabbix integration using the Network Device group and Host Inventory;
- expose the approved device/user/driver/settings APIs;
- connect the approved existing frontend to the real backend;
- replace frontend mock/localStorage/static operational data with API data;
- show real Zabbix device hostname/IP/vendor/model/UP-DOWN-UNKNOWN status;
- allow Admin to manually assign Backup Driver, Daily time, and retention;
- keep Viewer read-only.

Do not start implementing real vendor SSH backup commands, SHA-256 backup logic, Ceph object storage, retention execution, or Feishu workflow until the Phase 1 web application is usable.

Minimal compile/smoke checks are allowed during development, but formal full testing/hardening is Phase 3 and should not become the current focus.

Preserve:
- Modular Monolith;
- FastAPI;
- PostgreSQL;
- Redis/Celery;
- HTML/Tailwind/Vanilla JS;
- server-side session cookie;
- Zabbix as device/status SSOT;
- current database schema;
- current API contract;
- existing approved frontend visual design.

If source code conflicts with an authoritative document, fix source code to the approved contract when possible. If authoritative documents conflict with each other or a required architecture change is needed, stop and report the issue before changing the contract.

At the end of your work session report:

- what was built;
- files changed;
- migrations changed/added;
- endpoints completed;
- frontend modules connected;
- Zabbix integration status;
- environment variables needed;
- blockers;
- next recommended Phase 1 build step.
