# Dependency List — v1

## Runtime

| Package | Role |
|---|---|
| FastAPI | HTTP API |
| Uvicorn | ASGI server |
| Pydantic | API/config validation |
| pydantic-settings | `.env` / backend settings |
| SQLAlchemy 2.x | PostgreSQL ORM |
| psycopg 3 | PostgreSQL driver |
| Alembic | Database migrations |
| Celery | Background worker and task execution |
| redis | Redis client |
| Netmiko | SSH network-device automation |
| boto3 | Ceph S3/RGW integration |
| HTTPX | Zabbix, Ceph health, Feishu HTTP integration |
| argon2-cffi | Argon2id user-password hashing |
| python-multipart | Form/multipart support where required |

## Development/Test

| Package | Role |
|---|---|
| pytest | Test runner |
| pytest-cov | Coverage |
| pytest-asyncio | Async test support where needed |
| Ruff | Lint/format checks |
| mypy | Static type checking |

## Infrastructure Images

| Image | Role |
|---|---|
| python:3.12-slim | Backend base |
| postgres:16-alpine | Persistent application DB |
| redis:7-alpine | Celery broker, session, locks |
| nginx:1.27-alpine | Reverse proxy + static frontend |

## Version Policy

`requirements.txt` intentionally pins compatible major ranges instead of exact
patch versions during the scaffold phase. Before production/demo freeze, generate
a reproducible lock/freeze after the integration test environment is stable.
