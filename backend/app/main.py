from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import inspect

from app.api.router import api_router
from app.config import settings
from app.core.errors import AppError
from app.core.security_middleware import security_audit_middleware
from app.database import get_engine

logger = logging.getLogger(__name__)

EXPECTED_TABLES = {
    "users",
    "devices",
    "device_backup_settings",
    "backup_jobs",
    "config_objects",
    "snapshots",
    "snapshot_retention_marks",
    "integration_status",
    "custom_drivers",
    "storage_repositories",
    "system_audit_logs",
}


def verify_schema_contract() -> None:
    """
    Verifies that required database tables and columns exist and match the schema contract.
    Fails closed and aborts startup if migration/schema contract does not match (REL-01).
    """
    try:
        inspector = inspect(get_engine())
        existing_tables = set(inspector.get_table_names())
        missing_tables = EXPECTED_TABLES - existing_tables
        if missing_tables:
            error_msg = (
                f"Database schema contract failure: Missing required tables: {missing_tables}. "
                "Startup blocked. Run 'alembic upgrade head' before starting the service."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        # Verify critical columns required by current models
        sr_cols = {c["name"] for c in inspector.get_columns("storage_repositories")}
        if "master_key_encrypted" not in sr_cols:
            error_msg = (
                "Database schema contract failure: Column 'storage_repositories.master_key_encrypted' is missing. "
                "Startup blocked. Run 'alembic upgrade head'."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        bj_cols = {c["name"] for c in inspector.get_columns("backup_jobs")}
        if "repository_id" not in bj_cols:
            error_msg = (
                "Database schema contract failure: Column 'backup_jobs.repository_id' is missing. "
                "Startup blocked. Run 'alembic upgrade head'."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        logger.info("Database schema contract verification passed.")
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        logger.warning("Could not complete database schema check during startup: %s", exc)


def verify_security_configuration() -> None:
    """
    Verifies critical security settings on startup (SEC-03).
    Fails closed if SSH_STRICT_HOST_KEY_CHECKING is enabled but known_hosts is missing or empty.
    """
    import os
    if settings.ssh_strict_host_key_checking:
        hosts_path = settings.ssh_known_hosts_path
        if not os.path.exists(hosts_path) or os.path.getsize(hosts_path) == 0:
            error_msg = (
                f"SSH security configuration failure: 'ssh_strict_host_key_checking' is enabled but "
                f"known_hosts file at '{hosts_path}' does not exist or is empty. "
                "Startup blocked to prevent MITM attacks."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
        logger.info("SSH strict host key checking verification passed (known_hosts: %s)", hosts_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env != "test":
        verify_schema_contract()
        verify_security_configuration()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.middleware("http")(security_audit_middleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = exc.errors()
    code = "VALIDATION_ERROR"
    message = "Request validation failed."

    for error in errors:
        ctx_error = error.get("ctx", {}).get("error")
        if ctx_error is not None:
            marker = str(ctx_error)
            if "PASSWORD_CONFIRMATION_MISMATCH" in marker:
                code = "PASSWORD_CONFIRMATION_MISMATCH"
                message = "New password confirmation does not match."
                break
            if "INVALID_ROLE" in marker:
                code = "INVALID_ROLE"
                message = "Role must be admin or viewer."
                break

    safe_details = {
        "fields": [
            {
                "location": [str(item) for item in error.get("loc", ())],
                "message": error.get("msg", "Invalid value."),
            }
            for error in errors
        ]
    }

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": safe_details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/api/v1/healthz", tags=["system"])
def api_healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


app.include_router(api_router)
