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


@pytest.fixture(autouse=True)
def _clear_inventory_cache():
    from app.services import cloudwatch_service
    cloudwatch_service.clear_cache()
    yield
    cloudwatch_service.clear_cache()


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
    assert b["source"] == "sample" and b["costSummary"]["savedAmount"] == 0
    assert isinstance(b["costHistory"], list) and "serverUptimeHours" in b["systemHealth"]


def test_TC_F02_cost_breakdown_sorted(client, token):
    b = client.get("/api/reports/cost-breakdown", headers=H(token)).json()["breakdown"]
    costs = [x["cost"] for x in b]
    assert costs == sorted(costs, reverse=True)


def test_TC_F03_savings_report(client, token):
    b = client.get("/api/reports/savings", headers=H(token)).json()
    assert b["verified"] == [] and b["totalMonthlySavingPkr"] == 0 and b["monthly"] == []


def test_TC_F04_notifications_mark_read(client, token):
    from app.services import store
    store.notify("system", "F04 test notification", "body")
    nid = client.get("/api/notifications/", headers=H(token)).json()["notifications"][0]["id"]
    assert client.put(f"/api/notifications/{nid}/read", headers=H(token)).json() == {"ok": True}
    assert client.put("/api/notifications/999999/read", headers=H(token)).status_code == 404


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


def test_TC_H03_get_metric_api_error_is_raised():
    with patch.object(cw, "get_cloudwatch_client", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            cw.get_metric("f", "Duration")


def test_TC_H04_real_path_builds_function_records(monkeypatch):
    monkeypatch.setattr(cw.settings, "AWS_ACCESS_KEY_ID", "AKIAFAKEFORTEST")
    lam = MagicMock()
    lam.list_functions.return_value = {"Functions": [
        {"FunctionName": "demo", "FunctionArn": "arn:aws:lambda:us-east-1:000000000000:function:demo",
         "Runtime": "python3.12", "MemorySize": 256}]}
    with patch.object(cw, "get_lambda_client", return_value=lam), \
            patch.object(cw, "get_metric", side_effect=[3.0, 20.5]), patch.object(cw, "fetch_reports", return_value=[]):
        fns = cw.get_functions()
    assert len(fns) == 1 and fns[0]["name"] == "demo" and fns[0]["memory"] == 256
    assert fns[0]["invocations"] == 3 and fns[0]["avgDuration"] == 20.5
    assert fns[0]["architecture"] == "x86_64" and fns[0]["maxMemoryUsed"] is None


def test_TC_H05_aws_failure_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(cw.settings, "AWS_ACCESS_KEY_ID", "AKIAFAKEFORTEST")
    with patch.object(cw, "get_lambda_client", side_effect=RuntimeError("no network")):
        fns = cw.get_functions()
    assert len(fns) == 5 and fns[0]["id"] == "fn-001"


def test_TC_H06_clients_are_created_for_both_services():
    with patch.object(cw.boto3, "client") as c:
        cw.get_lambda_client(); cw.get_cloudwatch_client()
        cw.get_logs_client()
    assert [call.args[0] for call in c.call_args_list] == ["lambda", "cloudwatch", "logs"]


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


# =====================================================================================
# Groups K-P: execution engine, scheduler, history, verified savings, settings, training
# =====================================================================================
import csv  # noqa: E402
import math  # noqa: E402
import random  # noqa: E402
from app.services import apply_service, cycle_service, savings_service, store, training  # noqa: E402


def _report(duration, billed, memory, used, cold=False):
    msg = (f"REPORT RequestId: abc\tDuration: {duration} ms\tBilled Duration: {billed} ms\t"
           f"Memory Size: {memory} MB\tMax Memory Used: {used} MB")
    if cold:
        msg += "\tInit Duration: 150.0 ms"
    return msg


class FakeAWS:
    """Stands in for the boto3 lambda, cloudwatch and logs clients."""

    def __init__(self):
        def fn(name, mem, runtime="python3.12", arch="x86_64"):
            return {"FunctionName": name, "FunctionArn": f"arn:aws:lambda:us-east-1:000000000000:function:{name}",
                    "Runtime": runtime, "MemorySize": mem, "Architectures": [arch]}
        self.fns = {"ioc-demo-api": fn("ioc-demo-api", 1024), "other-fn": fn("other-fn", 1024),
                    "ioc-demo-go": fn("ioc-demo-go", 1024, runtime="go1.x")}
        self.invocations = {"ioc-demo-api": 5000, "other-fn": 5000, "ioc-demo-go": 10}
        self.durations = {"ioc-demo-api": 200.0, "other-fn": 200.0, "ioc-demo-go": 50.0}
        self.events = {}      # function name -> list of (timestamp_ms, message)
        self.calls = []
        self.fail_update = False

    # lambda
    def list_functions(self, **kw):
        return {"Functions": list(self.fns.values())}

    def update_function_configuration(self, FunctionName, MemorySize):
        if self.fail_update:
            raise RuntimeError("AccessDenied")
        self.fns[FunctionName]["MemorySize"] = MemorySize
        self.calls.append(("memory", FunctionName, MemorySize))

    def get_function(self, FunctionName):
        return {"Configuration": {"PackageType": "Zip"}, "Code": {"Location": "https://example.invalid/code.zip"}}

    def update_function_code(self, FunctionName, ZipFile, Architectures):
        self.fns[FunctionName]["Architectures"] = Architectures
        self.calls.append(("arch", FunctionName, Architectures[0]))

    def get_waiter(self, name):
        return MagicMock()

    # cloudwatch
    def get_metric_statistics(self, Namespace, MetricName, Dimensions, **kw):
        name = Dimensions[0]["Value"]
        if MetricName == "Invocations":
            return {"Datapoints": [{"Sum": self.invocations[name]}]}
        return {"Datapoints": [{"Average": self.durations[name]}]}

    # logs
    def filter_log_events(self, logGroupName, filterPattern, startTime, endTime, nextToken=None):
        name = logGroupName.rsplit("/", 1)[1]
        evs = [{"timestamp": t, "message": m} for t, m in self.events.get(name, []) if startTime <= t <= endTime]
        return {"events": evs}

    def add(self, name, ts_ms, n, duration, billed, memory, used, cold=False):
        self.events.setdefault(name, []).extend(
            (ts_ms + i, _report(duration, billed, memory, used, cold)) for i in range(n))


@pytest.fixture()
def aws(client, monkeypatch):
    fake = FakeAWS()
    monkeypatch.setattr(cw.settings, "AWS_ACCESS_KEY_ID", "AKIAFAKEFORTEST")
    monkeypatch.setattr(settings, "APPLY_ENABLED", True)
    monkeypatch.setattr(settings, "APPLY_ALLOWED_PREFIX", "ioc-demo-")
    for mod in (cw, apply_service):
        monkeypatch.setattr(mod, "get_lambda_client", lambda: fake)
    monkeypatch.setattr(cw, "get_cloudwatch_client", lambda: fake)
    monkeypatch.setattr(cw, "get_logs_client", lambda: fake)
    from sqlalchemy import delete
    from app.database import actions as actions_t
    with dbmod.engine.begin() as conn:
        conn.execute(delete(actions_t))           # every test starts without earlier changes
    store.kv_set("settings", {})  # defaults: autonomy "approve", min confidence 85
    store.kv_set("last_cycle", None)
    cw.clear_cache()
    fake.add("ioc-demo-api", int(time.time() * 1000) - 3_600_000, 30, 200.0, 200, 1024, 90)
    return fake


# ---------------- TC-K: execution engine (apply / rollback) ----------------
def test_TC_K01_apply_blocked_when_disabled(aws, monkeypatch):
    monkeypatch.setattr(settings, "APPLY_ENABLED", False)
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_memory("ioc-demo-api", 256)
    assert e.value.status_code == 403 and aws.calls == []


def test_TC_K02_apply_blocked_for_other_functions(aws):
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_memory("other-fn", 256)
    assert e.value.status_code == 403 and aws.calls == []


def test_TC_K03_apply_blocked_in_monitor_mode(aws):
    store.update_settings({"autonomy": "monitor"})
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_memory("ioc-demo-api", 256)
    assert e.value.status_code == 403 and aws.calls == []


def test_TC_K04_memory_change_is_applied_and_logged(aws):
    out = apply_service.apply_memory("ioc-demo-api", 256)
    assert out["old"] == 1024 and out["new"] == 256 and aws.fns["ioc-demo-api"]["MemorySize"] == 256
    logged = store.list_actions(1)[0]
    assert logged["status"] == "applied" and logged["kind"] == "memory" and logged["oldValue"] == "1024"
    assert store.list_notifications(1)[0]["type"] == "action"


@pytest.mark.parametrize("value", [100, 1500, 4096])
def test_TC_K05_invalid_memory_size_rejected(aws, value):
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_memory("ioc-demo-api", value)
    assert e.value.status_code == 400 and aws.calls == []


def test_TC_K06_same_memory_rejected(aws):
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_memory("ioc-demo-api", 1024)
    assert e.value.status_code == 400


def test_TC_K07_headroom_over_peak_memory_is_enforced(aws):
    aws.events["ioc-demo-api"] = []
    aws.add("ioc-demo-api", int(time.time() * 1000) - 60_000, 5, 200.0, 200, 1024, 500)
    with pytest.raises(apply_service.ApplyError) as e:   # 500 MB * 1.25 = 625 MB > 512 MB
        apply_service.apply_memory("ioc-demo-api", 512)
    assert e.value.status_code == 400 and "peak memory" in e.value.message
    assert apply_service.apply_memory("ioc-demo-api", 2048)["new"] == 2048  # a larger size is allowed


def test_TC_K08_aws_error_is_logged_as_failed(aws):
    aws.fail_update = True
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_memory("ioc-demo-api", 256)
    assert e.value.status_code == 502
    assert store.list_actions(1)[0]["status"] == "failed" and aws.fns["ioc-demo-api"]["MemorySize"] == 1024


def test_TC_K09_architecture_switch_to_arm64(aws):
    fake_resp = MagicMock()
    fake_resp.__enter__.return_value.read.return_value = b"zipbytes"
    with patch.object(apply_service.urllib.request, "urlopen", return_value=fake_resp):
        out = apply_service.apply_architecture("ioc-demo-api", "arm64")
    assert out["new"] == "arm64" and aws.fns["ioc-demo-api"]["Architectures"] == ["arm64"]


def test_TC_K10_unsupported_runtime_or_same_arch_rejected(aws):
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.apply_architecture("ioc-demo-go", "arm64")
    assert e.value.status_code == 400
    with pytest.raises(apply_service.ApplyError):
        apply_service.apply_architecture("ioc-demo-api", "x86_64")
    with pytest.raises(apply_service.ApplyError):
        apply_service.apply_architecture("ioc-demo-api", "mips")


def test_TC_K11_rollback_restores_old_value(aws):
    first = apply_service.apply_memory("ioc-demo-api", 256)
    back = apply_service.rollback(first["id"])
    assert back["new"] == 1024 and aws.fns["ioc-demo-api"]["MemorySize"] == 1024
    with pytest.raises(apply_service.ApplyError):          # a rollback itself cannot be rolled back
        apply_service.rollback(back["id"])
    with pytest.raises(apply_service.ApplyError) as e:
        apply_service.rollback(999999)
    assert e.value.status_code == 404


def test_TC_K12_api_requires_confirmation_and_valid_input(aws, client, token):
    body = {"function": "ioc-demo-api", "kind": "memory", "value": "256"}
    assert client.post("/api/optimization/apply", json=body, headers=H(token)).status_code == 400
    r = client.post("/api/optimization/apply", json={**body, "confirm": True}, headers=H(token))
    assert r.status_code == 200 and r.json()["new"] == 256
    assert client.post("/api/optimization/apply", json={**body, "value": "abc", "confirm": True}, headers=H(token)).status_code == 400
    assert client.post("/api/optimization/apply", json={**body, "kind": "disk", "confirm": True}, headers=H(token)).status_code == 400
    assert client.post("/api/optimization/apply", json=body).status_code == 401
    assert client.get("/api/optimization/actions", headers=H(token)).json()["actions"][0]["function"] == "ioc-demo-api"
    aid = client.get("/api/optimization/actions", headers=H(token)).json()["actions"][0]["id"]
    assert client.post(f"/api/optimization/rollback/{aid}", headers=H(token)).json()["new"] == 1024


def test_TC_K13_nothing_is_applied_on_sample_data(client, token, monkeypatch):
    monkeypatch.setattr(settings, "APPLY_ENABLED", True)
    store.kv_set("settings", {})
    r = client.post("/api/optimization/apply", headers=H(token),
                    json={"function": "ioc-demo-api", "kind": "memory", "value": "256", "confirm": True})
    assert r.status_code == 409


# ---------------- TC-L: monitoring cycle, scheduler, history, notifications ----------------
def test_TC_L01_run_cycle_authentication(aws, client, token, monkeypatch):
    monkeypatch.setattr(settings, "CRON_TOKEN", "secret-cron-token")
    assert client.post("/api/system/run-cycle").status_code == 401
    assert client.post("/api/system/run-cycle", headers={"X-Cron-Token": "wrong"}).status_code == 401
    r = client.post("/api/system/run-cycle", headers={"X-Cron-Token": "secret-cron-token"})
    assert r.status_code == 200 and r.json()["trigger"] == "scheduled" and r.json()["source"] == "aws"
    r = client.post("/api/system/run-cycle", headers=H(token))
    assert r.status_code == 200 and r.json()["trigger"] == "manual"
    assert client.post("/api/system/run-cycle", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_TC_L02_cycle_stores_history(aws, client, token):
    before = len(cycle_service.history())
    out = cycle_service.run_cycle()
    assert out["functions"] == 3 and out["measured"] == 1
    assert len(cycle_service.history()) == before + 1
    h = client.get("/api/reports/history", headers=H(token)).json()["history"]
    assert h[-1]["cost"] > 0
    assert store.kv_get("last_cycle")["functions"] == 3


def test_TC_L03_sample_data_is_never_stored_as_history(client, token):
    store.kv_set("settings", {})
    before = len(cycle_service.history())
    out = cycle_service.run_cycle()
    assert out["source"] == "sample" and len(cycle_service.history()) == before


def test_TC_L04_auto_mode_applies_only_safe_changes(aws):
    store.update_settings({"autonomy": "auto", "min_confidence": 50})
    out = cycle_service.run_cycle()
    assert out["applied"] == 1 and aws.calls == [("memory", "ioc-demo-api", aws.fns["ioc-demo-api"]["MemorySize"])]
    assert aws.fns["other-fn"]["MemorySize"] == 1024            # not an allowed function name
    assert aws.fns["ioc-demo-api"]["MemorySize"] < 1024


def test_TC_L05_approve_mode_applies_nothing(aws):
    store.update_settings({"autonomy": "approve", "min_confidence": 50})
    out = cycle_service.run_cycle()
    assert out["applied"] == 0 and aws.calls == [] and out["recommendations"] >= 1


def test_TC_L06_auto_mode_respects_confidence_threshold(aws, monkeypatch):
    fixed = {"current": 1024, "optimal": 256, "confidence": 90.0, "saves": True, "reduction_pct": 75.0, "basis": "x"}
    monkeypatch.setattr(cycle_service, "predict_memory", lambda *a, **k: fixed)
    store.update_settings({"autonomy": "auto", "min_confidence": 95})
    assert cycle_service.run_cycle()["applied"] == 0 and aws.calls == []
    store.update_settings({"min_confidence": 90})
    assert cycle_service.run_cycle()["applied"] == 1 and aws.fns["ioc-demo-api"]["MemorySize"] == 256


def test_TC_L07_spike_alert_and_deduplication(aws):
    cycle_service.run_cycle()
    aws.invocations["ioc-demo-api"] = 20000                      # 4x the previous check
    cycle_service.run_cycle()
    titles = [n["title"] for n in store.list_notifications(50)]
    assert titles.count("Usage increase: ioc-demo-api") == 1
    cycle_service.run_cycle()                                    # same title within 24 h is not repeated
    assert [n["title"] for n in store.list_notifications(50)].count("Usage increase: ioc-demo-api") == 1


def test_TC_L08_notification_preferences_are_respected(aws):
    store.update_settings({"notify_alerts": False})
    count = lambda: sum(1 for n in store.list_notifications(500) if n["type"] in ("recommendation", "alert"))  # noqa: E731
    before = count()
    cycle_service.run_cycle()
    assert count() == before


def test_TC_L09_notify_deduplicates_by_title():
    t = f"dedupe-{random.random()}"
    assert store.notify("system", t, "x", dedupe_hours=1) is True
    assert store.notify("system", t, "x", dedupe_hours=1) is False
    assert store.notify("system", t, "x") is True


# ---------------- TC-M: verified savings ----------------
def _apply_and_events(aws, new_memory, before_n=30, after_n=30, billed_after=200, kind="memory"):
    now = int(time.time() * 1000)
    aws.events["ioc-demo-api"] = []
    aws.add("ioc-demo-api", now - 3_600_000, before_n, 200.0, 200, 1024, 90)
    out = apply_service.apply_memory("ioc-demo-api", new_memory)
    aws.add("ioc-demo-api", int(time.time() * 1000), after_n, float(billed_after), billed_after, new_memory, 90)
    time.sleep(0.06)  # the verification window must end after the newest event
    return out


def test_TC_M01_waiting_until_enough_invocations(aws):
    _apply_and_events(aws, 256, after_n=5)
    item = savings_service.verified_savings()["items"][0]
    assert item["status"] == "waiting" and item["eventsAfter"] == 5


def test_TC_M02_memory_saving_is_measured_from_billed_cost(aws):
    _apply_and_events(aws, 256)
    r = savings_service.verified_savings()
    item = r["items"][0]
    assert item["status"] == "verified" and item["avgBilledBeforeMs"] == item["avgBilledAfterMs"] == 200
    assert -76 < item["changePct"] < -70                         # 1024 MB -> 256 MB, same duration
    assert item["monthlySavingPkr"] > 0 and r["totalMonthlySavingPkr"] == item["monthlySavingPkr"]


def test_TC_M03_slower_function_shows_less_or_no_saving(aws):
    _apply_and_events(aws, 128, billed_after=1600)               # 8x slower at 128 MB: no saving
    item = savings_service.verified_savings()["items"][0]
    assert item["status"] == "verified" and item["changePct"] >= -1 and item["monthlySavingPkr"] <= 0
    assert savings_service.verified_savings()["totalMonthlySavingPkr"] == 0


def test_TC_M04_architecture_saving_is_twenty_percent(aws):
    now = int(time.time() * 1000)
    aws.events["ioc-demo-api"] = []
    aws.add("ioc-demo-api", now - 3_600_000, 30, 200.0, 200, 1024, 90)
    resp = MagicMock(); resp.__enter__.return_value.read.return_value = b"z"
    with patch.object(apply_service.urllib.request, "urlopen", return_value=resp):
        apply_service.apply_architecture("ioc-demo-api", "arm64")
    aws.add("ioc-demo-api", int(time.time() * 1000), 30, 200.0, 200, 1024, 90)
    time.sleep(0.06)
    item = savings_service.verified_savings()["items"][0]
    assert item["kind"] == "architecture" and -20.5 < item["changePct"] < -10   # 20% on compute, requests unchanged


def test_TC_M05_dashboard_and_report_use_verified_total(aws, client, token):
    _apply_and_events(aws, 256)
    total = savings_service.verified_savings()["totalMonthlySavingPkr"]
    d = client.get("/api/dashboard/summary", headers=H(token)).json()
    assert d["source"] == "aws" and d["costSummary"]["savedAmount"] == total > 0
    assert d["costSummary"]["previousMonthly"] == round(d["costSummary"]["currentMonthly"] + total, 2)
    rep = client.get("/api/reports/savings", headers=H(token)).json()
    assert rep["totalMonthlySavingPkr"] == total and rep["monthly"][0]["saved"] == total


def test_TC_M06_rollback_entries_are_not_counted_as_savings(aws):
    first = _apply_and_events(aws, 256)
    apply_service.rollback(first["id"])
    assert all(i["mode"] != "rollback" for i in savings_service.verified_savings()["items"])


# ---------------- TC-N: settings and profile ----------------
def test_TC_N01_settings_defaults_and_update(client, token):
    store.kv_set("settings", {})
    d = client.get("/api/settings", headers=H(token)).json()
    assert d == {"autonomy": "approve", "min_confidence": 85, "notify_actions": True,
                 "notify_alerts": True, "notify_summary": True}
    r = client.put("/api/settings", headers=H(token), json={"autonomy": "auto", "min_confidence": 90, "notify_summary": False})
    assert r.status_code == 200 and r.json()["autonomy"] == "auto" and r.json()["notify_summary"] is False
    assert client.get("/api/settings", headers=H(token)).json()["min_confidence"] == 90
    store.kv_set("settings", {})


@pytest.mark.parametrize("body", [{"autonomy": "wild"}, {"min_confidence": 49}, {"min_confidence": 101},
                                  {"min_confidence": True}])
def test_TC_N02_invalid_settings_rejected(client, token, body):
    assert client.put("/api/settings", headers=H(token), json=body).status_code in (400, 422)


def test_TC_N03_settings_need_login(client):
    assert client.get("/api/settings").status_code == 401 and client.put("/api/settings", json={}).status_code == 401


def test_TC_N04_profile_update(client):
    t = _reg(client, "profile@example.com").json()["access_token"]
    r = client.put("/api/auth/me", headers=H(t), json={"name": "New Name", "accountType": "SME"})
    assert r.status_code == 200 and r.json()["user"] == {"name": "New Name", "email": "profile@example.com", "accountType": "SME"}
    assert client.post("/api/auth/login", json={"email": "profile@example.com", "password": "Passw0rd!"}).json()["user"]["name"] == "New Name"
    assert client.put("/api/auth/me", headers=H(t), json={"name": " ", "accountType": "SME"}).status_code == 400
    assert client.put("/api/auth/me", headers=H(t), json={"name": "X", "accountType": "Giant"}).status_code == 400
    assert client.put("/api/auth/me", json={"name": "X", "accountType": "SME"}).status_code == 401


def test_TC_N05_system_status_and_pipeline(aws, client, token, monkeypatch):
    monkeypatch.setattr(settings, "CRON_TOKEN", "")
    s = client.get("/api/system/status", headers=H(token)).json()
    assert s["aws"]["connected"] and s["apply"]["enabled"] and s["schedulerConfigured"] is False
    p = client.get("/api/optimization/pipeline", headers=H(token)).json()
    assert [x["status"] for x in p["stages"]] == ["waiting"] * 5 and p["lastCycle"] is None
    cycle_service.run_cycle()
    p = client.get("/api/optimization/pipeline", headers=H(token)).json()
    assert p["lastCycle"]["functions"] == 3 and p["stages"][0]["status"] == "complete"
    assert "3 function(s)" in p["stages"][0]["desc"]


def test_TC_N06_recommendations_include_measured_basis_and_architecture(aws, client, token):
    r = client.get("/api/optimization/recommendations", headers=H(token)).json()
    assert r["source"] == "aws" and r["applyEnabled"] is True
    api = next(x for x in r["recommendations"] if x["function"] == "ioc-demo-api")
    assert api["arch"]["recommend"] is True and api["arch"]["saving_pct"] == 20.0
    go = next(x for x in r["recommendations"] if x["function"] == "ioc-demo-go")
    assert go["arch"]["recommend"] is False


def test_TC_N07_aws_failure_is_reported_not_hidden(client, token, monkeypatch):
    monkeypatch.setattr(cw.settings, "AWS_ACCESS_KEY_ID", "AKIAFAKEFORTEST")
    monkeypatch.setattr(cw, "get_lambda_client", lambda: (_ for _ in ()).throw(RuntimeError("no network")))
    d = client.get("/api/resources/functions", headers=H(token)).json()
    assert d["source"] == "sample" and "Could not read from AWS" in d["warning"]


# ---------------- TC-O: training on real measurements ----------------
def _write_benchmark(path, n_profiles=24, seed=1):
    """Synthetic stand-in for the CSV produced by tools/collect_benchmark.py (formula-based)."""
    rnd = random.Random(seed)
    rows = []
    for k in range(n_profiles):
        used_base = rnd.choice([45, 120, 300, 600, 1000, 1800])
        cpu_ms = rnd.choice([0, 100, 400, 1500])
        sleep_ms = rnd.choice([0, 150])
        for mem in training.SIZES:
            if mem < used_base + 40:
                continue
            share = min(mem / 1769.0, 1.0)
            dur = 5 + sleep_ms + cpu_ms / share
            rows.append({"profile": f"p{k}", "memory_mb": mem, "duration_ms": round(dur, 2),
                         "billed_ms": math.ceil(dur), "max_used_mb": used_base + 40})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["profile", "memory_mb", "duration_ms", "billed_ms", "max_used_mb"])
        w.writeheader(); w.writerows(rows)


def _rows(*items):
    return [{"profile": "p", "memory_mb": m, "duration_ms": d, "billed_ms": math.ceil(d), "max_used_mb": u}
            for m, d, u in items]


def test_TC_O01_label_rule_picks_cheapest_size_within_latency_tolerance():
    # I/O-bound: the duration is the same at every size, so the smallest feasible size is cheapest
    assert training.optimal_size(_rows((128, 200, 50), (256, 200, 50), (512, 200, 50), (1024, 200, 50))) == 128
    # CPU-bound: 128 MB is 14x slower (more expensive and too slow); 1769 MB-class size is the fastest
    cpu = _rows((128, 1400, 50), (256, 700, 50), (512, 350, 50), (1024, 190, 50), (2048, 100, 50), (3008, 100, 50))
    assert training.optimal_size(cpu) == 2048


def test_TC_O02_label_rule_respects_memory_headroom():
    rows = _rows((128, 200, 100), (256, 200, 100), (512, 200, 100))   # 100 MB * 1.25 = 125 -> 128 is feasible
    assert training.optimal_size(rows) == 128
    rows = _rows((128, 200, 110), (256, 200, 110), (512, 200, 110))   # 110 * 1.25 = 137.5 -> 128 not feasible
    assert training.optimal_size(rows) == 256
    assert training.optimal_size(_rows((128, 200, 128))) is None


def test_TC_O03_train_from_csv_writes_model_and_metrics(tmp_path):
    _write_benchmark(tmp_path / "b.csv")
    meta = training.train_from_csv(tmp_path / "b.csv", tmp_path / "m.json", tmp_path / "meta.json")
    assert (tmp_path / "m.json").exists() and (tmp_path / "meta.json").exists()
    held = meta["metrics_held_out"]
    assert meta["feature_set"] == "real4" and meta["train_workloads"] + meta["test_workloads"] == 24
    assert 0 <= held["exact_accuracy_pct"] <= 100 and held["unsafe_predictions"] >= 0
    assert held["within_one_step_pct"] >= held["exact_accuracy_pct"]


def test_TC_O04_too_few_workloads_rejected(tmp_path):
    _write_benchmark(tmp_path / "b.csv", n_profiles=3)
    with pytest.raises(ValueError):
        training.train_from_csv(tmp_path / "b.csv", tmp_path / "m.json", tmp_path / "meta.json")


def test_TC_O05_backend_uses_benchmark_model_and_never_goes_below_safe_size(tmp_path, monkeypatch):
    _write_benchmark(tmp_path / "b.csv")
    training.train_from_csv(tmp_path / "b.csv", tmp_path / "m.json", tmp_path / "meta.json")
    monkeypatch.setattr(opt, "MODEL_FILE", tmp_path / "m.json")
    monkeypatch.setattr(opt, "META_FILE", tmp_path / "meta.json")
    for name, val in (("_model", None), ("_meta", {}), ("_source", "none"), ("_accuracy", 0.0)):
        monkeypatch.setattr(opt, name, val)
    assert opt.get_model_source() == "benchmark" and opt.get_meta()["feature_set"] == "real4"
    r = opt.predict_memory(2048, 5000, 120.0, max_used=900)
    assert r["optimal"] >= 1024 and r["basis"] == "measured peak memory"       # 900 * 1.25 = 1125 -> 2048 is the safe size
    assert opt.predict_memory(1024, 0, 0.0, max_used=None)["basis"] == "no usage data yet"
    assert opt.predict_memory(1024, 100, 50.0, max_used=None)["saves"] is False


def test_TC_O06_retrain_uses_benchmark_csv_when_present(tmp_path, monkeypatch):
    _write_benchmark(tmp_path / "real_benchmark.csv")
    monkeypatch.setattr(opt, "TRAINING_CSV", tmp_path / "real_benchmark.csv")
    monkeypatch.setattr(opt, "MODEL_FILE", tmp_path / "m.json")
    monkeypatch.setattr(opt, "META_FILE", tmp_path / "meta.json")
    for name, val in (("_model", None), ("_meta", {}), ("_source", "none"), ("_accuracy", 0.0)):
        monkeypatch.setattr(opt, name, val)
    opt._train()
    assert opt.get_model_source() == "benchmark" and (tmp_path / "m.json").exists()


def test_TC_O07_log_report_parsing_and_cost(aws):
    fns = cw.get_functions()
    api = next(f for f in fns if f["name"] == "ioc-demo-api")
    assert api["maxMemoryUsed"] == 90 and api["samples"] == 30 and api["coldStartRatio"] == 0.0
    assert api["monthlyCost"] == cw.calculate_cost(1024, 5000, 200.0)
    assert cw.calculate_cost(1024, 1000, 1000.0, "arm64") < cw.calculate_cost(1024, 1000, 1000.0, "x86_64")
    aws.add("ioc-demo-api", int(time.time() * 1000) - 2000, 2, 300.0, 300, 1024, 120, cold=True)
    cw.clear_cache()
    api = next(f for f in cw.get_functions() if f["name"] == "ioc-demo-api")
    assert api["maxMemoryUsed"] == 120 and api["coldStartRatio"] == round(2 / 32, 3)


def test_TC_M07_each_change_is_measured_only_against_its_own_period(aws):
    """A memory change followed by an architecture change must not count the memory saving twice."""
    now = int(time.time() * 1000)
    aws.events["ioc-demo-api"] = []
    aws.add("ioc-demo-api", now - 3_600_000, 30, 200.0, 200, 1024, 90)             # before everything
    apply_service.apply_memory("ioc-demo-api", 256)
    time.sleep(0.05)
    aws.add("ioc-demo-api", int(time.time() * 1000), 30, 200.0, 200, 256, 90)       # after memory change
    time.sleep(0.05)
    resp = MagicMock(); resp.__enter__.return_value.read.return_value = b"z"
    with patch.object(apply_service.urllib.request, "urlopen", return_value=resp):
        apply_service.apply_architecture("ioc-demo-api", "arm64")
    time.sleep(0.05)
    aws.add("ioc-demo-api", int(time.time() * 1000), 30, 200.0, 200, 256, 90)       # after arch change
    time.sleep(0.06)
    items = {i["kind"]: i for i in savings_service.verified_savings()["items"]}
    assert -76 < items["memory"]["changePct"] < -70            # 1024 -> 256 MB
    assert -20.5 < items["architecture"]["changePct"] < -10    # only the arm64 effect, not the memory one
    assert items["architecture"]["eventsBefore"] == 30


# ---------------- TC-P: benchmark collection script (simulated Lambda) ----------------
import base64 as _b64  # noqa: E402
import json as _json  # noqa: E402
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "tools"))
import collect_benchmark as cb  # noqa: E402


class SimLambda:
    """Simulates ioc-demo-bench: duration = waiting + CPU time / CPU share (1 vCPU at 1769 MB)."""

    def __init__(self):
        self.memory, self.calls = 128, 0

    def update_function_configuration(self, FunctionName, MemorySize, Timeout):
        self.memory, self.calls = MemorySize, 0

    def get_waiter(self, name):
        return MagicMock()

    def invoke(self, FunctionName, LogType, Payload):
        ev = _json.loads(Payload)
        self.calls += 1
        used = 35 + ev["alloc_mb"]
        if used > self.memory:
            return {"FunctionError": "Unhandled", "LogResult": _b64.b64encode(b"error")}
        cpu_ms = ev["cpu_iters"] / 1000.0                       # 1M iterations = 1000 ms at full CPU
        dur = 3 + ev["sleep_ms"] + cpu_ms / min(self.memory / 1769.0, 1.0)
        log = _report(round(dur, 2), math.ceil(dur), self.memory, used, cold=self.calls <= 2)
        return {"LogResult": _b64.b64encode(log.encode())}


def test_TC_P01_benchmark_collects_rows_and_discards_cold_starts(tmp_path):
    sim = SimLambda()
    profs = [p for p in cb.profiles() if p["alloc_mb"] in (0, 400) and p["cpu_iters"] in (0, 1_000_000)]
    rows = cb.run(sim, tmp_path / "b.csv", workers=1, profs=profs, log=lambda *_: None)
    assert (tmp_path / "b.csv").exists() and len(rows) > 0
    big = [r for r in rows if r["profile"] == "a400_c0m_s0"]
    assert min(r["memory_mb"] for r in big) == 512            # 400 MB + runtime does not fit in 128/256 MB
    cpu = {r["memory_mb"]: r["duration_ms"] for r in rows if r["profile"] == "a0_c1m_s0"}
    assert cpu[128] > 10 * cpu[2048] and abs(cpu[2048] - cpu[3008]) < 1     # CPU share grows with memory, then stops
    assert all(r["max_used_mb"] in (35, 435) for r in rows)


def test_TC_P02_full_pipeline_benchmark_to_trained_model(tmp_path):
    sim = SimLambda()
    cb.run(sim, tmp_path / "b.csv", workers=1, log=lambda *_: None)
    meta = training.train_from_csv(tmp_path / "b.csv", tmp_path / "m.json", tmp_path / "meta.json")
    held = meta["metrics_held_out"]
    assert meta["train_workloads"] + meta["test_workloads"] == len(cb.profiles())
    assert held["exact_accuracy_pct"] >= 60 and held["unsafe_predictions"] == 0
    assert set(meta["label_distribution"]) <= {str(x) for x in training.SIZES} and len(set(meta["label_distribution"])) >= 3
    assert len(meta["held_out_detail"]) == held["samples"]


def test_TC_K14_memory_change_refused_without_measured_usage(aws):
    with pytest.raises(apply_service.ApplyError) as e:        # ioc-demo-go has no log events yet
        apply_service.apply_memory("ioc-demo-go", 256)
    assert e.value.status_code == 400 and "no measured peak memory" in e.value.message and aws.calls == []
