from fastapi import APIRouter
from app.services.cloudwatch_service import get_functions

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_summary():
    fns = get_functions()
    current = sum(f["monthlyCost"] for f in fns)
    previous = round(current / 0.36, 2)
    return {
        "costSummary": {
            "previousMonthly": previous,
            "currentMonthly": round(current, 2),
            "savedAmount": round(previous - current, 2),
            "savingsPercent": 64,
            "currency": "PKR",
        },
        "savingsTrend": [
            {"month": "Jul", "before": 50000, "after": 31000},
            {"month": "Aug", "before": 50000, "after": 27000},
            {"month": "Sep", "before": 50000, "after": 24000},
            {"month": "Oct", "before": 50000, "after": 21000},
            {"month": "Nov", "before": 50000, "after": 19000},
            {"month": "Dec", "before": 50000, "after": 18000},
        ],
        "systemHealth": {
            "uptime": "99.98%",
            "lastOptimized": "2 mins ago",
            "functionsMonitored": len(fns),
            "actionsToday": 12,
        },
    }