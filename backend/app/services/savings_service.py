"""Verified savings: compares the REAL billed cost per invocation before and after each applied
change, using the REPORT lines in CloudWatch Logs (billed duration x configured memory)."""
from datetime import timedelta

from sqlalchemy import select

from app.config import settings
from app.database import actions, engine
from app.services import store
from app.services.cloudwatch_service import fetch_reports, get_inventory

MIN_EVENTS = 20  # invocations needed on each side before a result is shown


def _price(arch: str) -> float:
    return settings.PRICE_GBS_ARM if arch == "arm64" else settings.PRICE_GBS_X86


def event_cost_pkr(billed_ms: float, memory_mb: float, arch: str) -> float:
    usd = (billed_ms / 1000.0) * (memory_mb / 1024.0) * _price(arch) + settings.PRICE_PER_REQUEST
    return usd * settings.PKR_USD_RATE


def _mean_cost(events, arch):
    return sum(event_cost_pkr(e["billed"], e["memory"], arch) for e in events) / len(events)


def _neighbours(action: dict):
    """Previous and next applied change on the same function, so that each measurement covers
    only the period in which that change was the latest one."""
    with engine.connect() as c:
        prev = c.execute(select(actions.c.taken_at).where(
            actions.c.function_name == action["function_name"], actions.c.status == "applied",
            actions.c.taken_at < action["taken_at"]).order_by(actions.c.taken_at.desc()).limit(1)).first()
        nxt = c.execute(select(actions.c.taken_at).where(
            actions.c.function_name == action["function_name"], actions.c.status == "applied",
            actions.c.taken_at > action["taken_at"]).order_by(actions.c.taken_at.asc()).limit(1)).first()
    return (prev[0] if prev else None), (nxt[0] if nxt else None)


def verify(action: dict, monthly_invocations: int) -> dict:
    """action: a row of the actions table (mapping). Returns the measured before/after result."""
    fn, t = action["function_name"], action["taken_at"]
    prev_t, next_t = _neighbours(action)
    start = max(t - timedelta(days=14), prev_t) if prev_t else t - timedelta(days=14)
    end = next_t if next_t else store.utcnow()
    before = fetch_reports(fn, start=start, end=t - timedelta(milliseconds=1))
    after = fetch_reports(fn, start=t, end=end)
    base = {"actionId": action["id"], "function": fn, "kind": action["kind"], "oldValue": action["old_value"],
            "newValue": action["new_value"], "takenAt": t.isoformat() + "Z", "mode": action["mode"],
            "eventsBefore": len(before), "eventsAfter": len(after)}
    if len(before) < MIN_EVENTS or len(after) < MIN_EVENTS:
        return {**base, "status": "waiting",
                "message": f"Needs at least {MIN_EVENTS} invocations before and after the change."}
    arch_before = action["old_value"] if action["kind"] == "architecture" else action["arch_at_action"]
    arch_after = action["new_value"] if action["kind"] == "architecture" else action["arch_at_action"]
    c_before, c_after = _mean_cost(before, arch_before), _mean_cost(after, arch_after)
    d_before = sum(e["billed"] for e in before) / len(before)
    d_after = sum(e["billed"] for e in after) / len(after)
    return {**base, "status": "verified",
            "costPerInvocationBefore": round(c_before, 6), "costPerInvocationAfter": round(c_after, 6),
            "changePct": round((c_after - c_before) / c_before * 100, 1) if c_before else 0.0,
            "avgBilledBeforeMs": round(d_before, 1), "avgBilledAfterMs": round(d_after, 1),
            "monthlySavingPkr": round((c_before - c_after) * monthly_invocations, 2)}


def verified_savings(limit: int = 20) -> dict:
    inv_all = get_inventory()
    if inv_all["source"] != "aws":  # nothing can be verified without the real AWS account
        return {"items": [], "totalMonthlySavingPkr": 0}
    with engine.connect() as c:
        rows = c.execute(select(actions).where(actions.c.status == "applied", actions.c.mode != "rollback")
                         .order_by(actions.c.id.desc()).limit(limit)).mappings().all()
    inv = {f["name"]: f["invocations"] for f in inv_all["functions"]}
    results = [verify(dict(r), inv.get(r["function_name"], 0)) for r in rows]
    # one result per function and kind: the most recent
    seen, latest = set(), []
    for r in results:
        key = (r["function"], r["kind"])
        if key not in seen:
            seen.add(key)
            latest.append(r)
    total = round(sum(r.get("monthlySavingPkr", 0) for r in latest if r["status"] == "verified" and r["monthlySavingPkr"] > 0), 2)
    return {"items": results, "totalMonthlySavingPkr": total}
