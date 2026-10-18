from __future__ import annotations

from dataclasses import asdict
from fastapi import APIRouter, Depends

from app.dependencies import AuthContext, get_current_context
from app.integrations.ceph_health_client import CephHealthClient

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ceph")
def get_ceph_health(
    _: AuthContext = Depends(get_current_context),
):
    client = CephHealthClient()
    result = client.get_health()
    return {"data": asdict(result)}
