from fastapi import APIRouter, HTTPException
from app.services.cloudwatch_service import get_functions

router = APIRouter(prefix="/resources", tags=["Resources"])

@router.get("/functions")
def list_functions():
    fns = get_functions()
    return {"functions": fns, "total": len(fns)}

@router.get("/functions/{name}")
def get_function(name: str):
    fns = get_functions()
    fn = next((f for f in fns if f["name"] == name), None)
    if not fn:
        raise HTTPException(404, "Function not found")
    return fn