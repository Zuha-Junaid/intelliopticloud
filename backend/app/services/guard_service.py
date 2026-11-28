"""Closed loop: after a change has enough new invocations, the REAL billed cost and duration are
compared with the period before it. A change that made things worse is reported and, only in
the 'auto' autonomy level, rolled back automatically.

Why this exists: the model predicts from one observation of a function, so it can be wrong
(see cross_validation in the model report). The guard limits what a wrong prediction can cost."""
from sqlalchemy import select

from app.config import settings
from app.database import actions, engine
from app.services import store
from app.services.apply_service import ApplyError, rollback
from app.services.savings_service import verify

MAX_COST_INCREASE_PCT = 5.0   # the change must not make an invocation more than 5% more expensive
MAX_SLOWDOWN_PCT = 25.0       # nor more than 25% slower (the same tolerance the label rule uses)
LOOKBACK = 20                 # recent changes that are still checked


def evaluate(result: dict) -> dict:
    """result: one item returned by savings_service.verify(). Adds a verdict."""
    if result["status"] != "verified":
        return {**result, "verdict": "waiting", "reasons": []}
    reasons = []
    if result["changePct"] > MAX_COST_INCREASE_PCT:
        reasons.append(f"cost per invocation rose by {result['changePct']}%")
    before, after = result["avgBilledBeforeMs"], result["avgBilledAfterMs"]
    slowdown = (after - before) / before * 100 if before else 0.0
    if slowdown > MAX_SLOWDOWN_PCT:
        reasons.append(f"average billed duration is {round(slowdown, 1)}% slower")
    return {**result, "verdict": "regression" if reasons else "ok", "reasons": reasons}


def _already_reverted(row) -> bool:
    with engine.connect() as c:
        later = c.execute(select(actions.c.id).where(
            actions.c.function_name == row["function_name"], actions.c.kind == row["kind"],
            actions.c.mode == "rollback", actions.c.status == "applied",
            actions.c.taken_at > row["taken_at"]).limit(1)).first()
    return later is not None


def check_recent_changes(functions: list, autonomy: str) -> dict:
    """Called once per monitoring cycle. Every change is judged once, when its result is verified."""
    done = set(store.kv_get("guard_done", []) or [])
    summary = {"checked": 0, "ok": 0, "flagged": 0, "rolledBack": 0}
    monthly = {f["name"]: f["invocations"] for f in functions}
    with engine.connect() as c:
        rows = c.execute(select(actions).where(actions.c.status == "applied", actions.c.mode != "rollback")
                         .order_by(actions.c.id.desc()).limit(LOOKBACK)).mappings().all()
    for row in rows:
        row = dict(row)
        if row["id"] in done:
            continue
        if _already_reverted(row):
            done.add(row["id"])
            continue
        res = evaluate(verify(row, monthly.get(row["function_name"], 0)))
        if res["verdict"] == "waiting":
            continue
        done.add(row["id"])
        summary["checked"] += 1
        name = row["function_name"]
        if res["verdict"] == "ok":
            summary["ok"] += 1
            store.notify("action", f"Change verified: {name}",
                         f"Cost per invocation changed by {res['changePct']}% "
                         f"({res['costPerInvocationBefore']} to {res['costPerInvocationAfter']} PKR).",
                         "success", dedupe_hours=0)
            continue
        summary["flagged"] += 1
        why = " and ".join(res["reasons"])
        can_revert = autonomy == "auto" and settings.APPLY_ENABLED and name.startswith(settings.APPLY_ALLOWED_PREFIX)
        if can_revert:
            try:
                rollback(row["id"])
                summary["rolledBack"] += 1
                store.notify("action", f"Automatic rollback: {name}",
                             f"The change ({row['old_value']} to {row['new_value']}) was reverted because {why}.",
                             "warning")
                continue
            except ApplyError as exc:
                why += f" (automatic rollback failed: {exc.message})"
        store.notify("action", f"Change made things worse: {name}",
                     f"Measured result: {why}. Open Optimization and roll the change back.", "warning")
    store.kv_set("guard_done", sorted(done)[-200:])
    return summary
