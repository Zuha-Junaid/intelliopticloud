"""Test isolation: a throw-away database and no AWS credentials, whatever is in the local .env.
Environment variables take priority over the .env file, so the tests can never touch the real
Neon database or the real AWS account."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ioc_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AWS_ACCESS_KEY_ID"] = ""
os.environ["AWS_SECRET_ACCESS_KEY"] = ""
os.environ["APPLY_ENABLED"] = "false"
os.environ["CRON_TOKEN"] = ""


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_model_state():
    """Tests that retrain or replace the model must not leak into later tests."""
    from app.services import optimizer_service as opt
    saved = {n: getattr(opt, n) for n in ("_model", "_meta", "_source", "_accuracy")}
    yield
    for n, v in saved.items():
        setattr(opt, n, v)
