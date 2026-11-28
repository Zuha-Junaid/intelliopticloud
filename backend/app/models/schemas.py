from pydantic import BaseModel
from typing import Optional, List

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    accountType: str = "Startup"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdate(BaseModel):
    name: str
    accountType: str
