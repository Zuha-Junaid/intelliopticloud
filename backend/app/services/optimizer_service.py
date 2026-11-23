import json
from pathlib import Path

import numpy as np
from xgboost import XGBRegressor

# Valid AWS Lambda memory sizes the model snaps its prediction to
SIZES = np.array([128, 256, 512, 1024, 2048, 3008])

# Model trained in Google Colab (notebooks/IntelliOptiCloud_XGBoost_Training.ipynb)
MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_FILE = MODEL_DIR / "memory_model.json"
META_FILE = MODEL_DIR / "model_meta.json"

_model = None
_accuracy = 0.0
_source = "none"


def _snap(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return SIZES[np.abs(values[:, None] - SIZES[None, :]).argmin(axis=1)]


def _load_colab_model() -> bool:
    """Load the Colab-trained model if its files exist. Returns True on success."""
    global _model, _accuracy, _source
    if not MODEL_FILE.exists():
        return False
    try:
        m = XGBRegressor()
        m.load_model(str(MODEL_FILE))
        _model = m
        if META_FILE.exists():
            _accuracy = float(json.loads(META_FILE.read_text()).get("accuracy", 0.0))
        _source = "colab"
        print(f"Loaded Colab-trained model from {MODEL_FILE} (accuracy {_accuracy}%)")
        return True
    except Exception as exc:  # corrupt file etc. -> fall back to training
        print(f"Could not load Colab model ({exc}); training locally instead")
        return False


def _train() -> None:
    """Fallback: train the same model locally on synthetic data."""
    global _model, _accuracy, _source
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
    print(f"XGBoost trained locally - Accuracy: {_accuracy}%, MAE: {mae:.2f}")


def get_model() -> XGBRegressor:
    if _model is None and not _load_colab_model():
        _train()
    return _model


def predict_memory(memory: int, invocations: int, duration: float) -> dict:
    model = get_model()
    # cold_ratio, hour and utilisation are not available from basic CloudWatch metrics,
    # so typical defaults are used (see README limitations)
    X = np.array([[memory, invocations, duration, 0.1, 12, 0.6]], dtype=float)
    predicted = float(model.predict(X)[0])
    optimal = int(_snap([predicted])[0])
    confidence = round(max(50.0, 100 - abs(predicted - optimal) / optimal * 100), 1)
    return {
        "current": int(memory),
        "optimal": optimal,
        "confidence": confidence,
        "saves": optimal < memory,
        "reduction_pct": round((memory - optimal) / memory * 100, 1) if optimal < memory else 0,
    }


def recommend_spot(invocations: int, duration: float) -> dict:
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


def get_accuracy() -> float:
    get_model()
    return _accuracy


def get_model_source() -> str:
    get_model()
    return _source