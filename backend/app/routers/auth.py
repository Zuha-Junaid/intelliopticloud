from fastapi import APIRouter, HTTPException
from app.models.schemas import RegisterRequest, LoginRequest
from app.services.auth_service import register, authenticate, create_token

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