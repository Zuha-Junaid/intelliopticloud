"""Small helpers for the key/value settings table, notifications and the action log."""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select, update

from app.database import actions, app_settings, engine, notifications

DEFAULT_SETTINGS = {
    "autonomy": "approve",        # monitor | approve | auto
    "min_confidence": 85,         # minimum model confidence for automatic changes
    "notify_actions": True,
    "notify_alerts": True,        # recommendations and spikes
    "notify_summary": True,       # weekly summary
}
AUTONOMY_LEVELS = ("monitor", "approve", "auto")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- key/value ----------
def kv_get(key, default=None):
    with engine.connect() as c:
        row = c.execute(select(app_settings.c.value).where(app_settings.c.key == key)).first()
    return json.loads(row[0]) if row else default


def kv_set(key, value) -> None:
    text = json.dumps(value)
    with engine.begin() as c:
        exists = c.execute(select(app_settings.c.key).where(app_settings.c.key == key)).first()
        if exists:
            c.execute(update(app_settings).where(app_settings.c.key == key).values(value=text))
        else:
            c.execute(insert(app_settings).values(key=key, value=text))


# ---------- user-editable settings ----------
def get_settings() -> dict:
    stored = kv_get("settings", {}) or {}
    return {**DEFAULT_SETTINGS, **{k: v for k, v in stored.items() if k in DEFAULT_SETTINGS}}


def update_settings(changes: dict) -> dict:
    """Validate and save. Raises ValueError for an invalid value."""
    current = get_settings()
    for key, value in changes.items():
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"Unknown setting: {key}")
        if key == "autonomy" and value not in AUTONOMY_LEVELS:
            raise ValueError("autonomy must be monitor, approve or auto")
        if key == "min_confidence":
            if isinstance(value, bool) or not isinstance(value, int) or not 50 <= value <= 100:
                raise ValueError("min_confidence must be a whole number from 50 to 100")
        if key.startswith("notify_") and not isinstance(value, bool):
            raise ValueError(f"{key} must be true or false")
        current[key] = value
    kv_set("settings", current)
    return current


# ---------- notifications ----------
def notify(kind: str, title: str, body: str, severity: str = "info", dedupe_hours: int = 0) -> bool:
    """Create a notification. With dedupe_hours, an identical title within that period is skipped."""
    now = utcnow()
    with engine.begin() as c:
        if dedupe_hours:
            since = now - timedelta(hours=dedupe_hours)
            dup = c.execute(select(notifications.c.id).where(
                notifications.c.title == title, notifications.c.created_at >= since)).first()
            if dup:
                return False
        c.execute(insert(notifications).values(
            created_at=now, type=kind, title=title[:200], body=body, severity=severity, is_read=False))
    return True


def list_notifications(limit: int = 50) -> list:
    with engine.connect() as c:
        rows = c.execute(select(notifications).order_by(notifications.c.id.desc()).limit(limit)).mappings().all()
    return [{"id": r["id"], "type": r["type"], "title": r["title"], "desc": r["body"],
             "severity": r["severity"], "read": bool(r["is_read"]),
             "createdAt": r["created_at"].isoformat() + "Z"} for r in rows]


def mark_read(nid: int) -> bool:
    with engine.begin() as c:
        res = c.execute(update(notifications).where(notifications.c.id == nid).values(is_read=True))
    return res.rowcount > 0


def mark_all_read() -> None:
    with engine.begin() as c:
        c.execute(update(notifications).values(is_read=True))


# ---------- action log ----------
def log_action(function_name, kind, old, new, mode, status, detail, arch, saving_pct=0.0) -> int:
    with engine.begin() as c:
        res = c.execute(insert(actions).values(
            taken_at=utcnow(), function_name=function_name, kind=kind, old_value=str(old),
            new_value=str(new), mode=mode, status=status, detail=detail[:1000],
            arch_at_action=arch, estimated_saving_pct=saving_pct))
        return res.inserted_primary_key[0]


def list_actions(limit: int = 50) -> list:
    with engine.connect() as c:
        rows = c.execute(select(actions).order_by(actions.c.id.desc()).limit(limit)).mappings().all()
    return [{"id": r["id"], "takenAt": r["taken_at"].isoformat() + "Z", "function": r["function_name"],
             "kind": r["kind"], "oldValue": r["old_value"], "newValue": r["new_value"],
             "mode": r["mode"], "status": r["status"], "detail": r["detail"],
             "estimatedSavingPct": r["estimated_saving_pct"]} for r in rows]


def get_action(action_id: int):
    with engine.connect() as c:
        return c.execute(select(actions).where(actions.c.id == action_id)).mappings().first()
