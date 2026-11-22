from pathlib import Path

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, func
from sqlalchemy.engine import URL

from app.config import settings

SQLITE_FILE = Path(__file__).resolve().parent.parent / "data" / "intelliopticloud.db"


def _database_url():
    url = settings.DATABASE_URL.strip()
    if not url:  # local development: SQLite file
        SQLITE_FILE.parent.mkdir(parents=True, exist_ok=True)
        return URL.create("sqlite", database=str(SQLITE_FILE))
    # Always use the psycopg2 driver we installed. SQLAlchemy's default
    # Postgres driver differs between versions, which caused this error.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


engine = create_engine(_database_url(), pool_pre_ping=True, pool_recycle=300)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(120), nullable=False),
    Column("email", String(255), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("account_type", String(40), nullable=False, default="Startup"),
    Column("created_at", DateTime, server_default=func.now()),
)


def init_db() -> None:
    metadata.create_all(engine)  # creates the table only if it doesn't exist