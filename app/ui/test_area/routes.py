import json
import uuid
from datetime import datetime, timezone

from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    jsonify,
    request,
)

from . import test_area_bp
from .forms import CreateTestRunForm

from ...extensions import db
from ...models import TestRun
from ...services.test_taxonomy import (
    TEST_TAXONOMY,
    test_types_for_area,
    get_test_spec,
    allowed_runner_modes,
    default_runner_mode,
)

from ...services.test_runner import (
    validate_target_config,
    start_test_run,
    stop_test_run,
    cancel_test_run,
    get_run_log_tail,
    has_active_run,
    get_active_run,
)
# =========================================================
# Helpers
# =========================================================

ACTIVE_STATES = {"QUEUED", "BASELINE", "RUNNING", "STOPPING"}


def _utcnow():
    return datetime.now(timezone.utc)


def _fill_test_type_choices(form: CreateTestRunForm):
    area = form.test_area.data or "TA1"
    form.test_type.choices = test_types_for_area(area)

    # If current selected subtype is invalid for this area,
    # fall back to the first available subtype.
    valid_values = [choice[0] for choice in form.test_type.choices]
    if form.test_type.data not in valid_values and valid_values:
        form.test_type.data = valid_values[0]


def _safe_get_field_data(form: CreateTestRunForm, field_name: str):
    if not hasattr(form, field_name):
        return None
    return getattr(form, field_name).data


def _take_int(form: CreateTestRunForm, field_name: str):
    value = _safe_get_field_data(form, field_name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _take_bool(form: CreateTestRunForm, field_name: str):
    value = _safe_get_field_data(form, field_name)
    return bool(value)


def _split_endpoints(raw_text: str):
    if not raw_text:
        return []
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def _get_active_run():
    return (
        db.session.query(TestRun)
        .filter(TestRun.execution_state.in_(ACTIVE_STATES))
        .order_by(TestRun.start_time.desc().nullslast(), TestRun.test_id.desc())
        .first()
    )


def _build_target_config(form: CreateTestRunForm):
    return {
        "protocol": form.protocol.data,
        "host": form.host.data.strip() if form.host.data else "",
        "port": form.port.data,
        "endpoints": _split_endpoints(form.endpoints.data),
    }


def _build_parameters(form: CreateTestRunForm):
    area = form.test_area.data
    test_type = form.test_type.data

    spec = get_test_spec(area, test_type)
    taxonomy_fields = spec.get("fields", {})

    params = {
        "level": form.level.data,
        "runner_mode": form.runner_mode.data,
        "baseline_seconds": form.baseline_seconds.data,
        "dry_run": bool(form.dry_run.data),
        "escalation_schedule": form.escalation_schedule.data.strip()
        if form.escalation_schedule.data
        else "",
        "custom_flags": form.custom_flags.data.strip()
        if form.custom_flags.data
        else "",
        "notes": form.notes.data.strip() if form.notes.data else "",
    }

    for field_name, meta in taxonomy_fields.items():
        field_type = meta.get("type")

        if field_type == "select":
            value = _take_int(form, field_name)
            if value is not None:
                params[field_name] = value

        elif field_type == "bool":
            params[field_name] = _take_bool(form, field_name)

    return params





def _validate_runner_mode(area: str, test_type: str, runner_mode: str):
    allowed = allowed_runner_modes(area, test_type)
    if allowed and runner_mode not in allowed:
        return (
            False,
            f"Runner mode '{runner_mode}' is not allowed for {area}/{test_type}. "
            f"Allowed modes: {', '.join(allowed)}"
        )
    return True, "Runner mode is valid."


def _make_taxonomy_run_name(area: str, test_type: str):
    ts = _utcnow().strftime("%Y%m%d-%H%M%S")
    return f"{area}-{test_type}-{ts}"


def _serialize_run(run: TestRun):
    return {
        "test_id": run.test_id,
        "test_area": run.test_area,
        "test_name": run.test_name,
        "execution_state": run.execution_state,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "end_time": run.end_time.isoformat() if run.end_time else None,
        "failure_reason": run.failure_reason,
        "test_parameters": json.loads(run.test_parameters) if run.test_parameters else {},
        "target_config": json.loads(run.target_config) if run.target_config else {},
    }


# =========================================================
# Page routes
# =========================================================

@test_area_bp.get("/new")
def new_test():
    form = CreateTestRunForm()
    _fill_test_type_choices(form)

    # Set runner mode default based on selected area/subtype
    if form.test_area.data and form.test_type.data:
        form.runner_mode.data = default_runner_mode(form.test_area.data, form.test_type.data)

    active_run = _get_active_run()
    return render_template(
        "test_create.html",
        form=form,
        active_run=active_run,
    )


@test_area_bp.get("/created/<test_id>")
def test_created(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        flash("Run not found.", "error")
        return redirect(url_for("test_area.new_test"))

    return render_template("test_created.html", run=run)


# =========================================================
# JSON / AJAX endpoints
# =========================================================

@test_area_bp.get("/subtypes/<area>")
def subtypes(area: str):
    choices = test_types_for_area(area)
    if not choices:
        return jsonify([]), 404
    return jsonify(choices)


@test_area_bp.get("/spec/<area>/<test_type>")
def subtype_spec(area: str, test_type: str):
    spec = get_test_spec(area, test_type)
    if not spec:
        return jsonify({"ok": False, "message": "Test spec not found."}), 404

    return jsonify(
        {
            "ok": True,
            "area": area,
            "test_type": test_type,
            "label": spec.get("label", test_type),
            "description": spec.get("description", ""),
            "runner_modes": spec.get("runner_modes", []),
            "default_runner": spec.get("default_runner", "framework"),
            "fields": spec.get("fields", {}),
        }
    )


@test_area_bp.post("/validate")
def validate_test():
    form = CreateTestRunForm()
    _fill_test_type_choices(form)

    if not form.validate_on_submit():
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Please fix the form errors and try again.",
                    "errors": form.errors,
                }
            ),
            400,
        )

    area = form.test_area.data
    test_type = form.test_type.data
    runner_mode = form.runner_mode.data

    target_cfg = _build_target_config(form)

    ok, message = validate_target_config(target_cfg)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    ok, message = _validate_runner_mode(area, test_type, runner_mode)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    if form.level.data == "full" and (form.baseline_seconds.data or 0) < 60:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Full phase requires a mandatory baseline of at least 60 seconds.",
                }
            ),
            400,
        )

    active_run = _get_active_run()
    if active_run:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": f"Another active test already exists: {active_run.test_name} ({active_run.test_id})",
                    "active_run": _serialize_run(active_run),
                }
            ),
            409,
        )

    params = _build_parameters(form)

    return jsonify(
        {
            "ok": True,
            "message": "Validation successful.",
            "target_config": target_cfg,
            "parameters": params,
            "test_area": area,
            "test_type": test_type,
            "runner_mode": runner_mode,
        }
    )


@test_area_bp.get("/active")
def active_run():
    run = _get_active_run()
    if not run:
        return jsonify({"ok": True, "active": False, "run": None})
    return jsonify({"ok": True, "active": True, "run": _serialize_run(run)})


@test_area_bp.get("/status/<test_id>")
def run_status(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404
    return jsonify({"ok": True, "run": _serialize_run(run)})


@test_area_bp.get("/logs/<test_id>")
def run_logs(test_id: str):
    """
    Return the latest log output for a run.
    Uses the runner log if available, otherwise falls back
    to a synthetic log built from DB metadata.
    """

    from ...services.test_runner import get_run_log_tail

    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    # Try to read the real runner log first
    log_tail = get_run_log_tail(test_id)

    if log_tail and "No log file exists" not in log_tail:
        return jsonify({"ok": True, "log": log_tail})

    # Fallback if the run has not started yet
    try:
        target_cfg = json.loads(run.target_config or "{}")
    except Exception:
        target_cfg = {}

    try:
        params = json.loads(run.test_parameters or "{}")
    except Exception:
        params = {}

    lines = [
        f"Test ID      : {run.test_id}",
        f"Test Name    : {run.test_name}",
        f"Area         : {run.test_area}",
        f"State        : {run.execution_state}",
        f"Start Time   : {run.start_time.isoformat() if run.start_time else 'N/A'}",
        f"End Time     : {run.end_time.isoformat() if run.end_time else 'N/A'}",
        "",
        "[Target Configuration]",
        json.dumps(target_cfg, indent=2),
        "",
        "[Parameters]",
        json.dumps(params, indent=2),
    ]

    if run.failure_reason:
        lines.extend(["", "[Failure Reason]", run.failure_reason])

    return jsonify({"ok": True, "log": "\n".join(lines)})


# =========================================================
# Run creation
# =========================================================

@test_area_bp.post("/create")
def create_test():
    form = CreateTestRunForm()
    _fill_test_type_choices(form)

    if not form.validate_on_submit():
        flash("Please fix the form errors and try again.", "error")
        active_run = _get_active_run()
        return (
            render_template("test_create.html", form=form, active_run=active_run),
            400,
        )

    area = form.test_area.data
    test_type = form.test_type.data
    runner_mode = form.runner_mode.data

    active_run = _get_active_run()
    if active_run:
        flash(
            f"Another test is already active: {active_run.test_name} ({active_run.test_id}).",
            "error",
        )
        return (
            render_template("test_create.html", form=form, active_run=active_run),
            409,
        )

    target_cfg = _build_target_config(form)

    ok, message = _validate_target_config(target_cfg)
    if not ok:
        flash(message, "error")
        return (
            render_template("test_create.html", form=form, active_run=None),
            400,
        )

    ok, message = _validate_runner_mode(area, test_type, runner_mode)
    if not ok:
        flash(message, "error")
        return (
            render_template("test_create.html", form=form, active_run=None),
            400,
        )

    if form.level.data == "full" and (form.baseline_seconds.data or 0) < 60:
        flash(
            "Full phase requires a mandatory baseline of at least 60 seconds.",
            "error",
        )
        return (
            render_template("test_create.html", form=form, active_run=None),
            400,
        )

    test_id = str(uuid.uuid4())
    tax_name = _make_taxonomy_run_name(area, test_type)
    params = _build_parameters(form)

    run = TestRun(
        test_id=test_id,
        test_area=area,
        test_name=tax_name,
        test_parameters=json.dumps(params),
        target_config=json.dumps(target_cfg),
        execution_state="QUEUED",
        start_time=None,
        end_time=None,
        failure_reason=None,
    )

    db.session.add(run)
    db.session.commit()

    flash(f"Test run created successfully: {tax_name}", "success")
    return redirect(url_for("test_area.test_created", test_id=test_id))


# =========================================================
# Start / Stop / Cancel
# =========================================================

@test_area_bp.post("/start/<test_id>")
def start_test(test_id: str):
    """
    Start a test run through the runner service.
    """
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    ok, message = start_test_run(run)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    updated_run = db.session.get(TestRun, test_id)

    return jsonify(
        {
            "ok": True,
            "message": message,
            "run": _serialize_run(updated_run) if updated_run else None,
        }
    )


@test_area_bp.post("/stop/<test_id>")
def stop_test(test_id: str):
    """
    Request a graceful stop through the runner service.
    """
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    ok, message = stop_test_run(test_id)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    updated_run = db.session.get(TestRun, test_id)

    return jsonify(
        {
            "ok": True,
            "message": message,
            "run": _serialize_run(updated_run) if updated_run else None,
        }
    )


@test_area_bp.post("/cancel/<test_id>")
def cancel_test(test_id: str):
    """
    Cancel a test run through the runner service.
    """
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    ok, message = cancel_test_run(test_id)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    updated_run = db.session.get(TestRun, test_id)

    return jsonify(
        {
            "ok": True,
            "message": message,
            "run": _serialize_run(updated_run) if updated_run else None,
        }
    )


# =========================================================
# Demo completion / failure endpoints
# These are optional helpers while the runner engine is not yet built.
# =========================================================

@test_area_bp.post("/complete/<test_id>")
def complete_test(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    if run.execution_state not in {"BASELINE", "RUNNING", "STOPPING"}:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": f"Run cannot be completed from state {run.execution_state}.",
                }
            ),
            400,
        )

    run.execution_state = "COMPLETED"
    run.end_time = _utcnow()
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "message": f"Run {run.test_name} marked as completed.",
            "run": _serialize_run(run),
        }
    )


@test_area_bp.post("/fail/<test_id>")
def fail_test(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

        reason = None

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason")

    if not reason:
        reason = request.form.get("reason")

    if not reason:
        reason = "Run failed."
    if not reason:
        reason = "Run failed."

    run.execution_state = "FAILED"
    run.end_time = _utcnow()
    run.failure_reason = reason
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "message": f"Run {run.test_name} marked as failed.",
            "run": _serialize_run(run),
        }
    )