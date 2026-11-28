"""Invoke a demo function many times so that CloudWatch gets real usage to measure.
Run in CloudShell:   python3 generate_load.py --function ioc-demo-api --count 150"""
import argparse
import base64
import json
import re
from concurrent.futures import ThreadPoolExecutor

import boto3

PAYLOADS = {
    "ioc-demo-api": {"sleep_ms": 180},                       # waits for an external service
    "ioc-demo-compute": {"cpu_iters": 3_000_000},             # CPU work
    "ioc-demo-heavy": {"alloc_mb": 700, "sleep_ms": 50},     # needs a lot of memory
}
BILLED = re.compile(r"Billed Duration: (\d+) ms")


def one(client, name, payload):
    r = client.invoke(FunctionName=name, LogType="Tail", Payload=json.dumps(payload).encode())
    log = base64.b64decode(r.get("LogResult", "")).decode(errors="ignore")
    m = BILLED.search(log)
    return (int(m.group(1)) if m else None), bool(r.get("FunctionError"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--function", required=True)
    ap.add_argument("--count", type=int, default=150)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--payload", help="JSON event, overrides the default for this function")
    a = ap.parse_args()
    payload = json.loads(a.payload) if a.payload else PAYLOADS.get(a.function, {})
    client = boto3.client("lambda", region_name="us-east-1")
    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(lambda _: one(client, a.function, payload), range(a.count)))
    billed = [b for b, err in res if b is not None and not err]
    print(f"{len(billed)}/{a.count} invocations succeeded; average billed duration "
          f"{sum(billed) / max(1, len(billed)):.1f} ms")


if __name__ == "__main__":
    main()
