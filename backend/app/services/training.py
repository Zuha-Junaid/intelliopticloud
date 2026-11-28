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


def merge_csvs(paths, output) -> int:
    """Combine several benchmark files into one (the last value wins for the same workload and size)."""
    merged = {}
    for path in paths:
        for r in load_rows(path):
            merged[(r["profile"], r["memory_mb"])] = r
    rows = sorted(merged.values(), key=lambda r: (r["profile"], r["memory_mb"]))
    with open(output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["profile", "memory_mb", "duration_ms", "billed_ms", "max_used_mb"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})
    return len(rows)


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


def harmonise_peaks(rows) -> list:
    """The peak memory of a workload does not depend on the memory it is configured with, but Lambda's
    "Max Memory Used" is the highest value of a whole (reused) execution environment, so a measurement can
    only be too HIGH, never too low. The lowest value measured for a workload at any size is therefore the
    best estimate of its real peak, and is used for all of its rows."""
    low = {}
    for r in rows:
        low[r["profile"]] = min(low.get(r["profile"], r["max_used_mb"]), r["max_used_mb"])
    return [{**r, "max_used_mb": low[r["profile"]]} for r in rows]


def build_dataset(rows):
    groups = {}
    for r in harmonise_peaks(rows):
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
    # Shallow trees: with a few dozen workloads, deep trees memorise single workloads. The depth was
    # chosen by workload-grouped cross-validation (see cross_validate), not on the held-out split.
    m = XGBRegressor(n_estimators=60, max_depth=2, learning_rate=0.1, random_state=seed, n_jobs=1)
    m.fit(X, y)
    return m


def min_safe_size(max_used) -> int:
    """Smallest size that keeps the headroom above the measured peak memory."""
    need = float(max_used) * HEADROOM
    return next((s for s in SIZES if s >= need), SIZES[-1])


def _clamp_safe(pred, X) -> np.ndarray:
    """What the deployed backend does: never go below the minimum safe size."""
    return np.array([max(int(p), min_safe_size(x[2])) for p, x in zip(pred, X)])


def _downsize_outcome(pred, src, groups) -> dict:
    """Judges only the recommendations the app can act on: those that LOWER the memory.
    Each is scored against what was measured for that workload at the recommended size."""
    n = cut = slow = 0
    cost, dur = [], []
    for p, r in zip(pred, src):
        if int(p) >= r["memory_mb"]:
            continue
        at_p = next((x for x in groups[r["profile"]] if x["memory_mb"] == int(p)), None)
        if at_p is None:
            continue  # that size was not measured for this workload
        n += 1
        c = cost_units(at_p) / cost_units(r) - 1.0
        d = at_p["duration_ms"] / r["duration_ms"] - 1.0
        cost.append(c)
        dur.append(d)
        cut += c < -0.02
        slow += d > LATENCY_TOLERANCE - 1.0
    if n == 0:
        return {"downsizes_scored": 0}
    return {"downsizes_scored": n,
            "cut_cost_pct": round(cut / n * 100, 1),
            "slower_than_25pct_pct": round(slow / n * 100, 1),
            "mean_cost_change_pct": round(float(np.mean(cost)) * 100, 1),
            "median_duration_change_pct": round(float(np.median(dur)) * 100, 1)}


def cross_validate(X, y, prof, src, groups, seed: int = 42, k: int = 6, reps: int = 3) -> dict:
    """Repeated k-fold cross-validation grouped by WORKLOAD (all sizes of a workload stay together),
    so every workload is predicted by a model that never saw it. Much steadier than one small
    held-out split. The model is compared with two trivial baselines."""
    profiles = sorted(set(prof))
    prof_arr = np.array(prof)
    k = max(2, min(k, len(profiles)))
    idx = {s: i for i, s in enumerate(SIZES)}
    methods = {"model": [], "baseline_min_safe_size": [], "baseline_always_2048": []}
    exact, within1 = [], []
    for rep in range(reps):
        rng = np.random.default_rng(seed + rep)
        folds = np.array_split(rng.permutation(profiles), k)
        pred = {m: np.zeros(len(y)) for m in methods}
        for fold in folds:
            te = np.isin(prof_arr, fold)
            model = _fit(X[~te], y[~te], seed)
            pred["model"][te] = _clamp_safe(snap(model.predict(X[te])), X[te])
            pred["baseline_min_safe_size"][te] = [min_safe_size(x[2]) for x in X[te]]
            pred["baseline_always_2048"][te] = _clamp_safe(np.full(int(te.sum()), 2048), X[te])
        exact.append(float(np.mean(pred["model"] == y)) * 100)
        within1.append(float(np.mean([abs(idx[int(a)] - idx[int(b)]) <= 1 for a, b in zip(pred["model"], y)])) * 100)
        for m in methods:
            methods[m].append(_downsize_outcome(pred[m], src, groups))
    out = {"folds": k, "repeats": reps, "exact_accuracy_pct": round(float(np.mean(exact)), 1),
           "within_one_step_pct": round(float(np.mean(within1)), 1)}
    for m, runs in methods.items():
        runs = [r for r in runs if r.get("downsizes_scored")]
        out[m] = ({key: round(float(np.mean([r[key] for r in runs])), 1) for key in runs[0]} if runs
                  else {"downsizes_scored": 0})
    return out


def evaluate(model, X, y, src, groups) -> dict:
    pred = _clamp_safe(snap(model.predict(X)), X)  # as deployed: never below the minimum safe size
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
    test_pred = _clamp_safe(snap(held_out.predict(X[is_test])), X[is_test])
    detail = [{"profile": r["profile"], "memory_mb": r["memory_mb"], "peak_mb": r["max_used_mb"],
               "label": int(t), "predicted": int(p)} for r, t, p in zip(test_src, y[is_test], test_pred)]
    cv = cross_validate(X, y, prof, src, groups, seed=seed)
    final = _fit(X, y, seed)  # deployed model uses all workloads
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    final.save_model(str(model_path))
    meta = {
        "feature_set": FEATURE_SET,
        "features": FEATURES,
        "version": "v3.1",
        "trainedOn": f"Measured AWS Lambda benchmark ({len(profiles)} workloads x {len(SIZES)} memory sizes)",
        "accuracy": metrics["exact_accuracy_pct"],
        "metrics_held_out": metrics,
        "cross_validation": cv,
        "train_workloads": len(profiles) - len(test_profiles),
        "test_workloads": len(test_profiles),
        "rows": len(rows),
        "peaks_harmonised": True,
        "label_distribution": {str(int(k)): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
        "held_out_detail": detail,
        "headroom": HEADROOM,
        "latency_tolerance": LATENCY_TOLERANCE,
        "seed": seed,
    }
    Path(meta_path).write_text(json.dumps(meta, indent=2))
    return meta
