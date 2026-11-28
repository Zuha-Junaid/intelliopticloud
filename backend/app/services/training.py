"""Training of the memory model from REAL measurements.

Input is the CSV written by tools/collect_benchmark.py: one row per (workload profile,
memory size) with the durations and peak memory measured on AWS Lambda. For every workload
the best memory size is decided from its own measurements with one fixed rule:

  1. a size is feasible only if the function fits with headroom: max_used * 1.25 <= memory
  2. among feasible sizes, the duration must stay within 25% of the fastest feasible size
  3. the cheapest size (GB-seconds = memory/1024 * billed duration) is the label

The model learns to predict that label from what the monitoring module can observe on a
running function (memory, average duration, peak memory used, utilisation)."""
import csv
import json
from pathlib import Path

import numpy as np
from xgboost import XGBRegressor

SIZES = [128, 256, 512, 1024, 2048, 3008]
HEADROOM = 1.25
LATENCY_TOLERANCE = 1.25
FEATURES = ["Memory MB", "Avg Duration ms", "Peak Memory Used MB", "Memory Utilization %"]
FEATURE_SET = "real4"


def load_rows(csv_path) -> list:
    rows = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "profile": r["profile"],
                "memory_mb": int(float(r["memory_mb"])),
                "duration_ms": float(r["duration_ms"]),
                "billed_ms": float(r["billed_ms"]),
                "max_used_mb": float(r["max_used_mb"]),
            })
    return rows


def cost_units(row) -> float:
    return row["memory_mb"] / 1024.0 * row["billed_ms"]  # GB-milliseconds


def feasible(row) -> bool:
    return row["max_used_mb"] * HEADROOM <= row["memory_mb"]


def optimal_size(profile_rows):
    """Label rule applied to the measurements of ONE workload. None if nothing is feasible."""
    ok = [r for r in profile_rows if feasible(r)]
    if not ok:
        return None
    best = min(r["duration_ms"] for r in ok)
    ok = [r for r in ok if r["duration_ms"] <= LATENCY_TOLERANCE * best]
    return min(ok, key=lambda r: (cost_units(r), r["memory_mb"]))["memory_mb"]


def features(memory, duration, max_used) -> list:
    return [float(memory), float(duration), float(max_used), float(max_used) / float(memory) * 100.0]


def snap(values) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    s = np.asarray(SIZES)
    return s[np.abs(v[:, None] - s[None, :]).argmin(axis=1)]


def build_dataset(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r["profile"], []).append(r)
    X, y, prof, src = [], [], [], []
    for p, rs in groups.items():
        label = optimal_size(rs)
        if label is None:
            continue
        for r in rs:
            X.append(features(r["memory_mb"], r["duration_ms"], r["max_used_mb"]))
            y.append(label)
            prof.append(p)
            src.append(r)
    return np.array(X), np.array(y, dtype=float), prof, src, groups


def _fit(X, y, seed):
    m = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=seed, n_jobs=1)
    m.fit(X, y)
    return m


def evaluate(model, X, y, src, groups) -> dict:
    pred = snap(model.predict(X))
    exact = float(np.mean(pred == y)) * 100
    idx = {s: i for i, s in enumerate(SIZES)}
    within1 = float(np.mean([abs(idx[int(p)] - idx[int(t)]) <= 1 for p, t in zip(pred, y)])) * 100
    regrets, unsafe = [], 0
    for p, t, r in zip(pred, y, src):
        rs = groups[r["profile"]]
        at_p = next((x for x in rs if x["memory_mb"] == int(p)), None)
        at_t = next((x for x in rs if x["memory_mb"] == int(t)), None)
        if at_p is None or not feasible(at_p):
            unsafe += 1
            continue
        regrets.append(cost_units(at_p) / cost_units(at_t) - 1.0)
    return {
        "samples": int(len(y)),
        "exact_accuracy_pct": round(exact, 1),
        "within_one_step_pct": round(within1, 1),
        "mean_cost_regret_pct": round(float(np.mean(regrets)) * 100, 1) if regrets else None,
        "unsafe_predictions": int(unsafe),
        "mae_mb": round(float(np.mean(np.abs(pred - y))), 1),
    }


def train_from_csv(csv_path, model_path, meta_path, seed: int = 42, test_fraction: float = 0.3) -> dict:
    rows = load_rows(csv_path)
    X, y, prof, src, groups = build_dataset(rows)
    if len(set(prof)) < 6:
        raise ValueError("Need measurements from at least 6 workload profiles to train.")
    profiles = sorted(set(prof))
    rng = np.random.default_rng(seed)
    test_profiles = set(rng.permutation(profiles)[: max(1, int(len(profiles) * test_fraction))])
    is_test = np.array([p in test_profiles for p in prof])  # split by WORKLOAD, not by row
    held_out = _fit(X[~is_test], y[~is_test], seed)
    test_src = [s for s, t in zip(src, is_test) if t]
    metrics = evaluate(held_out, X[is_test], y[is_test], test_src, groups)
    test_pred = snap(held_out.predict(X[is_test]))
    detail = [{"profile": r["profile"], "memory_mb": r["memory_mb"], "peak_mb": r["max_used_mb"],
               "label": int(t), "predicted": int(p)} for r, t, p in zip(test_src, y[is_test], test_pred)]
    final = _fit(X, y, seed)  # deployed model uses all workloads
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    final.save_model(str(model_path))
    meta = {
        "feature_set": FEATURE_SET,
        "features": FEATURES,
        "version": "v3.0",
        "trainedOn": f"Measured AWS Lambda benchmark ({len(profiles)} workloads x {len(SIZES)} memory sizes)",
        "accuracy": metrics["exact_accuracy_pct"],
        "metrics_held_out": metrics,
        "train_workloads": len(profiles) - len(test_profiles),
        "test_workloads": len(test_profiles),
        "rows": len(rows),
        "label_distribution": {str(int(k)): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
        "held_out_detail": detail,
        "headroom": HEADROOM,
        "latency_tolerance": LATENCY_TOLERANCE,
        "seed": seed,
    }
    Path(meta_path).write_text(json.dumps(meta, indent=2))
    return meta
