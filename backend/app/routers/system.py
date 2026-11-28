from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.security import get_current_user
from app.services import store
from app.services.cloudwatch_service import aws_configured, get_inventory
from app.services.cycle_service import run_cycle

router = APIRouter(tags=["System"])


class SettingsUpdate(BaseModel):
    autonomy: str | None = None
    min_confidence: int | None = None
    notify_actions: bool | None = None
    notify_alerts: bool | None = None
    notify_summary: bool | None = None


@router.get("/system/status")
def status(user=Depends(get_current_user)):
    inv = get_inventory()
    return {
        "aws": {"connected": aws_configured(), "region": settings.AWS_REGION, "source": inv["source"],
                "warning": inv["warning"]},
        "apply": {"enabled": settings.APPLY_ENABLED, "allowedPrefix": settings.APPLY_ALLOWED_PREFIX},
        "schedulerConfigured": bool(settings.CRON_TOKEN),
        "lastCycle": store.kv_get("last_cycle"),
    }


@router.post("/system/run-cycle")
def run(x_cron_token: str | None = Header(default=None), authorization: str | None = Header(default=None)):
    """Called by the scheduled job (X-Cron-Token) or by a signed-in user (Run Cycle Now)."""
    if settings.CRON_TOKEN and x_cron_token == settings.CRON_TOKEN:
        return run_cycle(trigger="scheduled")
    if authorization:
        from fastapi.security import HTTPAuthorizationCredentials
        scheme, _, token = authorization.partition(" ")
        get_current_user(HTTPAuthorizationCredentials(scheme=scheme, credentials=token))
        return run_cycle(trigger="manual")
    raise HTTPException(401, "Not authenticated")


@router.get("/settings")
def read_settings(user=Depends(get_current_user)):
    return store.get_settings()


@router.put("/settings")
def write_settings(body: SettingsUpdate, user=Depends(get_current_user)):
    try:
        return store.update_settings(body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
