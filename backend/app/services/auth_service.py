from datetime import datetime, timedelta
from jose import jwt
import bcrypt
from app.config import settings

# In-memory store — replace with DB in Phase 2
users_db = {}

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expire}, settings.SECRET_KEY, settings.ALGORITHM)

def register(name: str, email: str, password: str, accountType: str):
    if email in users_db:
        return None
    users_db[email] = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "accountType": accountType,
    }
    return users_db[email]

def authenticate(email: str, password: str):
    user = users_db.get(email)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user