"""The execution engine: applies (and rolls back) changes on AWS Lambda.

Safety rules, all enforced here and again by the IAM policy:
  * nothing is applied unless APPLY_ENABLED=true on the server
  * only functions whose name starts with APPLY_ALLOWED_PREFIX can be changed
  * the autonomy level 'monitor' blocks every change
  * a memory change must leave 25% headroom above the measured peak memory
  * every change is written to the action log with the old value, so it can be rolled back"""
import urllib.request

from app.config import settings
from app.services import store
from app.services.cloudwatch_service import (
    clear_cache, get_inventory, get_lambda_client, supports_arm,
)
from app.services.optimizer_service import HEADROOM, SIZES


class ApplyError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _guard(function_name: str) -> None:
    if not settings.APPLY_ENABLED:
        raise ApplyError(403, "Applying changes is disabled on this server (APPLY_ENABLED is false).")
    if store.get_settings()["autonomy"] == "monitor":
        raise ApplyError(403, "Autonomy level is 'Monitor only'. Change it in Settings to apply changes.")
    if not function_name.startswith(settings.APPLY_ALLOWED_PREFIX):
        raise ApplyError(403, f"Only functions whose name starts with '{settings.APPLY_ALLOWED_PREFIX}' can be changed.")


def _find(function_name: str) -> dict:
    inv = get_inventory(force=True)
    if inv["source"] != "aws":
        raise ApplyError(409, "AWS is not connected, so nothing can be applied.")
    fn = next((f for f in inv["functions"] if f["name"] == function_name), None)
    if fn is None:
        raise ApplyError(404, "Function not found")
    return fn


def _wait(client, function_name: str) -> None:
    client.get_waiter("function_updated_v2").wait(
        FunctionName=function_name, WaiterConfig={"Delay": 2, "MaxAttempts": 60})


def apply_memory(function_name: str, new_memory: int, mode: str = "manual", saving_pct: float = 0.0) -> dict:
    _guard(function_name)
    if new_memory not in [int(s) for s in SIZES]:
        raise ApplyError(400, f"Memory must be one of {[int(s) for s in SIZES]} MB.")
    fn = _find(function_name)
    if new_memory == fn["memory"]:
        raise ApplyError(400, "The function already has this memory size.")
    used = fn.get("maxMemoryUsed")
    if used is None:
        raise ApplyError(400, "Refused: no measured peak memory yet. Let the function run first so CloudWatch Logs contain its usage.")
    if new_memory < used * HEADROOM:
        raise ApplyError(400, f"Refused: peak memory used is {used} MB, so at least {int(used * HEADROOM) + 1} MB is needed.")
    client = get_lambda_client()
    try:
        client.update_function_configuration(FunctionName=function_name, MemorySize=new_memory)
        _wait(client, function_name)
    except Exception as exc:
        aid = store.log_action(function_name, "memory", fn["memory"], new_memory, mode, "failed", str(exc), fn["architecture"])
        store.notify("action", f"Change failed: {function_name}", str(exc), "error")
        raise ApplyError(502, f"AWS refused the change ({type(exc).__name__}). Logged as action {aid}.")
    clear_cache()
    aid = store.log_action(function_name, "memory", fn["memory"], new_memory, mode, "applied",
                           f"Memory changed from {fn['memory']} MB to {new_memory} MB", fn["architecture"], saving_pct)
    if store.get_settings()["notify_actions"]:
        store.notify("action", f"Memory changed: {function_name}",
                     f"{fn['memory']} MB -> {new_memory} MB ({mode}). Verified savings appear after new invocations.", "success")
    return {"id": aid, "function": function_name, "kind": "memory", "old": fn["memory"], "new": new_memory}


def apply_architecture(function_name: str, new_arch: str = "arm64", mode: str = "manual", saving_pct: float = 0.0) -> dict:
    _guard(function_name)
    if new_arch not in ("arm64", "x86_64"):
        raise ApplyError(400, "Architecture must be arm64 or x86_64.")
    fn = _find(function_name)
    if new_arch == fn["architecture"]:
        raise ApplyError(400, "The function already uses this architecture.")
    if not supports_arm(fn["runtime"]):
        raise ApplyError(400, "This runtime or package type cannot be switched safely.")
    client = get_lambda_client()
    try:
        info = client.get_function(FunctionName=function_name)
        if info.get("Configuration", {}).get("PackageType", "Zip") != "Zip":
            raise ApplyError(400, "Container image functions are not supported.")
        with urllib.request.urlopen(info["Code"]["Location"], timeout=60) as resp:  # presigned S3 URL
            package = resp.read()
        client.update_function_code(FunctionName=function_name, ZipFile=package, Architectures=[new_arch])
        _wait(client, function_name)
    except ApplyError:
        raise
    except Exception as exc:
        aid = store.log_action(function_name, "architecture", fn["architecture"], new_arch, mode, "failed", str(exc), fn["architecture"])
        store.notify("action", f"Change failed: {function_name}", str(exc), "error")
        raise ApplyError(502, f"AWS refused the change ({type(exc).__name__}). Logged as action {aid}.")
    clear_cache()
    aid = store.log_action(function_name, "architecture", fn["architecture"], new_arch, mode, "applied",
                           f"Architecture changed from {fn['architecture']} to {new_arch}", fn["architecture"], saving_pct)
    if store.get_settings()["notify_actions"]:
        store.notify("action", f"Architecture changed: {function_name}",
                     f"{fn['architecture']} -> {new_arch} ({mode}).", "success")
    return {"id": aid, "function": function_name, "kind": "architecture", "old": fn["architecture"], "new": new_arch}


def rollback(action_id: int) -> dict:
    row = store.get_action(action_id)
    if row is None:
        raise ApplyError(404, "Action not found")
    if row["status"] != "applied" or row["mode"] == "rollback":
        raise ApplyError(400, "Only an applied change can be rolled back.")
    if row["kind"] == "memory":
        return apply_memory(row["function_name"], int(row["old_value"]), mode="rollback")
    return apply_architecture(row["function_name"], row["old_value"], mode="rollback")
