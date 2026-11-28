from fastapi import APIRouter, HTTPException

from app.services import store

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def get_all():
    return {"notifications": store.list_notifications()}


# read-all must be declared before /{nid}/read so the path is not parsed as an id
@router.put("/read-all")
def mark_all_read():
    store.mark_all_read()
    return {"ok": True}


@router.put("/{nid}/read")
def mark_read(nid: int):
    if not store.mark_read(nid):
        raise HTTPException(404, "Notification not found")
    return {"ok": True}
