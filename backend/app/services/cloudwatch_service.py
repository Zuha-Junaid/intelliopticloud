import re
import time
from datetime import datetime, timedelta, timezone

import boto3

from app.config import settings

# Lambda writes one REPORT line per invocation to CloudWatch Logs. It holds the real
# billed duration, configured memory, peak memory used and (for cold starts) Init Duration.
REPORT_RE = re.compile(
    r"Duration: ([\d.]+) ms\s+Billed Duration: (\d+) ms\s+Memory Size: (\d+) MB\s+"
    r"Max Memory Used: (\d+) MB(?:\s+Init Duration: ([\d.]+) ms)?"
)
ARM_RUNTIME_PREFIXES = ("python", "nodejs", "java", "dotnet", "ruby", "provided.al")
CACHE_SECONDS = 20
_cache = {"at": 0.0, "value": None}


def _creds():
    return dict(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def get_lambda_client():
    return boto3.client("lambda", **_creds())


def get_cloudwatch_client():
    return boto3.client("cloudwatch", **_creds())


def get_logs_client():
    return boto3.client("logs", **_creds())


def aws_configured() -> bool:
    return bool(settings.AWS_ACCESS_KEY_ID)


def clear_cache() -> None:
    _cache["at"] = 0.0
    _cache["value"] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_metric(fn_name: str, metric: str) -> float:
    """30-day Sum (Invocations) or Average (Duration) from CloudWatch. Raises on AWS errors."""
    cw = get_cloudwatch_client()
    stat = "Sum" if metric == "Invocations" else "Average"
    resp = cw.get_metric_statistics(
        Namespace="AWS/Lambda",
        MetricName=metric,
        Dimensions=[{"Name": "FunctionName", "Value": fn_name}],
        StartTime=_utcnow() - timedelta(days=30),
        EndTime=_utcnow(),
        Period=2592000,
        Statistics=[stat],
    )
    pts = resp.get("Datapoints", [])
    if not pts:
        return 0.0
    return round(pts[0][stat], 2)


def fetch_reports(fn_name: str, start=None, end=None, days: int = 7, max_events: int = 1500) -> list:
    """Read the per-invocation REPORT lines of a function from CloudWatch Logs.
    Returns a list of dicts: ts (ms), duration, billed, memory, max_used, cold."""
    end = end or _utcnow()
    start = start or (end - timedelta(days=days))
    logs = get_logs_client()
    out, token = [], None
    while len(out) < max_events:
        kwargs = dict(
            logGroupName=f"/aws/lambda/{fn_name}",
            filterPattern='"REPORT RequestId"',
            startTime=int(start.replace(tzinfo=timezone.utc).timestamp() * 1000),
            endTime=int(end.replace(tzinfo=timezone.utc).timestamp() * 1000),
        )
        if token:
            kwargs["nextToken"] = token
        try:
            resp = logs.filter_log_events(**kwargs)
        except Exception as exc:  # the log group does not exist until the first invocation
            if "ResourceNotFound" in type(exc).__name__ or "ResourceNotFound" in str(exc):
                return out
            raise
        for ev in resp.get("events", []):
            m = REPORT_RE.search(ev.get("message", ""))
            if m:
                out.append({
                    "ts": ev["timestamp"],
                    "duration": float(m.group(1)),
                    "billed": int(m.group(2)),
                    "memory": int(m.group(3)),
                    "max_used": int(m.group(4)),
                    "cold": m.group(5) is not None,
                })
        token = resp.get("nextToken")
        if not token:
            break
    return out


def calculate_cost(memory_mb: int, invocations: int, avg_duration_ms: float = 100.0,
                   arch: str = "x86_64") -> float:
    """Estimated monthly cost in PKR at AWS list prices (before the free tier is applied)."""
    gb = memory_mb / 1024
    price = settings.PRICE_GBS_ARM if arch == "arm64" else settings.PRICE_GBS_X86
    compute = invocations * gb * (avg_duration_ms / 1000.0) * price
    requests = invocations * settings.PRICE_PER_REQUEST
    return round((compute + requests) * settings.PKR_USD_RATE, 2)


def supports_arm(runtime: str) -> bool:
    return str(runtime or "").lower().startswith(ARM_RUNTIME_PREFIXES)


def _read_function(fn: dict) -> dict:
    name = fn["FunctionName"]
    inv = int(get_metric(name, "Invocations"))
    dur = get_metric(name, "Duration")
    reports = fetch_reports(name, days=7)
    arch = (fn.get("Architectures") or ["x86_64"])[0]
    cold = sum(1 for r in reports if r["cold"])
    return {
        "id": fn["FunctionArn"],
        "name": name,
        "region": settings.AWS_REGION,
        "runtime": fn.get("Runtime", "container image"),
        "memory": fn["MemorySize"],
        "architecture": arch,
        "invocations": inv,
        "avgDuration": dur,
        "maxMemoryUsed": max((r["max_used"] for r in reports), default=None),
        "coldStartRatio": round(cold / len(reports), 3) if reports else None,
        "samples": len(reports),
        "monthlyCost": calculate_cost(fn["MemorySize"], inv, dur, arch),
        "status": "active" if inv > 0 else "idle",
    }


def get_inventory(force: bool = False) -> dict:
    """Return {"functions": [...], "source": "aws"|"sample", "warning": None|str, "readAt": iso}.
    Without credentials the built-in sample data is used. If AWS fails while credentials are
    set, sample data is returned together with a warning, never silently."""
    if not force and _cache["value"] and time.time() - _cache["at"] < CACHE_SECONDS:
        return _cache["value"]
    warning = None
    if aws_configured():
        try:
            client = get_lambda_client()
            fns, marker = [], None
            while True:
                resp = client.list_functions(**({"Marker": marker} if marker else {}))
                fns.extend(resp.get("Functions", []))
                marker = resp.get("NextMarker")
                if not marker:
                    break
            result = {"functions": [_read_function(f) for f in fns], "source": "aws", "warning": None}
        except Exception as exc:
            warning = f"Could not read from AWS ({type(exc).__name__}). Showing sample data."
            result = {"functions": get_mock_functions(), "source": "sample", "warning": warning}
    else:
        result = {"functions": get_mock_functions(), "source": "sample",
                  "warning": "AWS credentials are not set. Showing sample data."}
    result["readAt"] = _utcnow().isoformat() + "Z"
    _cache["at"], _cache["value"] = time.time(), result
    return result


def get_functions() -> list:
    return get_inventory()["functions"]


def get_mock_functions() -> list:
    """Built-in SAMPLE inventory used only when AWS is not connected (development and tests)."""
    rows = [
        ("api-auth-handler", "Node.js 20.x", 512, 142000, 84, 160),
        ("image-processor", "Python 3.12", 1024, 38000, 612, 470),
        ("notification-service", "Node.js 20.x", 256, 95000, 45, 60),
        ("data-pipeline", "Python 3.12", 2048, 12000, 1840, 1500),
        ("report-generator", "Node.js 20.x", 768, 5400, 320, 300),
    ]
    out = []
    for i, (name, runtime, mem, inv, dur, used) in enumerate(rows, 1):
        out.append({
            "id": f"fn-{i:03d}", "name": name, "region": "us-east-1", "runtime": runtime,
            "memory": mem, "architecture": "x86_64", "invocations": inv, "avgDuration": dur,
            "maxMemoryUsed": used, "coldStartRatio": 0.02, "samples": 0,
            "monthlyCost": calculate_cost(mem, inv, dur), "status": "active",
        })
    return out
