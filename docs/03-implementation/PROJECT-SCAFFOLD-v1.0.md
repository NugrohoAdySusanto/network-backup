    # Network Backup Dashboard — Project Scaffold Specification

    **Version:** 1.0  
    **Scope:** Checkpoint C0 / development foundation

    ## Architecture

    ```text
    Browser
       |
    Nginx
       |
       +--> Static Frontend
       |
       +--> FastAPI
              |
              +--> PostgreSQL
              +--> Redis
                       |
                       +--> Celery Worker
                       +--> Celery Beat
    ```

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

    ## Docker Services

    `postgres`
    : PostgreSQL 16 persistent database.

    `redis`
    : Celery broker, Redis-backed sessions later, and per-device locks later.
      AOF is enabled for practical restart resilience, but PostgreSQL remains the
      authoritative data store.

    `api`
    : FastAPI process.

    `worker`
    : Celery background worker. Later owns backup-job execution.

    `beat`
    : Celery Beat. Placeholder schedules are already wired for dispatcher,
      Zabbix sync, and Ceph health refresh.

    `nginx`
    : Serves the approved frontend and proxies `/api/` and `/healthz`.

    ## Current Runnable Backend

    Only the following are intentionally implemented at C0:

    ```text
    GET /healthz
    GET /api/v1/healthz
    ```

    All scheduled Celery tasks are harmless placeholders returning
    `not_implemented`.

    ## Environment

    `.env.example` is the only template committed to source control.
    Real `.env` must never be committed.

    Secrets include:

    ```text
    APP_SECRET
    POSTGRES_PASSWORD
    ZABBIX_API_TOKEN
    NETWORK_SSH_PASSWORD
    S3_ACCESS_KEY
    S3_SECRET_KEY
    CEPH_HEALTH_TOKEN
    FEISHU_WEBHOOK_URL
    ```

    ## Development Rules

    - Do not run SSH in FastAPI requests.
    - Do not move persistent business data into Redis.
    - Do not expose `.env` values to frontend.
    - Do not replace the approved frontend design at scaffold stage.
    - Do not implement AES/HMAC/CSV/PDF in v1.
    - Do not add microservices/Kubernetes.
    - Use Alembic for every schema change after C1 starts.
