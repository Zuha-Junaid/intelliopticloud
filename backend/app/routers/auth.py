from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import RegisterRequest, LoginRequest, ProfileUpdate
from app.security import get_current_user
from app.services.auth_service import register, authenticate, create_token, update_profile

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
def register_user(body: RegisterRequest):
    if not body.name or not body.email or len(body.password) < 8:
        raise HTTPException(400, "Name, valid email, and 8+ char password required")
    user = register(body.name, body.email, body.password, body.accountType)
    if not user:
        raise HTTPException(400, "Email already registered")
    return {
        "access_token": create_token(body.email),
        "token_type": "bearer",
        "user": {"name": user["name"], "email": user["email"], "accountType": user["accountType"]},
    }

@router.post("/login")
def login_user(body: LoginRequest):
    user = authenticate(body.email, body.password)
    if not user:
        raise HTTPException(401, "Invalid email or password")
    return {
        "access_token": create_token(body.email),
        "token_type": "bearer",
        "user": {"name": user["name"], "email": user["email"], "accountType": user["accountType"]},
    }


@router.put("/me")
def update_me(body: ProfileUpdate, user=Depends(get_current_user)):
    try:
        updated = update_profile(user["sub"], body.name, body.accountType)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not updated:
        raise HTTPException(404, "User not found")
    return {"user": updated}
