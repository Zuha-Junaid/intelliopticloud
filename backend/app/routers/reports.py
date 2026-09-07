from fastapi import APIRouter
from app.services.cloudwatch_service import get_functions

router = APIRouter(prefix="/reports", tags=["Reports"])

TREND = [
    {"month": "Jul", "before": 50000, "after": 31000},
    {"month": "Aug", "before": 50000, "after": 27000},
    {"month": "Sep", "before": 50000, "after": 24000},
    {"month": "Oct", "before": 50000, "after": 21000},
    {"month": "Nov", "before": 50000, "after": 19000},
    {"month": "Dec", "before": 50000, "after": 18000},
]

@router.get("/savings")
def savings_report():
    detailed = [
        {**m, "saved": m["before"] - m["after"],
         "percentReduction": round((m["before"] - m["after"]) / m["before"] * 100, 1)}
        for m in TREND
    ]
    return {"report": detailed}

@router.get("/cost-breakdown")
def cost_breakdown():
    fns = get_functions()
    breakdown = sorted(
        [{"name": f["name"], "cost": f["monthlyCost"]} for f in fns],
        key=lambda x: x["cost"], reverse=True
    )
    return {"breakdown": breakdown}