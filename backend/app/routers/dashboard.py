import time

from fastapi import APIRouter

from app.services import store
from app.services.cloudwatch_service import get_inventory
from app.services.cycle_service import history
from app.services.savings_service import verified_savings

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
STARTED = time.time()


@router.get("/summary")
def get_summary():
    inv = get_inventory()
    fns = inv["functions"]
    current = round(sum(f["monthlyCost"] for f in fns), 2)
    saved = verified_savings()["totalMonthlySavingPkr"] if inv["source"] == "aws" else 0
    baseline = round(current + saved, 2)
    actions = store.list_actions(200)
    today = store.utcnow().date().isoformat()
    applied = [a for a in actions if a["status"] == "applied" and a["mode"] != "rollback"]
    last_cycle = store.kv_get("last_cycle")
    return {
        "source": inv["source"],
        "warning": inv["warning"],
        "costSummary": {
            "previousMonthly": baseline,
            "currentMonthly": current,
            "savedAmount": saved,
            "savingsPercent": round(saved / baseline * 100, 1) if baseline else 0,
            "currency": "PKR",
        },
        "costHistory": history(),  # real snapshots, one point per monitoring cycle
        "systemHealth": {
            "serverUptimeHours": round((time.time() - STARTED) / 3600, 1),
            "lastOptimized": applied[0]["takenAt"] if applied else None,
            "lastCycle": last_cycle["at"] if last_cycle else None,
            "functionsMonitored": len(fns),
            "actionsToday": sum(1 for a in applied if a["takenAt"][:10] == today),
        },
    }
