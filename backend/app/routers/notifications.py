from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["Notifications"])

_store = [
    {"id": 1, "type": "optimization", "title": "Memory right-sized: api-auth-handler", "desc": "Reduced from 512MB to 256MB. Saving PKR 4,200/month.", "time": "2 mins ago", "read": False, "severity": "success"},
    {"id": 2, "type": "optimization", "title": "Spot instance switch: image-processor", "desc": "Switched to Spot instance. 68% cost reduction with zero downtime.", "time": "14 mins ago", "read": False, "severity": "success"},
    {"id": 3, "type": "alert", "title": "Spike detected: webhook-dispatcher", "desc": "Invocation rate increased 32% in the last hour. Monitoring.", "time": "38 mins ago", "read": False, "severity": "warning"},
    {"id": 4, "type": "system", "title": "XGBoost model retrained", "desc": "Model v2.3.1 retrained with 5,000 samples. Accuracy: 94.2%", "time": "6 hours ago", "read": True, "severity": "info"},
]

@router.get("/")
def get_all():
    return {"notifications": _store}

@router.put("/{nid}/read")
def mark_read(nid: int):
    for n in _store:
        if n["id"] == nid:
            n["read"] = True
            return {"ok": True}
    return {"ok": False}

@router.put("/read-all")
def mark_all_read():
    for n in _store:
        n["read"] = True
    return {"ok": True}