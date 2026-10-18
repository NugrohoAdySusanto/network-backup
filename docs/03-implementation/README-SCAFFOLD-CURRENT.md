    # Network Backup Dashboard — Project Scaffold v1.0

    This scaffold implements **Checkpoint C0 / foundation only**.

    It intentionally does **not** implement:
    - database business models/migrations;
    - authentication;
    - Zabbix synchronization;
    - real backup drivers;
    - SHA change detection;
    - Ceph object storage;
    - retention;
    - Feishu alerts.

    Those are built incrementally following the approved architecture documents.

    ## Folder Structure

    ```text
    network-backup-scaffold/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── drivers/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   ├── celery_app.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
├── migrations/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── nginx/
│   └── nginx.conf
├── tests/
│   ├── integration/
│   └── unit/
├── reference/
│   ├── mockup-original.html
│   └── server-original.js
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── DEPENDENCIES.md
└── README.md

    ```

    ## Quick Start

    1. Copy environment file:

       ```bash
       cp .env.example .env
       ```

    2. Replace all `replace-me` values.

    3. For development only, `COOKIE_SECURE=false` is acceptable over plain HTTP.
       Production should use HTTPS and `COOKIE_SECURE=true`.

    4. Build and start:

       ```bash
       docker compose up -d --build
       ```

    5. Check containers:

       ```bash
       docker compose ps
       ```

    6. Check backend through Nginx:

       ```bash
       curl http://localhost:${NGINX_PORT:-8080}/healthz
       ```

    7. Open:

       ```text
       http://<server-ip>:8080/
       ```

    ## Important

    The current frontend `index.html` is the approved mockup baseline and still
    contains demo-side JavaScript. It is preserved so later implementation does not
    redesign the UI. The demo logic must be replaced progressively by real API calls.

    `reference/server-original.js` is retained only as historical mockup reference;
    it is not part of the Docker production architecture.

    ## Next Checkpoint

    C1:
    - SQLAlchemy models;
    - Alembic migrations;
    - PostgreSQL schema from `DATABASE-SCHEMA-ERD-v1.0.md`.

    Do not skip directly to real SSH drivers before C1-C4 are stable.

## Checkpoint Status

```text
C0 Project Scaffold           DONE
C1 DB Models + Alembic        BASELINE IMPLEMENTED
C2 Authentication + RBAC      BASELINE IMPLEMENTED
C3 Zabbix Integration         BASELINE IMPLEMENTED
C4 Driver Registry/Settings   BASELINE IMPLEMENTED
C5 Queue + Job State Machine  BASELINE IMPLEMENTED
C6 Real Netmiko Drivers       NEXT
```

C1 validation must be performed against a real disposable PostgreSQL container
before moving C1 to `VERIFIED`.


## AI Agent Entry Point

For AI/agentic development, do not start from source-code inference.

Read in this order:

```text
AI-CONTEXT-MANIFEST.md
MASTERPLAN-AI-AGENT.md
```

Then follow the numbered `docs/` folders.

See:

```text
PROJECT-FILES-CHECKLIST.md
```

for the complete repository context checklist.
