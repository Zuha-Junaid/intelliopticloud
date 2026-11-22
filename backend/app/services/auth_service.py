import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings
from app.database import get_connection


def _pw(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes
    return password.encode()[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw(password), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_pw(plain), hashed.encode())


def create_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expire}, settings.SECRET_KEY, settings.ALGORITHM)


def register(name: str, email: str, password: str, accountType: str):
    email = email.strip().lower()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, account_type) VALUES (?, ?, ?, ?)",
            (name.strip(), email, hash_password(password), accountType),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return None  # email already registered
    finally:
        conn.close()
    return {"name": name.strip(), "email": email, "accountType": accountType}


def authenticate(email: str, password: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    finally:
        conn.close()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return {"name": row["name"], "email": row["email"], "accountType": row["account_type"]}