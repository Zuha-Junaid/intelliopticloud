from collections import defaultdict

from fastapi import APIRouter

from app.services.cloudwatch_service import get_inventory
from app.services.cycle_service import history
from app.services.savings_service import verified_savings

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/savings")
def savings_report():
    """Savings measured from real billed durations before and after each applied change."""
    v = verified_savings()
    monthly = defaultdict(float)
    for item in v["items"]:
        if item["status"] == "verified" and item["monthlySavingPkr"] > 0:
            monthly[item["takenAt"][:7]] += item["monthlySavingPkr"]
    return {"verified": v["items"], "totalMonthlySavingPkr": v["totalMonthlySavingPkr"],
            "monthly": [{"month": k, "saved": round(x, 2)} for k, x in sorted(monthly.items())]}


@router.get("/cost-breakdown")
def cost_breakdown():
    inv = get_inventory()
    breakdown = sorted([{"name": f["name"], "cost": f["monthlyCost"]} for f in inv["functions"]],
                       key=lambda x: x["cost"], reverse=True)
    return {"breakdown": breakdown, "source": inv["source"], "warning": inv["warning"]}


@router.get("/history")
def cost_history(days: int = 30):
    return {"history": history(max(1, min(days, 365)))}
