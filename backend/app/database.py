from pathlib import Path

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, MetaData, String, Table, Text,
    create_engine, func,
)
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

# Key/value store for system settings and the result of the last monitoring cycle.
app_settings = Table(
    "app_settings",
    metadata,
    Column("key", String(60), primary_key=True),
    Column("value", Text, nullable=False),
)

# One row per function per monitoring cycle (history of usage and estimated cost).
snapshots = Table(
    "snapshots",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("cycle_id", String(40), nullable=False, index=True),
    Column("taken_at", DateTime, nullable=False),
    Column("function_name", String(140), nullable=False),
    Column("memory", Integer, nullable=False),
    Column("architecture", String(10), nullable=False, default="x86_64"),
    Column("invocations", Integer, nullable=False, default=0),
    Column("avg_duration", Float, nullable=False, default=0.0),
    Column("max_memory_used", Integer),
    Column("cold_ratio", Float),
    Column("monthly_cost", Float, nullable=False, default=0.0),
    Column("source", String(10), nullable=False, default="aws"),
)

# Every change the system applied (or refused) on AWS, so it can be audited and rolled back.
actions = Table(
    "actions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("taken_at", DateTime, nullable=False),
    Column("function_name", String(140), nullable=False),
    Column("kind", String(12), nullable=False),  # memory | architecture
    Column("old_value", String(20), nullable=False),
    Column("new_value", String(20), nullable=False),
    Column("mode", String(10), nullable=False),  # manual | auto | rollback
    Column("status", String(10), nullable=False),  # applied | failed
    Column("detail", Text, nullable=False, default=""),
    Column("arch_at_action", String(10), nullable=False, default="x86_64"),
    Column("estimated_saving_pct", Float, nullable=False, default=0.0),
)

notifications = Table(
    "notifications",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime, nullable=False),
    Column("type", String(20), nullable=False),  # action | recommendation | alert | system
    Column("title", String(200), nullable=False),
    Column("body", Text, nullable=False, default=""),
    Column("severity", String(10), nullable=False, default="info"),
    Column("is_read", Boolean, nullable=False, default=False),
)


def init_db() -> None:
    metadata.create_all(engine)  # creates the tables only if they don't exist
