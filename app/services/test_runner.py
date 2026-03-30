import json
import socket
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Union

from flask import current_app

from app.extensions import db
from app.models import TestRun
from app.services.test_taxonomy import (
    area_has_subtypes,
    default_runner_mode,
    get_test_spec,
    internal_test_type_for_area,
)



RUNNING_PROCESSES: Dict[str, Dict] = {}
REGISTRY_LOCK = threading.Lock()
STALE_QUEUE_MINUTES = 10
ACTIVE_STATES = {"QUEUED", "BASELINE", "RUNNING", "STOPPING"}


def _utcnow():
    return datetime.now(timezone.utc)


def _dt_to_storage(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _venv_bin() -> Path:
    return _project_root() / "venv" / "bin"


def _reports_root() -> Path:
    return _project_root() / "reports-area"


def _test_area_root() -> Path:
    return _project_root() / "test-area"


def _locust_dir() -> Path:
    return _test_area_root() / "locust-attacks"


def _locust_abuse_dir() -> Path:
    return _test_area_root() / "locust-attacks" / "locust-abuse"


def _slowhttptest_dir() -> Path:
    return _test_area_root() / "slowhttptest-attacks"


def _slowloris_dir() -> Path:
    return _test_area_root() / "slowloris-attacks"


def _service_abuse_dir() -> Path:
    return _test_area_root() / "service-abuse" / "curl-bursts"


def _python_flood_dir() -> Path:
    return _test_area_root() / "python-l7-flood"


def _locust_executable() -> str:
    locust_path = _venv_bin() / "locust"
    return str(locust_path) if locust_path.exists() else "locust"


def _python_executable() -> str:
    py = _venv_bin() / "python"
    return str(py) if py.exists() else "python3"


def _commit():
    db.session.commit()


def _mark_failed(test_run: TestRun, reason: str):
    test_run.execution_state = "FAILED"
    test_run.failure_reason = reason
    test_run.end_time = _dt_to_storage(_utcnow())
    _commit()


def _mark_running(test_run: TestRun):
    test_run.execution_state = "RUNNING"
    test_run.start_time = _dt_to_storage(_utcnow())
    test_run.failure_reason = None
    _commit()


def _mark_completed(test_run: TestRun):
    test_run.execution_state = "COMPLETED"
    test_run.end_time = _dt_to_storage(_utcnow())
    _commit()


def _mark_cancelled(test_run: TestRun, reason: str = "Cancelled by user"):
    test_run.execution_state = "CANCELLED"
    test_run.failure_reason = reason
    test_run.end_time = _dt_to_storage(_utcnow())
    _commit()


def _get_test_by_id(test_id: str) -> Optional[TestRun]:
    return TestRun.query.filter_by(test_id=test_id).first()


def get_active_run() -> Optional[TestRun]:
    cleanup_stale_queued_tests()
    candidates = (
        TestRun.query
        .filter(TestRun.execution_state.in_(list(ACTIVE_STATES)))
        .all()
    )
    if not candidates:
        return None

    def sort_key(run: TestRun):
        return (
            str(getattr(run, "start_time", "") or ""),
            str(getattr(run, "test_id", "") or "")
        )

    return sorted(candidates, key=sort_key, reverse=True)[0]


def has_active_run() -> bool:
    return get_active_run() is not None


def _find_active_test() -> Optional[TestRun]:
    return get_active_run()


def cleanup_stale_queued_tests():
    cutoff = _utcnow() - timedelta(minutes=STALE_QUEUE_MINUTES)
    stale_items = TestRun.query.filter_by(execution_state="QUEUED").all()

    changed = False
    for item in stale_items:
        created_value = getattr(item, "start_time", None) or getattr(item, "created_at", None)
        if not created_value:
            continue

        if isinstance(created_value, str):
            try:
                created_value = datetime.fromisoformat(created_value.replace("Z", "+00:00"))
            except Exception:
                continue

        if created_value.tzinfo is None:
            created_value = created_value.replace(tzinfo=timezone.utc)

        if created_value < cutoff:
            item.execution_state = "FAILED"
            item.failure_reason = "Stale queued test cleaned up automatically"
            item.end_time = _dt_to_storage(_utcnow())
            changed = True

    if changed:
        _commit()


def _json_load(value, fallback):
    if not value:
        return fallback
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _get_target_config(test_run: TestRun) -> Dict:
    return _json_load(getattr(test_run, "target_config", None), {})


def _get_test_parameters(test_run: TestRun) -> Dict:
    return _json_load(getattr(test_run, "test_parameters", None), {})


def validate_target_config(target_config: Dict) -> Tuple[bool, str]:
    protocol = str(target_config.get("protocol", "http")).strip().lower()
    host = str(target_config.get("host", "")).strip()
    port = target_config.get("port")
    endpoints = target_config.get("endpoints", [])

    if protocol not in {"http", "https"}:
        return False, f"Unsupported protocol: {protocol}"
    if not host:
        return False, "Target host is required"
    if host.startswith("http://") or host.startswith("https://"):
        return False, "Host must not include http:// or https://"

    try:
        port = int(port)
    except Exception:
        return False, "Port must be a valid integer"

    if not (1 <= port <= 65535):
        return False, "Port must be between 1 and 65535"

    if not isinstance(endpoints, list) or not endpoints:
        return False, "At least one endpoint is required"

    for ep in endpoints:
        if not str(ep).startswith("/"):
            return False, f"Endpoint must start with '/': {ep}"

    try:
        socket.gethostbyname(host)
    except Exception as exc:
        return False, f"Target reachability check failed: {exc}"

    return True, "Target configuration looks valid"


def resolve_taxonomy(test_area: str, test_type: Optional[str]) -> Tuple[str, str, Dict]:
    resolved_type = internal_test_type_for_area(test_area, test_type)
    if not resolved_type:
        raise ValueError(f"Invalid test area: {test_area}")

    spec = get_test_spec(test_area, test_type)
    if not spec:
        raise ValueError(f"Invalid test selection for area={test_area}, type={test_type}")

    runner_mode = default_runner_mode(test_area, test_type)
    return resolved_type, runner_mode, spec


def _normalized_level(params: Dict) -> str:
    level = params.get("execution_level") or params.get("profile") or params.get("level") or "baseline"
    return str(level).strip().lower()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(value))


def _report_prefix(test_run: TestRun, subdir: str, name: str) -> Path:
    target = _reports_root() / subdir
    target.mkdir(parents=True, exist_ok=True)
    return target / f"{_safe_slug(name)}_{_safe_slug(test_run.test_id)}"


def _endpoint_csv_arg(endpoints: List[str]) -> str:
    return ",".join(str(x).strip() for x in endpoints if str(x).strip())


def _build_ta1_command(test_run: TestRun, params: Dict, target: Dict) -> Tuple[List[str], Path, Dict[str, str]]:
    level = _normalized_level(params)
    script_map = {
        "baseline": "locust_baseline.py",
        "light": "locust_light_attack.py",
        "medium": "locust_medium_attack.py",
        "full": "locust_full_attack.py",
    }
    script_path = _locust_dir() / script_map.get(level, "")
    if not script_path.exists():
        raise FileNotFoundError(f"TA1 locust script not found: {script_path}")

    report_prefix = _report_prefix(test_run, "volumetric", f"vol_{level}")
    host_url = f'{target["protocol"]}://{target["host"]}:{target["port"]}'
    users = int(params.get("users", 1))
    spawn_rate = int(params.get("spawn_rate", 1))
    duration_seconds = int(params.get("duration_seconds", 60))

    cmd = [
        _locust_executable(),
        "-f", str(script_path),
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "--run-time", f"{duration_seconds}s",
        "--host", host_url,
        "--print-stats",
        "--csv", str(report_prefix),
        "--html", f"{report_prefix}.html",
    ]

    env = {}
    endpoints = target.get("endpoints", [])
    if endpoints:
        env["TARGET_ENDPOINTS"] = _endpoint_csv_arg(endpoints)

    return cmd, script_path.parent, env


def _build_ta2_command(test_run: TestRun, test_type: str, params: Dict, target: Dict) -> Tuple[List[str], Path]:
    level = _normalized_level(params)
    wrapper = _slowhttptest_dir() / "run_slow_tests_profiles.py"

    if test_type == "SLOWHTTPTEST_BODY":
        if not wrapper.exists():
            raise FileNotFoundError(f"TA2 wrapper not found: {wrapper}")
        return [_python_executable(), str(wrapper), "B", level], wrapper.parent

    if test_type == "SLOWHTTPTEST_HEADER":
        if not wrapper.exists():
            raise FileNotFoundError(f"TA2 wrapper not found: {wrapper}")
        return [_python_executable(), str(wrapper), "H", level], wrapper.parent

    if test_type == "SLOWLORIS":
        script = _slowloris_dir() / "run_slowloris_test.py"
        if not script.exists():
            raise FileNotFoundError(f"TA2 slowloris runner not found: {script}")
        return [_python_executable(), str(script), level], script.parent

    raise ValueError(f"Unsupported TA2 subtype: {test_type}")


def _build_ta3_command(test_run: TestRun, params: Dict, target: Dict) -> Tuple[List[str], Path, Dict[str, str]]:
    level = _normalized_level(params)
    script_map = {
        "baseline": "locust_abuse_baseline.py",
        "light": "locust_abuse_light.py",
        "medium": "locust_abuse_medium.py",
        "full": "locust_abuse_FULL.py",
    }
    script_path = _locust_abuse_dir() / script_map.get(level, "")
    if not script_path.exists():
        raise FileNotFoundError(f"TA3 locust script not found: {script_path}")

    report_prefix = _report_prefix(test_run, "locust-abuse", f"abuse_{level}")
    host_url = f'{target["protocol"]}://{target["host"]}:{target["port"]}'
    users = int(params.get("users", 1))
    spawn_rate = int(params.get("spawn_rate", 1))
    duration_seconds = int(params.get("duration_seconds", 60))

    cmd = [
        _locust_executable(),
        "-f", str(script_path),
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "--run-time", f"{duration_seconds}s",
        "--host", host_url,
        "--print-stats",
        "--csv", str(report_prefix),
        "--html", f"{report_prefix}.html",
    ]

    extra_env = {}
    endpoints = target.get("endpoints", [])
    if endpoints:
        extra_env["TARGET_ENDPOINTS"] = _endpoint_csv_arg(endpoints)

    return cmd, script_path.parent, extra_env


def _build_ta4_command(test_run: TestRun, test_type: str, params: Dict, target: Dict) -> Tuple[List[str], Path]:
    level = _normalized_level(params)
    script = _service_abuse_dir() / "run_service_abuse_profiles.sh"
    if not script.exists():
        raise FileNotFoundError(f"TA4 script not found: {script}")

    cmd = [str(script), level]
    if test_type == "CURL_BURST_PIDSTAT":
        cmd.append("--pidstat")
    elif test_type != "CURL_BURST":
        raise ValueError(f"Unsupported TA4 subtype: {test_type}")
    return cmd, script.parent
def _build_ta5_command(test_run, resolved_type, params, target):
    base_dir = _project_root() / "test-area" / "python-l7-flood"
    scenarios_dir = base_dir / "scenarios"

    protocol = str(target.get("protocol", "http")).strip().lower()
    host = str(target.get("host", "")).strip()
    port = int(target.get("port"))
    endpoints = target.get("endpoints", ["/"]) or ["/"]

    endpoint = str(endpoints[0]).strip() if endpoints else "/"
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    url = f"{protocol}://{host}:{port}{endpoint}"

    level = str(params.get("level", "baseline")).strip().lower()
    timeout = int(params.get("request_timeout", 10))

    resolved_type = str(resolved_type).strip().upper()

    if level not in {"baseline", "light", "medium", "full"}:
        raise ValueError(f"Unsupported TA5 level: {level}")

    if resolved_type == "ASYNC_FLOOD":
        scenario_name = f"python_l7_async_{level}.py"
    elif resolved_type in {"REQUESTS_FLOOD", "REQUEST_FLOOD"}:
        scenario_name = f"python_l7_requests_{level}.py"
    else:
        raise ValueError(f"Unsupported TA5 subtype: {resolved_type}")

    script_path = scenarios_dir / scenario_name

    if not script_path.exists():
        raise FileNotFoundError(f"TA5 python flood script not found: {script_path}")

    python_exec = _python_executable()

    cmd = [
        python_exec,
        str(script_path),
        "--url",
        url,
        "--timeout",
        str(timeout),
    ]

    return cmd, base_dir



    
def build_runner_command(test_run: TestRun) -> Tuple[List[str], Path, str]:
    test_area = test_run.test_area
    params = _get_test_parameters(test_run)
    target = _get_target_config(test_run)
    raw_test_type = (
        getattr(test_run, "test_type", None)
        or getattr(test_run, "test_subtype", None)
        or params.get("test_type")
        or params.get("selected_test_type")
        or params.get("resolved_test_type")
    )

    resolved_type, runner_mode, _spec = resolve_taxonomy(test_area, raw_test_type)

    if test_area == "TA1":
        cmd, cwd, extra_env = _build_ta1_command(test_run, params, target)
    elif test_area == "TA2":
        cmd, cwd = _build_ta2_command(test_run, resolved_type, params, target)
    elif test_area == "TA3":
        cmd, cwd, extra_env = _build_ta3_command(test_run, params, target)
    elif test_area == "TA4":
        cmd, cwd = _build_ta4_command(test_run, resolved_type, params, target)
    elif test_area == "TA5":
        cmd, cwd = _build_ta5_command(test_run, resolved_type, params, target)
    else:
        raise ValueError(f"Unsupported test area: {test_area}")

    return cmd, cwd, runner_mode


def _register_process(test_id: str, process: subprocess.Popen, command: List[str], cwd: Path):
    with REGISTRY_LOCK:
        RUNNING_PROCESSES[test_id] = {
            "process": process,
            "command": command,
            "cwd": str(cwd),
            "started_at": _dt_to_storage(_utcnow()),
        }


def _unregister_process(test_id: str):
    with REGISTRY_LOCK:
        RUNNING_PROCESSES.pop(test_id, None)


def _get_registered_process(test_id: str) -> Optional[Dict]:
    with REGISTRY_LOCK:
        return RUNNING_PROCESSES.get(test_id)


def launch_test_process(test_run: TestRun) -> Dict:
    cleanup_stale_queued_tests()

    active = _find_active_test()
    if active and active.test_id != test_run.test_id:
        return {
            "ok": False,
            "message": f"Another active test already exists: {active.test_id}"
        }

    target = _get_target_config(test_run)
    ok, message = validate_target_config(target)
    if not ok:
        _mark_failed(test_run, message)
        return {"ok": False, "message": message}

    try:
        command, cwd, runner_mode = build_runner_command(test_run)
    except Exception as exc:
        current_app.logger.exception("Failed to build runner command")
        _mark_failed(test_run, str(exc))
        return {"ok": False, "message": str(exc)}

    try:
        current_app.logger.info(
            "[RUNNER] Launching test_id=%s area=%s runner=%s cwd=%s cmd=%s",
            test_run.test_id,
            test_run.test_area,
            runner_mode,
            str(cwd),
            " ".join(str(x) for x in command),
        )

        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except Exception as exc:
        current_app.logger.exception("Failed to launch subprocess")
        _mark_failed(test_run, f"Failed to launch test runner: {exc}")
        return {
            "ok": False,
            "message": f"Failed to launch test runner: {exc}"
        }

    _register_process(test_run.test_id, process, command, cwd)
    _mark_running(test_run)

    app = current_app._get_current_object()
    watcher = threading.Thread(
        target=_watch_process_exit,
        args=(app, test_run.test_id),
        daemon=True,
    )
    watcher.start()

    return {
        "ok": True,
        "message": "Test launched successfully",
        "test_id": test_run.test_id,
        "pid": process.pid,
        "runner_mode": runner_mode,
        "command": command,
    }


def _watch_process_exit(app, test_id: str):
    with app.app_context():
        record = _get_registered_process(test_id)
        if not record:
            return

        process = record["process"]

        try:
            stdout, stderr = process.communicate()
        except Exception as exc:
            current_app.logger.exception("Failed while waiting for test process")
            test_run = _get_test_by_id(test_id)
            if test_run and test_run.execution_state != "CANCELLED":
                _mark_failed(test_run, f"Watcher failed: {exc}")
            _unregister_process(test_id)
            return

        test_run = _get_test_by_id(test_id)
        if not test_run:
            _unregister_process(test_id)
            return

        current_app.logger.info(
            "Test process finished test_id=%s returncode=%s",
            test_id,
            process.returncode
        )

        if test_run.execution_state == "CANCELLED":
            _unregister_process(test_id)
            return

        if process.returncode == 0:
            _mark_completed(test_run)
        else:
            err = (stderr or "").strip()
            if not err and stdout:
                err = stdout.strip()
            _mark_failed(
                test_run,
                f"Runner exited with code {process.returncode}. stderr: {err[:1000]}"
            )

        _unregister_process(test_id)


def validate_test_request(payload: Dict) -> Dict:
    test_area = payload.get("test_area")
    test_type = payload.get("test_type") or payload.get("test_subtype")
    target_config = {
        "protocol": payload.get("protocol", "http"),
        "host": str(payload.get("host", "")).strip(),
        "port": payload.get("port"),
        "endpoints": _normalize_endpoints(payload.get("endpoints")),
    }

    if not test_area:
        return {"ok": False, "message": "Test area is required"}

    if area_has_subtypes(test_area) and not test_type:
        return {"ok": False, "message": f"Test subtype is required for {test_area}"}

    try:
        resolved_type, runner_mode, spec = resolve_taxonomy(test_area, test_type)
    except Exception as exc:
        return {"ok": False, "message": str(exc)}

    ok, message = validate_target_config(target_config)
    if not ok:
        return {"ok": False, "message": message}

    return {
        "ok": True,
        "message": "Validation passed",
        "resolved_test_type": resolved_type,
        "runner_mode": runner_mode,
        "category": spec.get("category"),
        "description": spec.get("description"),
    }


def run_test_by_id(test_id: str) -> Dict:
    test_run = _get_test_by_id(test_id)
    if not test_run:
        return {"ok": False, "message": f"Test not found: {test_id}"}
    return launch_test_process(test_run)


def start_test_run(test_ref: Union[str, TestRun]) -> Dict:
    if isinstance(test_ref, TestRun):
        return launch_test_process(test_ref)
    return run_test_by_id(test_ref)


def stop_test_run(test_id: str) -> Dict:
    return cancel_test(test_id)


def cancel_test_run(test_id: str) -> Dict:
    return cancel_test(test_id)


def cancel_test(test_id: str) -> Dict:
    record = _get_registered_process(test_id)
    test_run = _get_test_by_id(test_id)

    if not test_run:
        return {"ok": False, "message": f"Test not found: {test_id}"}

    if not record:
        if test_run.execution_state in {"QUEUED", "RUNNING", "BASELINE", "STOPPING"}:
            _mark_cancelled(test_run, "Cancelled, but no active process handle was found")
            return {"ok": True, "message": "Test marked as cancelled", "test_id": test_id}
        return {"ok": False, "message": "No active process found for this test", "test_id": test_id}

    process = record["process"]
    try:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

        _mark_cancelled(test_run)
        _unregister_process(test_id)
        return {"ok": True, "message": "Test cancelled successfully", "test_id": test_id}
    except Exception as exc:
        return {"ok": False, "message": f"Failed to cancel test: {exc}", "test_id": test_id}


def cancel_active_test() -> Dict:
    active = _find_active_test()
    if not active:
        return {"ok": False, "message": "No active test found"}
    return cancel_test(active.test_id)


def get_run_log_tail(test_id: str, max_chars: int = 4000) -> Dict:
    test_run = _get_test_by_id(test_id)
    if not test_run:
        return {"ok": False, "message": f"Test not found: {test_id}", "test_id": test_id, "log": ""}

    record = _get_registered_process(test_id)
    state = getattr(test_run, "execution_state", "UNKNOWN")
    reason = getattr(test_run, "failure_reason", None)

    if record:
        cmd = record.get("command", [])
        cwd = record.get("cwd", "")
        started_at = record.get("started_at", "")
        log_text = (
            f"[RUNNING]\n"
            f"test_id={test_id}\n"
            f"state={state}\n"
            f"started_at={started_at}\n"
            f"cwd={cwd}\n"
            f"command={' '.join(str(x) for x in cmd)}\n"
        )
    else:
        log_text = (
            f"[NOT RUNNING]\n"
            f"test_id={test_id}\n"
            f"state={state}\n"
        )
        if reason:
            log_text += f"reason={reason}\n"

    return {"ok": True, "test_id": test_id, "state": state, "log": log_text[-max_chars:]}


def get_test_run_status(test_id: str) -> Dict:
    test_run = _get_test_by_id(test_id)
    if not test_run:
        return {"ok": False, "message": f"Test not found: {test_id}", "test_id": test_id}

    record = _get_registered_process(test_id)
    return {
        "ok": True,
        "test_id": test_id,
        "state": getattr(test_run, "execution_state", None),
        "failure_reason": getattr(test_run, "failure_reason", None),
        "is_running": record is not None,
        "start_time": getattr(test_run, "start_time", None),
        "end_time": getattr(test_run, "end_time", None),
    }


def get_run_status(test_id: str) -> Dict:
    return get_test_run_status(test_id)


def get_test_status(test_id: str) -> Dict:
    return get_test_run_status(test_id)


def get_test_log_tail(test_id: str, max_chars: int = 4000) -> Dict:
    return get_run_log_tail(test_id, max_chars=max_chars)


def _normalize_endpoints(raw) -> List[str]:
    if raw is None:
        return ["/"]
    if isinstance(raw, list):
        cleaned = [str(x).strip() for x in raw if str(x).strip()]
    else:
        cleaned = [line.strip() for line in str(raw).splitlines() if line.strip()]
    return cleaned or ["/"]