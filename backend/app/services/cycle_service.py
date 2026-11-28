"""One monitoring cycle: read AWS, store a history snapshot, produce recommendations and
notifications and, only when the autonomy level is 'auto', apply safe memory changes."""
import time
import uuid
from datetime import timedelta

from sqlalchemy import insert, select

from app.config import settings
from app.database import engine, snapshots
from app.services import store
from app.services.apply_service import ApplyError, apply_memory
from app.services.cloudwatch_service import get_inventory
from app.services.optimizer_service import (
    predict_memory, recommend_architecture, recommend_spot,
)

MAX_AUTO_CHANGES_PER_CYCLE = 3
SPIKE_FACTOR = 1.5
SPIKE_MIN_INCREASE = 100


def build_recommendations(functions: list) -> list:
    out = []
    for fn in functions:
        out.append({
            "function": fn["name"],
            "runtime": fn["runtime"],
            "architecture": fn["architecture"],
            "measured": fn.get("maxMemoryUsed") is not None,
            "memory": predict_memory(fn["memory"], fn["invocations"], fn["avgDuration"], fn.get("maxMemoryUsed")),
            "spot": recommend_spot(fn["invocations"], fn["avgDuration"]),
            "arch": recommend_architecture(fn["runtime"], fn["architecture"], fn["invocations"]),
        })
    return out


def _previous_invocations(name: str):
    with engine.connect() as c:
        row = c.execute(select(snapshots.c.invocations).where(snapshots.c.function_name == name)
                        .order_by(snapshots.c.id.desc()).limit(1)).first()
    return row[0] if row else None


def run_cycle(trigger: str = "manual") -> dict:
    started = time.time()
    cfg = store.get_settings()
    inv = get_inventory(force=True)
    fns = inv["functions"]
    cycle_id = uuid.uuid4().hex[:12]
    now = store.utcnow()
    summary = {"at": now.isoformat() + "Z", "trigger": trigger, "source": inv["source"], "warning": inv["warning"],
               "functions": len(fns), "measured": sum(1 for f in fns if f.get("maxMemoryUsed") is not None),
               "recommendations": 0, "applied": 0, "skipped": 0, "errors": []}

    # 1. spike alerts (compare with the previous snapshot BEFORE storing the new one)
    if cfg["notify_alerts"] and inv["source"] == "aws":
        for f in fns:
            prev = _previous_invocations(f["name"])
            if prev is not None and f["invocations"] >= prev * SPIKE_FACTOR and f["invocations"] - prev >= SPIKE_MIN_INCREASE:
                store.notify("alert", f"Usage increase: {f['name']}",
                             f"Invocations in the last 30 days rose from {prev} to {f['invocations']} since the previous check.",
                             "warning", dedupe_hours=24)

    # 2. history (only real AWS data is stored as history)
    if inv["source"] == "aws" and fns:
        with engine.begin() as c:
            c.execute(insert(snapshots), [{
                "cycle_id": cycle_id, "taken_at": now, "function_name": f["name"], "memory": f["memory"],
                "architecture": f["architecture"], "invocations": f["invocations"], "avg_duration": f["avgDuration"],
                "max_memory_used": f.get("maxMemoryUsed"), "cold_ratio": f.get("coldStartRatio"),
                "monthly_cost": f["monthlyCost"], "source": "aws"} for f in fns])

    # 3. recommendations, notifications and (optional) automatic changes
    recs = build_recommendations(fns)
    auto_ok = cfg["autonomy"] == "auto" and settings.APPLY_ENABLED and inv["source"] == "aws"
    auto_done = 0
    for r in recs:
        m = r["memory"]
        if m["saves"]:
            summary["recommendations"] += 1
            if cfg["notify_alerts"] and inv["source"] == "aws":
                store.notify("recommendation", f"Recommendation: {r['function']} {m['current']} MB to {m['optimal']} MB",
                             f"Predicted memory {m['optimal']} MB (confidence {m['confidence']}%, basis: {m['basis']}).",
                             "info", dedupe_hours=24)
            eligible = (auto_ok and r["measured"] and m["confidence"] >= cfg["min_confidence"]
                        and r["function"].startswith(settings.APPLY_ALLOWED_PREFIX)
                        and auto_done < MAX_AUTO_CHANGES_PER_CYCLE)
            if eligible:
                try:
                    apply_memory(r["function"], m["optimal"], mode="auto", saving_pct=m["reduction_pct"])
                    summary["applied"] += 1
                    auto_done += 1
                except ApplyError as exc:
                    summary["errors"].append(f"{r['function']}: {exc.message}")
            else:
                summary["skipped"] += 1

    # 4. weekly summary
    if cfg["notify_summary"] and inv["source"] == "aws":
        total = round(sum(f["monthlyCost"] for f in fns), 2)
        store.notify("system", "Weekly summary",
                     f"{len(fns)} functions monitored, estimated monthly cost PKR {total}, "
                     f"{summary['recommendations']} recommendation(s) open.", "info", dedupe_hours=24 * 7)

    summary["durationMs"] = int((time.time() - started) * 1000)
    store.kv_set("last_cycle", summary)
    return summary


def history(days: int = 30) -> list:
    """Total estimated monthly cost per cycle (real history of the connected account)."""
    since = store.utcnow() - timedelta(days=days)
    with engine.connect() as c:
        rows = c.execute(select(snapshots.c.cycle_id, snapshots.c.taken_at, snapshots.c.monthly_cost)
                         .where(snapshots.c.taken_at >= since).order_by(snapshots.c.taken_at)).all()
    cycles = {}
    for cid, at, cost in rows:
        entry = cycles.setdefault(cid, {"at": at, "cost": 0.0})
        entry["cost"] += cost
    return [{"at": v["at"].isoformat() + "Z", "cost": round(v["cost"], 2)} for v in cycles.values()]
