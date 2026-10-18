
from fastapi import APIRouter

from app.api.audit_logs import router as audit_logs_router
from app.api.auth import router as auth_router
from app.api.backup_settings import router as backup_settings_router
from app.api.backups import router as backups_router
from app.api.dashboard import router as dashboard_router
from app.api.devices import router as devices_router
from app.api.drivers import router as drivers_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.api.snapshots import router as snapshots_router
from app.api.storage import router as storage_router
from app.api.users import router as users_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(users_router)
api_router.include_router(drivers_router)
api_router.include_router(devices_router)
api_router.include_router(backup_settings_router)
api_router.include_router(backups_router)
api_router.include_router(snapshots_router)
api_router.include_router(storage_router)
api_router.include_router(health_router)
api_router.include_router(reports_router)
api_router.include_router(audit_logs_router)

from app.api.storage import rotate_repository_password
api_router.add_api_route(
    "/repositories/{repo_id}/rotate-password",
    rotate_repository_password,
    methods=["POST"],
    tags=["storage"],
)

