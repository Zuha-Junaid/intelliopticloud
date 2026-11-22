import numpy as np
from xgboost import XGBRegressor

# Valid AWS Lambda memory sizes the model snaps its prediction to
SIZES = np.array([128, 256, 512, 1024, 2048, 3008])

_model = None
_accuracy = 0.0


def _snap(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return SIZES[np.abs(values[:, None] - SIZES[None, :]).argmin(axis=1)]


def _train() -> None:
    global _model, _accuracy
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
    print(f"XGBoost trained — Accuracy: {_accuracy}%, MAE: {mae:.2f}")


def get_model() -> XGBRegressor:
    if _model is None:
        _train()
    return _model


def predict_memory(memory: int, invocations: int, duration: float) -> dict:
    model = get_model()
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