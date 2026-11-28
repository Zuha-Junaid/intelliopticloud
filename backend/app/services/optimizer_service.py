import json
from pathlib import Path

import numpy as np
from xgboost import XGBRegressor

from app.config import settings
from app.services import training
from app.services.cloudwatch_service import supports_arm

# Valid AWS Lambda memory sizes the model snaps its prediction to
SIZES = np.array([128, 256, 512, 1024, 2048, 3008])
HEADROOM = training.HEADROOM

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_FILE = MODEL_DIR / "memory_model.json"
META_FILE = MODEL_DIR / "model_meta.json"
# The benchmark is committed to Git (backend/data/ is ignored), so Render can retrain from it.
BENCHMARK_DIR = Path(__file__).resolve().parent.parent.parent / "benchmark"
TRAINING_CSV = BENCHMARK_DIR / "real_benchmark.csv"

LEGACY_FEATURES = ["Memory MB", "Invocations", "Avg Duration", "Cold Start Ratio", "Hour of Day",
                   "Memory Utilization %"]

_model = None
_accuracy = 0.0
_source = "none"
_meta = {}


def _snap(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return SIZES[np.abs(values[:, None] - SIZES[None, :]).argmin(axis=1)]


def _load_colab_model() -> bool:
    """Load the trained model if its files exist. Returns True on success."""
    global _model, _accuracy, _source, _meta
    if not MODEL_FILE.exists():
        return False
    try:
        m = XGBRegressor()
        m.load_model(str(MODEL_FILE))
        _model = m
        _meta = json.loads(META_FILE.read_text()) if META_FILE.exists() else {}
        _accuracy = float(_meta.get("accuracy", 0.0))
        _source = "benchmark" if _meta.get("feature_set") == training.FEATURE_SET else "colab"
        print(f"Loaded model from {MODEL_FILE} ({_source}, accuracy {_accuracy}%)")
        return True
    except Exception as exc:  # corrupt file etc. -> fall back to training
        print(f"Could not load model ({exc}); training locally instead")
        return False


def _train() -> None:
    """Retrain. Uses the real benchmark CSV when it exists, otherwise the synthetic fallback."""
    global _model, _accuracy, _source, _meta
    if TRAINING_CSV.exists():
        try:
            _meta = training.train_from_csv(TRAINING_CSV, MODEL_FILE, META_FILE)
            m = XGBRegressor()
            m.load_model(str(MODEL_FILE))
            _model, _accuracy, _source = m, float(_meta["accuracy"]), "benchmark"
            print(f"Model retrained on real benchmark data - held-out accuracy {_accuracy}%")
            return
        except Exception as exc:
            print(f"Training on the benchmark file failed ({exc}); using the synthetic fallback")
    rng = np.random.default_rng(42)
    n = 5000
    memory = rng.choice(SIZES, n)
    invocations = rng.integers(1_000, 500_000, n)
    duration = rng.uniform(10, 3000, n)
    cold_ratio = rng.uniform(0, 0.3, n)
    hour = rng.integers(0, 24, n)
    util = rng.uniform(0.1, 0.95, n)

    X = np.column_stack([memory, invocations, duration, cold_ratio, hour, util])
    y = _snap(memory * util * 1.2)

    idx = rng.permutation(n)
    cut = int(n * 0.8)
    train, test = idx[:cut], idx[cut:]

    _model = XGBRegressor(
        n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=1
    )
    _model.fit(X[train], y[train])

    mae = float(np.mean(np.abs(_model.predict(X[test]) - y[test])))
    _accuracy = round(max(0.0, 100 - mae / float(y[test].mean()) * 100), 1)
    _source = "trained-at-startup"
    _meta = {"feature_set": "legacy6", "features": LEGACY_FEATURES, "version": "v2.3.1",
             "trainedOn": "Synthetic cloud usage data (5,000 samples)", "accuracy": _accuracy}
    print(f"XGBoost trained locally (synthetic) - Accuracy: {_accuracy}%, MAE: {mae:.2f}")


def get_model() -> XGBRegressor:
    if _model is None and not _load_colab_model():
        _train()
    return _model


def get_meta() -> dict:
    get_model()
    return dict(_meta)


def _min_safe_size(max_used) -> int:
    """Smallest valid size that still leaves headroom above the measured peak memory."""
    need = float(max_used) * HEADROOM
    for s in SIZES:
        if s >= need:
            return int(s)
    return int(SIZES[-1])


def predict_memory(memory: int, invocations: int, duration: float, max_used=None) -> dict:
    model = get_model()
    real = _meta.get("feature_set") == training.FEATURE_SET
    if real:
        if max_used is None or invocations <= 0:
            return {"current": int(memory), "optimal": int(memory), "confidence": 0.0,
                    "saves": False, "reduction_pct": 0, "basis": "no usage data yet"}
        X = np.array([training.features(memory, duration, max_used)], dtype=float)
        basis = "measured peak memory"
    else:
        # legacy model: cold_ratio, hour and utilisation are typical defaults
        X = np.array([[memory, invocations, duration, 0.1, 12, 0.6]], dtype=float)
        basis = "default utilisation"
    predicted = float(model.predict(X)[0])
    optimal = int(_snap([predicted])[0])
    if max_used is not None:
        optimal = max(optimal, _min_safe_size(max_used))  # never recommend a size that cannot hold the function
    confidence = round(max(50.0, 100 - abs(predicted - optimal) / optimal * 100), 1)
    return {
        "current": int(memory),
        "optimal": optimal,
        "confidence": confidence,
        "saves": optimal < memory,
        "reduction_pct": round((memory - optimal) / memory * 100, 1) if optimal < memory else 0,
        "basis": basis,
    }


def recommend_spot(invocations: int, duration: float) -> dict:
    """Advisory score for how suitable a workload is for the cheaper compute option
    (steady, high-volume, long enough to matter). AWS Lambda has no spot market, so the
    option the system can actually APPLY is the Graviton (arm64) architecture."""
    score = 0
    if invocations > 50000:
        score += 30
    if duration > 200:
        score += 25
    if invocations > 100000:
        score += 25
    score = min(score, 80)
    return {
        "recommend": score >= 50,
        "score": score,
        "risk": "Low" if score >= 70 else "Medium" if score >= 50 else "High",
        "saving_pct": round(score * 0.8, 1) if score >= 50 else 0,
    }


def recommend_architecture(runtime: str, architecture: str, invocations: int) -> dict:
    """Graviton2 (arm64) is billed 20% less per GB-second than x86_64."""
    saving = round((1 - settings.PRICE_GBS_ARM / settings.PRICE_GBS_X86) * 100, 1)
    if architecture == "arm64":
        return {"recommend": False, "saving_pct": 0, "reason": "already on arm64"}
    if not supports_arm(runtime):
        return {"recommend": False, "saving_pct": 0, "reason": "runtime or package type not supported"}
    if invocations <= 0:
        return {"recommend": False, "saving_pct": 0, "reason": "no usage yet"}
    return {"recommend": True, "saving_pct": saving, "reason": "arm64 is billed 20% less per GB-second"}


def get_accuracy() -> float:
    get_model()
    return _accuracy


def get_model_source() -> str:
    get_model()
    return _source
