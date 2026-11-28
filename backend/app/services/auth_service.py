from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import engine, users


def _pw(password: str) -> bytes:
    return password.encode()[:72]  # bcrypt only uses the first 72 bytes


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw(password), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_pw(plain), hashed.encode())


def create_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expire}, settings.SECRET_KEY, settings.ALGORITHM)


def register(name: str, email: str, password: str, accountType: str):
    name, email = name.strip(), email.strip().lower()
    try:
        with engine.begin() as conn:
            conn.execute(
                insert(users).values(
                    name=name,
                    email=email,
                    password_hash=hash_password(password),
                    account_type=accountType,
                )
            )
    except IntegrityError:
        return None  # email already registered
    return {"name": name, "email": email, "accountType": accountType}


def authenticate(email: str, password: str):
    with engine.connect() as conn:
        row = conn.execute(
            select(users).where(users.c.email == email.strip().lower())
        ).mappings().first()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return {"name": row["name"], "email": row["email"], "accountType": row["account_type"]}

ACCOUNT_TYPES = ("Startup", "SME", "Enterprise")


def update_profile(email: str, name: str, account_type: str):
    """Change the display name and account type of a user. Returns the user or None."""
    from sqlalchemy import update
    name = name.strip()
    if not name or account_type not in ACCOUNT_TYPES:
        raise ValueError("Name is required and account type must be Startup, SME or Enterprise")
    with engine.begin() as conn:
        res = conn.execute(update(users).where(users.c.email == email.strip().lower())
                           .values(name=name, account_type=account_type))
    if res.rowcount == 0:
        return None
    return {"name": name, "email": email.strip().lower(), "accountType": account_type}
