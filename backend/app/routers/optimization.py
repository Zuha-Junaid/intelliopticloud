from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services import store
from app.services.apply_service import ApplyError, apply_architecture, apply_memory, rollback
from app.services.cloudwatch_service import get_inventory
from app.services.cycle_service import build_recommendations
from app.services.optimizer_service import _train, get_accuracy, get_meta, get_model_source

router = APIRouter(prefix="/optimization", tags=["Optimization"])


class ApplyRequest(BaseModel):
    function: str
    kind: str            # memory | architecture
    value: str           # e.g. "256" or "arm64"
    confirm: bool = False


@router.get("/model-info")
def model_info():
    meta = get_meta()
    return {
        "algorithm": "XGBoost Regressor",
        "trainedOn": meta.get("trainedOn") or "Synthetic cloud usage data (Google Colab)",
        "accuracy": get_accuracy(),
        "version": meta.get("version", "v2.3.1"),
        "features": meta.get("features", []),
        "source": get_model_source(),
        "heldOut": meta.get("metrics_held_out"),
    }


@router.get("/pipeline")
def pipeline():
    """Real status of the last monitoring cycle. Nothing here is a fixed or invented value."""
    last = store.kv_get("last_cycle")
    cfg = store.get_settings()
    if not last:
        stages = [
            ("Data collection", "No cycle has run yet. Press Run Cycle Now or wait for the scheduled job.", "waiting"),
            ("Feature extraction", "Waiting for the first cycle.", "waiting"),
            ("XGBoost prediction", "Waiting for the first cycle.", "waiting"),
            ("Decision validation", "Waiting for the first cycle.", "waiting"),
            ("Applying changes", "Waiting for the first cycle.", "waiting"),
        ]
    else:
        collect = "complete" if last["source"] == "aws" else "warning"
        apply_state = ("complete" if last["applied"] else "waiting")
        if not settings.APPLY_ENABLED:
            apply_desc = "Disabled on the server (APPLY_ENABLED=false). Recommendations only."
        elif cfg["autonomy"] == "auto":
            apply_desc = f"Automatic mode: {last['applied']} change(s) applied in the last cycle."
        elif cfg["autonomy"] == "approve":
            apply_desc = "Approval mode: changes are applied only when you press Apply."
        else:
            apply_desc = "Monitor-only mode: no changes are applied."
        stages = [
            ("Data collection", f"{last['functions']} function(s) read from {'AWS' if last['source']=='aws' else 'sample data'} at {last['at']}.", collect),
            ("Feature extraction", f"{last['measured']} function(s) have measured peak memory from CloudWatch Logs.", "complete"),
            ("XGBoost prediction", f"{last['recommendations']} function(s) can save memory.", "complete"),
            ("Decision validation", f"Safety checks: 25% headroom over peak memory, confidence at least {cfg['min_confidence']}%, allowed name prefix '{settings.APPLY_ALLOWED_PREFIX}'.", "complete"),
            ("Applying changes", apply_desc, apply_state),
        ]
    return {"lastCycle": last, "stages": [{"id": i + 1, "stage": s, "desc": d, "status": st}
                                          for i, (s, d, st) in enumerate(stages)]}


@router.get("/recommendations")
def recommendations():
    inv = get_inventory()
    return {"recommendations": build_recommendations(inv["functions"]), "source": inv["source"],
            "warning": inv["warning"], "applyEnabled": settings.APPLY_ENABLED,
            "allowedPrefix": settings.APPLY_ALLOWED_PREFIX, "autonomy": store.get_settings()["autonomy"]}


@router.post("/apply")
def apply(body: ApplyRequest):
    if not body.confirm:
        raise HTTPException(400, "Confirmation is required to change a function on AWS.")
    try:
        if body.kind == "memory":
            if not body.value.isdigit():
                raise HTTPException(400, "Memory value must be a number of MB.")
            return apply_memory(body.function, int(body.value))
        if body.kind == "architecture":
            return apply_architecture(body.function, body.value)
    except ApplyError as exc:
        raise HTTPException(exc.status_code, exc.message)
    raise HTTPException(400, "kind must be memory or architecture")


@router.post("/rollback/{action_id}")
def rollback_action(action_id: int):
    try:
        return rollback(action_id)
    except ApplyError as exc:
        raise HTTPException(exc.status_code, exc.message)


@router.get("/actions")
def actions():
    return {"actions": store.list_actions()}


@router.post("/retrain")
def retrain():
    _train()
    return {"message": "Model retrained", "accuracy": get_accuracy(), "source": get_model_source()}
