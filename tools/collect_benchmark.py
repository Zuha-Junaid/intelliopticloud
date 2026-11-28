"""Collect REAL measurements for training the memory model.

For every workload profile (memory to hold x CPU work x waiting time) and every Lambda memory size,
the demo function ioc-demo-bench is invoked and the REPORT line of each invocation is read
(duration, billed duration, peak memory used). Cold starts are discarded.

Run in AWS CloudShell (about 10-20 minutes, free tier is enough):
    python3 collect_benchmark.py --output real_benchmark.csv
Then download real_benchmark.csv (Actions > Download file) and put it in backend/benchmark/.

More workloads (a bigger, more varied training set; about 20-30 minutes):
    python3 collect_benchmark.py --extra 60 --output real_benchmark_extra.csv
These are NEW workloads (different CPU work, waiting time and memory held), chosen with a fixed random
seed. The run can be repeated: pairs already in the output file are skipped, so a cut-off session
continues where it stopped. Merge and train on your computer:
    python tools/train_real.py backend/benchmark/real_benchmark.csv backend/benchmark/real_benchmark_extra.csv
"""
import argparse
import base64
import csv
import json
import random
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

SIZES = [128, 256, 512, 1024, 2048, 3008]
ALLOCS = [0, 60, 200, 400, 900, 1700]          # MB allocated on top of the runtime (about 35 MB)
CPUS = [0, 1_000_000, 5_000_000]                # loop iterations
SLEEPS = [0, 200]                               # ms of waiting
FUNCTION = "ioc-demo-bench"
WARM_NEEDED, MAX_TRIES = 3, 10
REPORT = re.compile(r"Duration: ([\d.]+) ms\s+Billed Duration: (\d+) ms\s+Memory Size: (\d+) MB\s+"
                    r"Max Memory Used: (\d+) MB(?:\s+Init Duration: ([\d.]+) ms)?")


def profiles():
    out = []
    for a in ALLOCS:
        for c in CPUS:
            for s in SLEEPS:
                out.append({"id": f"a{a}_c{c // 1_000_000}m_s{s}", "alloc_mb": a, "cpu_iters": c, "sleep_ms": s})
    return out


XALLOCS = [0, 30, 60, 120, 200, 300, 400, 600, 900, 1200, 1700]
XCPUS = [0, 200_000, 1_000_000, 2_000_000, 5_000_000, 8_000_000]
XSLEEPS = [0, 50, 200, 500, 1000]


def extra_profiles(n=60, seed=7):
    """n NEW workloads drawn at random (fixed seed) from a finer grid than the base 36."""
    base = {p["id"] for p in profiles()}
    grid = [(a, c, s) for a in XALLOCS for c in XCPUS for s in XSLEEPS]
    random.Random(seed).shuffle(grid)
    out = []
    for a, c, s in grid:
        pid = f"x_a{a}_c{c // 1000}k_s{s}"
        if pid in base:
            continue
        out.append({"id": pid, "alloc_mb": a, "cpu_iters": c, "sleep_ms": s})
        if len(out) >= n:
            break
    return out


def load_done(output):
    """(profile, memory) pairs already written to the output file, with their rows."""
    try:
        with open(output, newline="") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return [], set()
    return rows, {(r["profile"], int(float(r["memory_mb"]))) for r in rows}


def invoke_once(client, payload):
    r = client.invoke(FunctionName=FUNCTION, LogType="Tail", Payload=json.dumps(payload).encode())
    log = base64.b64decode(r.get("LogResult", "")).decode(errors="ignore")
    m = REPORT.search(log)
    if r.get("FunctionError") or not m:
        return None
    return {"duration": float(m.group(1)), "billed": int(m.group(2)), "max_used": int(m.group(4)),
            "cold": m.group(5) is not None}


def measure(client, prof, memory):
    """Mean warm duration / billed duration and peak memory for one profile at one memory size."""
    if prof["alloc_mb"] + 45 > memory * 0.98:
        return None                                   # cannot fit: skip instead of crashing the function
    payload = {k: prof[k] for k in ("alloc_mb", "cpu_iters", "sleep_ms")}
    warm = []
    for _ in range(MAX_TRIES):
        r = invoke_once(client, payload)
        if r is None:
            return None                               # error, out of memory or timeout
        if not r["cold"]:
            warm.append(r)
        if len(warm) >= WARM_NEEDED:
            break
    if len(warm) < WARM_NEEDED:
        return None
    return {"profile": prof["id"], "memory_mb": memory,
            "duration_ms": round(statistics.mean(w["duration"] for w in warm), 2),
            "billed_ms": round(statistics.mean(w["billed"] for w in warm), 2),
            "max_used_mb": max(w["max_used"] for w in warm)}


def run(client, output, workers=3, sizes=SIZES, profs=None, log=print, resume=False):
    profs = profs or profiles()
    rows, done = load_done(output) if resume else ([], set())
    rows = [dict(r) for r in rows]
    # Ascending memory held. Lambda reports "Max Memory Used" as the highest value of the whole execution
    # environment, and environments are reused between invocations. Running the small workloads first means
    # the highest value an environment has seen is always the peak of the workload being measured.
    all_profs = sorted(profs, key=lambda p: p["alloc_mb"])
    for mem in sizes:
        profs = [p for p in all_profs if (p["id"], mem) not in done]
        if not profs:
            log(f"memory {mem:>4} MB: already complete")
            continue
        client.update_function_configuration(FunctionName=FUNCTION, MemorySize=mem, Timeout=60)
        client.get_waiter("function_updated_v2").wait(FunctionName=FUNCTION)
        t0 = time.time()
        with ThreadPoolExecutor(workers) as ex:
            results = list(ex.map(lambda p: measure(client, p, mem), profs))
        got = [r for r in results if r]
        rows.extend(got)
        log(f"memory {mem:>4} MB: {len(got)}/{len(profs)} workloads measured in {time.time() - t0:.0f}s")
        with open(output, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["profile", "memory_mb", "duration_ms", "billed_ms", "max_used_mb"])
            w.writeheader()
            w.writerows(rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="real_benchmark.csv")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--extra", type=int, default=0, help="measure N NEW workloads instead of the base 36")
    a = ap.parse_args()
    import boto3
    client = boto3.client("lambda", region_name="us-east-1")
    if a.extra:
        rows = run(client, a.output, a.workers, profs=extra_profiles(a.extra), resume=True)
        floor = a.extra * 2
    else:
        rows = run(client, a.output, a.workers)
        floor = 100
    print(f"Wrote {len(rows)} rows to {a.output}")
    if len(rows) < floor:
        sys.exit("Fewer rows than expected: check that ioc-demo-bench exists and can be invoked.")


if __name__ == "__main__":
    main()
