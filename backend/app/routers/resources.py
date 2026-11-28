from fastapi import APIRouter, HTTPException

from app.services.cloudwatch_service import get_inventory

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/functions")
def list_functions():
    inv = get_inventory()
    return {"functions": inv["functions"], "total": len(inv["functions"]),
            "source": inv["source"], "warning": inv["warning"], "readAt": inv["readAt"]}


@router.get("/functions/{name}")
def get_function(name: str):
    fn = next((f for f in get_inventory()["functions"] if f["name"] == name), None)
    if not fn:
        raise HTTPException(404, "Function not found")
    return fn
