"""IntelliOptiCloud automated test suite (black-box API tests + white-box unit tests).
Runs against the real backend code with the local SQLite database and the
built-in mock Lambda inventory (no AWS credentials are used)."""
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.main import app
from app.services import optimizer_service as opt
from app.services.cloudwatch_service import calculate_cost, get_functions

SIZES = [128, 256, 512, 1024, 2048, 3008]


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _reg(client, email, pw="Passw0rd!", name="Test User", acct="Startup"):
    return client.post("/api/auth/register", json={"name": name, "email": email, "password": pw, "accountType": acct})


@pytest.fixture(scope="session")
def token(client):
    r = _reg(client, "session.user@example.com")
    assert r.status_code == 200
    return r.json()["access_token"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


# ---------------- TC-A: registration ----------------
def test_TC_A01_register_valid(client):
    r = _reg(client, "a01@example.com")
    assert r.status_code == 200
    b = r.json()
    assert b["token_type"] == "bearer" and b["access_token"]
    assert b["user"] == {"name": "Test User", "email": "a01@example.com", "accountType": "Startup"}


def test_TC_A02_register_duplicate_email(client):
    _reg(client, "a02@example.com")
    r = _reg(client, "a02@example.com")
    assert r.status_code == 400 and r.json()["detail"] == "Email already registered"


def test_TC_A03_password_7_chars_rejected(client):
    assert _reg(client, "a03@example.com", pw="1234567").status_code == 400


def test_TC_A04_password_8_chars_accepted(client):
    assert _reg(client, "a04@example.com", pw="12345678").status_code == 200


def test_TC_A05_password_9_chars_accepted(client):
    assert _reg(client, "a05@example.com", pw="123456789").status_code == 200


def test_TC_A06_empty_name_rejected(client):
    assert _reg(client, "a06@example.com", name="").status_code == 400


def test_TC_A07_empty_email_rejected(client):
    assert _reg(client, "", pw="Passw0rd!").status_code == 400


def test_TC_A08_email_is_case_insensitive(client):
    _reg(client, "  MiXed.Case@Example.COM ")
    r = client.post("/api/auth/login", json={"email": "mixed.case@example.com", "password": "Passw0rd!"})
    assert r.status_code == 200


def test_TC_A09_missing_field_is_validation_error(client):
    r = client.post("/api/auth/register", json={"name": "x", "email": "y@z.com"})
    assert r.status_code == 422


def test_TC_A10_empty_password_rejected(client):
    assert _reg(client, "a10@example.com", pw="").status_code == 400


def test_TC_A11_password_longer_than_72_bytes_is_handled(client):
    pw = "x" * 80   # bcrypt only uses the first 72 bytes; longer input must not crash
    assert _reg(client, "a11@example.com", pw=pw).status_code == 200
    r = client.post("/api/auth/login", json={"email": "a11@example.com", "password": pw})
    assert r.status_code == 200


# ---------------- TC-B: login ----------------
def test_TC_B01_login_valid(client):
    _reg(client, "b01@example.com")
    r = client.post("/api/auth/login", json={"email": "b01@example.com", "password": "Passw0rd!"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_TC_B02_login_wrong_password(client):
    _reg(client, "b02@example.com")
    r = client.post("/api/auth/login", json={"email": "b02@example.com", "password": "WrongPass1"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password"


def test_TC_B03_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Passw0rd!"})
    assert r.status_code == 401


def test_TC_B04_password_is_stored_hashed(client):
    from sqlalchemy import select
    from app.database import engine, users
    _reg(client, "b04@example.com", pw="PlainText123")
    with engine.connect() as c:
        row = c.execute(select(users).where(users.c.email == "b04@example.com")).mappings().first()
    assert row["password_hash"] != "PlainText123" and row["password_hash"].startswith("$2")


# ---------------- TC-C: access control (JWT) ----------------
def test_TC_C01_no_token_rejected(client):
    r = client.get("/api/resources/functions")
    assert r.status_code == 401 and r.json()["detail"] == "Not authenticated"


def test_TC_C02_garbage_token_rejected(client):
    assert client.get("/api/resources/functions", headers=H("not-a-jwt")).status_code == 401


def test_TC_C03_expired_token_rejected(client):
    old = jwt.encode({"sub": "x@example.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                     settings.SECRET_KEY, settings.ALGORITHM)
    r = client.get("/api/resources/functions", headers=H(old))
    assert r.status_code == 401 and "expired" in r.json()["detail"].lower()


def test_TC_C04_wrong_secret_rejected(client):
    bad = jwt.encode({"sub": "x@example.com", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                     "some-other-secret", settings.ALGORITHM)
    assert client.get("/api/dashboard/summary", headers=H(bad)).status_code == 401


def test_TC_C05_valid_token_accepted(client, token):
    assert client.get("/api/resources/functions", headers=H(token)).status_code == 200


@pytest.mark.parametrize("path", ["/api/dashboard/summary", "/api/resources/functions", "/api/optimization/model-info",
                                  "/api/optimization/recommendations", "/api/reports/savings",
                                  "/api/reports/cost-breakdown", "/api/notifications/"])
def test_TC_C06_every_data_endpoint_requires_token(client, path):
    assert client.get(path).status_code == 401


def test_TC_C07_token_lifetime_is_60_minutes(client, token):
    p = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    life = p["exp"] - datetime.now(timezone.utc).timestamp()
    assert 59 * 60 < life <= 60 * 60


# ---------------- TC-D: resources ----------------
def test_TC_D01_list_functions(client, token):
    b = client.get("/api/resources/functions", headers=H(token)).json()
    assert b["total"] == len(b["functions"]) == 5
    assert {"name", "memory", "invocations", "avgDuration", "monthlyCost"} <= set(b["functions"][0])


def test_TC_D02_function_found(client, token):
    r = client.get("/api/resources/functions/image-processor", headers=H(token))
    assert r.status_code == 200 and r.json()["name"] == "image-processor"


def test_TC_D03_function_not_found(client, token):
    assert client.get("/api/resources/functions/does-not-exist", headers=H(token)).status_code == 404


def test_TC_D04_cost_formula():
    # 1024 MB, 1,000,000 invocations: (1*0.1*0.0000166667*1e6 + 0.0000002*1e6)*278
    assert calculate_cost(1024, 1_000_000) == round((1 * 0.1 * 0.0000166667 * 1e6 + 0.0000002 * 1e6) * 278.0, 2)
    assert calculate_cost(512, 0) == 0


# ---------------- TC-E: optimisation ----------------
def test_TC_E01_model_info_uses_colab_model(client, token):
    b = client.get("/api/optimization/model-info", headers=H(token)).json()
    assert b["algorithm"] == "XGBoost Regressor" and b["accuracy"] == 99.7
    assert opt.get_model_source() == "colab"


def test_TC_E02_recommendations_cover_all_functions(client, token):
    b = client.get("/api/optimization/recommendations", headers=H(token)).json()["recommendations"]
    assert len(b) == 5
    for r in b:
        assert r["memory"]["optimal"] in SIZES
        assert 50.0 <= r["memory"]["confidence"] <= 100.0
        assert {"recommend", "score", "risk", "saving_pct"} <= set(r["spot"])


def test_TC_E03_pipeline_has_five_stages(client, token):
    assert len(client.get("/api/optimization/pipeline", headers=H(token)).json()["stages"]) == 5


def test_TC_E04_retrain_endpoint(client, token):
    r = client.post("/api/optimization/retrain", headers=H(token))
    assert r.status_code == 200 and r.json()["message"] == "Model retrained"


# ---------------- TC-F: dashboard / reports / notifications ----------------
def test_TC_F01_dashboard_summary(client, token):
    b = client.get("/api/dashboard/summary", headers=H(token)).json()
    assert b["costSummary"]["currency"] == "PKR" and b["systemHealth"]["functionsMonitored"] == 5
    assert len(b["savingsTrend"]) == 6


def test_TC_F02_cost_breakdown_sorted(client, token):
    b = client.get("/api/reports/cost-breakdown", headers=H(token)).json()["breakdown"]
    costs = [x["cost"] for x in b]
    assert costs == sorted(costs, reverse=True)


def test_TC_F03_savings_report(client, token):
    b = client.get("/api/reports/savings", headers=H(token)).json()["report"]
    assert len(b) == 6 and b[0]["saved"] == b[0]["before"] - b[0]["after"]


def test_TC_F04_notifications_mark_read(client, token):
    assert client.put("/api/notifications/1/read", headers=H(token)).json() == {"ok": True}
    assert client.put("/api/notifications/999/read", headers=H(token)).json() == {"ok": False}


def test_TC_F05_notifications_mark_all_read(client, token):
    assert client.put("/api/notifications/read-all", headers=H(token)).json() == {"ok": True}
    ns = client.get("/api/notifications/", headers=H(token)).json()["notifications"]
    assert all(n["read"] for n in ns)


def test_TC_F06_health_and_root(client):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/").json()["status"] == "running"


# ---------------- TC-G: white-box / unit: spot recommendation ----------------
@pytest.mark.parametrize("inv,dur,score,rec,risk,saving", [
    (1000, 100, 0, False, "High", 0),            # none of C1,C2,C3
    (1000, 300, 25, False, "High", 0),           # C2 only
    (60000, 100, 30, False, "High", 0),          # C1 only
    (60000, 300, 55, True, "Medium", 44.0),      # C1,C2
    (150000, 100, 55, True, "Medium", 44.0),     # C1,C3
    (150000, 300, 80, True, "Low", 64.0),        # C1,C2,C3 (capped at 80)
])
def test_TC_G01_spot_decision_table(inv, dur, score, rec, risk, saving):
    r = opt.recommend_spot(inv, dur)
    assert (r["score"], r["recommend"], r["risk"], r["saving_pct"]) == (score, rec, risk, saving)


@pytest.mark.parametrize("inv,dur,score", [
    (50000, 200, 0), (50001, 200, 30), (100000, 200, 30), (100001, 200, 55),
    (1000, 200, 0), (1000, 200.01, 25),
])
def test_TC_G02_spot_boundaries(inv, dur, score):
    assert opt.recommend_spot(inv, dur)["score"] == score


@pytest.mark.parametrize("mem", SIZES)
def test_TC_G03_memory_prediction_valid_size(mem):
    r = opt.predict_memory(mem, 100000, 500.0)
    assert r["current"] == mem and r["optimal"] in SIZES
    assert r["saves"] == (r["optimal"] < mem)
    assert 50.0 <= r["confidence"] <= 100.0
    if not r["saves"]:
        assert r["reduction_pct"] == 0


def test_TC_G04_snap_to_nearest_size():
    assert list(opt._snap([100, 200, 400, 800, 1500, 2600, 5000])) == [128, 256, 512, 1024, 1024, 3008, 3008]
    assert list(opt._snap([130])) == [128] and list(opt._snap([3000])) == [3008]


def test_TC_G05_fallback_training_path(monkeypatch, tmp_path):
    monkeypatch.setattr(opt, "MODEL_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(opt, "_model", None)
    m = opt.get_model()
    assert m is not None and opt.get_model_source() == "trained-at-startup"


def test_TC_G06_corrupt_model_file_falls_back(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not a model")
    monkeypatch.setattr(opt, "MODEL_FILE", bad)
    monkeypatch.setattr(opt, "_model", None)
    assert opt.get_model() is not None and opt.get_model_source() == "trained-at-startup"


# ---------------- TC-H: CloudWatch adapter (boto3 mocked) ----------------
from unittest.mock import MagicMock, patch  # noqa: E402
from app.services import cloudwatch_service as cw  # noqa: E402
from app import database as dbmod  # noqa: E402


def test_TC_H01_get_metric_returns_rounded_value():
    fake = MagicMock()
    fake.get_metric_statistics.return_value = {"Datapoints": [{"Sum": 12.0}]}
    with patch.object(cw, "get_cloudwatch_client", return_value=fake):
        assert cw.get_metric("f", "Invocations") == 12.0
    fake.get_metric_statistics.return_value = {"Datapoints": [{"Average": 13.7149}]}
    with patch.object(cw, "get_cloudwatch_client", return_value=fake):
        assert cw.get_metric("f", "Duration") == 13.71


def test_TC_H02_get_metric_no_datapoints_is_zero():
    fake = MagicMock()
    fake.get_metric_statistics.return_value = {"Datapoints": []}
    with patch.object(cw, "get_cloudwatch_client", return_value=fake):
        assert cw.get_metric("f", "Invocations") == 0.0


def test_TC_H03_get_metric_api_error_is_zero():
    with patch.object(cw, "get_cloudwatch_client", side_effect=RuntimeError("boom")):
        assert cw.get_metric("f", "Duration") == 0.0


def test_TC_H04_real_path_builds_function_records(monkeypatch):
    monkeypatch.setattr(cw.settings, "AWS_ACCESS_KEY_ID", "AKIAFAKEFORTEST")
    lam = MagicMock()
    lam.list_functions.return_value = {"Functions": [
        {"FunctionName": "demo", "FunctionArn": "arn:aws:lambda:us-east-1:000000000000:function:demo",
         "Runtime": "python3.12", "MemorySize": 256}]}
    with patch.object(cw, "get_lambda_client", return_value=lam), patch.object(cw, "get_metric", side_effect=[3.0, 20.5]):
        fns = cw.get_functions()
    assert len(fns) == 1 and fns[0]["name"] == "demo" and fns[0]["memory"] == 256
    assert fns[0]["invocations"] == 3 and fns[0]["avgDuration"] == 20.5


def test_TC_H05_aws_failure_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(cw.settings, "AWS_ACCESS_KEY_ID", "AKIAFAKEFORTEST")
    with patch.object(cw, "get_lambda_client", side_effect=RuntimeError("no network")):
        fns = cw.get_functions()
    assert len(fns) == 5 and fns[0]["id"] == "fn-001"


def test_TC_H06_clients_are_created_for_both_services():
    with patch.object(cw.boto3, "client") as c:
        cw.get_lambda_client(); cw.get_cloudwatch_client()
    assert [call.args[0] for call in c.call_args_list] == ["lambda", "cloudwatch"]


# ---------------- TC-I: database URL handling ----------------
@pytest.mark.parametrize("given,expected", [
    ("postgres://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
    ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg2://u:p@h/db?sslmode=require"),
    ("mysql://u:p@h/db", "mysql://u:p@h/db"),
])
def test_TC_I01_database_url_rewrite(monkeypatch, given, expected):
    monkeypatch.setattr(dbmod.settings, "DATABASE_URL", given)
    assert dbmod._database_url() == expected


def test_TC_I02_empty_url_uses_sqlite(monkeypatch):
    monkeypatch.setattr(dbmod.settings, "DATABASE_URL", "")
    assert str(dbmod._database_url()).startswith("sqlite")


def test_TC_G07_model_without_metadata_file(monkeypatch, tmp_path):
    import shutil
    shutil.copy(opt.MODEL_FILE, tmp_path / "memory_model.json")
    monkeypatch.setattr(opt, "MODEL_FILE", tmp_path / "memory_model.json")
    monkeypatch.setattr(opt, "META_FILE", tmp_path / "model_meta.json")  # does not exist
    monkeypatch.setattr(opt, "_model", None)
    monkeypatch.setattr(opt, "_accuracy", 0.0)
    assert opt.get_model() is not None and opt.get_accuracy() == 0.0 and opt.get_model_source() == "colab"


# ---------------- TC-J: end-to-end use case ----------------
def test_TC_J01_end_to_end_user_journey(client):
    """Register -> login -> dashboard -> resources -> optimization -> reports -> notifications."""
    assert _reg(client, "journey@example.com").status_code == 200
    r = client.post("/api/auth/login", json={"email": "journey@example.com", "password": "Passw0rd!"})
    assert r.status_code == 200
    h = H(r.json()["access_token"])
    assert client.get("/api/dashboard/summary", headers=h).status_code == 200
    fns = client.get("/api/resources/functions", headers=h).json()
    recs = client.get("/api/optimization/recommendations", headers=h).json()["recommendations"]
    fns = fns["functions"] if isinstance(fns, dict) else fns
    assert len(fns) == len(recs) and len(fns) > 0
    assert client.get("/api/reports/cost-breakdown", headers=h).status_code == 200
    assert client.get("/api/reports/savings", headers=h).status_code == 200
    assert client.get("/api/notifications/", headers=h).status_code == 200