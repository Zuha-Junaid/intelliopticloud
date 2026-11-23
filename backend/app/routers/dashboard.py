from fastapi import APIRouter
from app.services.cloudwatch_service import get_functions

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_summary():
    fns = get_functions()
    current = round(sum(f["monthlyCost"] for f in fns), 2)
    return {
        "costSummary": {
            # Real values from CloudWatch. No savings are claimed until optimizations are applied.
            "previousMonthly": current,
            "currentMonthly": current,
            "savedAmount": 0,
            "savingsPercent": 0,
            "currency": "PKR",
        },
        # SAMPLE DATA for chart illustration only (not measured)
        "trendIsSample": True,
        "savingsTrend": [
            {"month": "Jul", "before": 50000, "after": 31000},
            {"month": "Aug", "before": 50000, "after": 27000},
            {"month": "Sep", "before": 50000, "after": 24000},
            {"month": "Oct", "before": 50000, "after": 21000},
            {"month": "Nov", "before": 50000, "after": 19000},
            {"month": "Dec", "before": 50000, "after": 18000},
        ],
        "systemHealth": {
            "uptime": "N/A",
            "lastOptimized": "Never",
            "functionsMonitored": len(fns),
            "actionsToday": 0,
        },
    }