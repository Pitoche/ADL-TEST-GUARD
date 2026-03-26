import json
import uuid
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, jsonify, request

from . import test_area_bp
from .forms import CreateTestRunForm

from ...extensions import db
from ...models import TestRun
from ...services.test_taxonomy import (
    test_types_for_area,
    get_test_spec,
    default_runner_mode,
    internal_test_type_for_area,
    get_area_meta,
)
from ...services.test_runner import (
    validate_target_config,
    start_test_run,
    stop_test_run,
    cancel_test_run,
    get_run_log_tail,
)


from app.services.test_runner import RUNNING_PROCESSES, REGISTRY_LOCK

ACTIVE_STATES = {"QUEUED", "BASELINE", "RUNNING", "STOPPING"}


def _utcnow_str():
    return datetime.now(timezone.utc).isoformat()


def _safe_ts(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _fill_test_type_choices(form: CreateTestRunForm):
    area = form.test_area.data or "TA1"
    choices = test_types_for_area(area)
    form.test_type.choices = choices

    if choices:
        valid_values = [choice[0] for choice in choices]
        if form.test_type.data not in valid_values:
            form.test_type.data = valid_values[0]
    else:
        # TA1 / TA3: no visible subtype in the UI
        form.test_type.data = ""


def _split_endpoints(raw_text: str):
    if not raw_text:
        return []
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def _take_field(form: CreateTestRunForm, field_name: str):
    if not hasattr(form, field_name):
        return None
    return getattr(form, field_name).data


def _build_target_config(form: CreateTestRunForm):
    raw_endpoints = form.endpoints.data

    endpoints = _split_endpoints(raw_endpoints)

    # ---------------------------------------------------------
    # CRITICAL FIX:
    # If no endpoint provided → default to "/"
    # ---------------------------------------------------------
    if not endpoints or all(not str(ep).strip() for ep in endpoints):
        endpoints = ["/"]

    return {
        "protocol": (form.protocol.data or "http").strip().lower(),
        "host": (form.host.data or "").strip(),
        "port": form.port.data,
        "endpoints": endpoints,
    }


def _resolved_test_type(area: str, selected_test_type: str | None):
    return internal_test_type_for_area(area, selected_test_type)


def _build_parameters(form: CreateTestRunForm):
    area = form.test_area.data
    selected_test_type = form.test_type.data or None
    resolved_test_type = _resolved_test_type(area, selected_test_type)
    spec = get_test_spec(area, selected_test_type)
    taxonomy_fields = spec.get("fields", {})

    params = {
        "level": form.level.data,
        "baseline_seconds": form.baseline_seconds.data,
        "dry_run": bool(form.dry_run.data),
        "escalation_schedule": (form.escalation_schedule.data or "").strip(),
        "custom_flags": (form.custom_flags.data or "").strip(),
        "notes": (form.notes.data or "").strip(),
        "selected_test_type": selected_test_type,
        "resolved_test_type": resolved_test_type,
        "runner_mode": default_runner_mode(area, selected_test_type),
    }

    for field_name, meta in taxonomy_fields.items():
        value = _take_field(form, field_name)
        if value in (None, ""):
            continue
        params[field_name] = bool(value) if meta.get("type") == "bool" else value

    return params


def _make_taxonomy_run_name(area: str, selected_test_type: str | None):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    resolved = _resolved_test_type(area, selected_test_type)
    if resolved == "__default__" or not selected_test_type:
        return f"{area}-{ts}"
    return f"{area}-{selected_test_type}-{ts}"


def _serialize_run(run: TestRun):
    try:
        params = json.loads(run.test_parameters) if run.test_parameters else {}
    except Exception:
        params = {}

    try:
        target_cfg = json.loads(run.target_config) if run.target_config else {}
    except Exception:
        target_cfg = {}

    return {
        "test_id": run.test_id,
        "test_area": run.test_area,
        "test_name": run.test_name,
        "execution_state": run.execution_state,
        "start_time": _safe_ts(run.start_time),
        "end_time": _safe_ts(run.end_time),
        "failure_reason": run.failure_reason,
        "test_parameters": params,
        "target_config": target_cfg,
    }


def _get_active_run():
    return ( 
        db.session.query(TestRun)
        .filter(TestRun.execution_state.in_(ACTIVE_STATES))
        .order_by(TestRun.test_id.desc())
        .first()
    )

@test_area_bp.get("/dashboard")
def dashboard():
    runs = TestRun.query.all()
    total_runs = len(runs)

    active_run = next(
        (r for r in runs if r.execution_state in {"QUEUED", "RUNNING", "BASELINE", "STOPPING"}),
        None
    )

    return render_template(
        "dashboard.html",
        total_runs=total_runs,
        active_test_name=active_run.test_name if active_run else "None",
        detection_status="Monitoring",
        last_alert_level="Low",
        avg_response_time="-",
        error_rate="-",
        cpu_usage="-",
        memory_usage="-",
    )


@test_area_bp.get("/new")
def new_test():
    form = CreateTestRunForm()
    _fill_test_type_choices(form)
    active_run = _get_active_run()
    return render_template(
        "test_create.html",
        form=form,
        active_run=active_run,
        taxonomy_meta={area: get_area_meta(area) for area, _ in form.test_area.choices},
    )


@test_area_bp.get("/created/<test_id>")
def test_created(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        flash("Run not found.", "error")
        return redirect(url_for("test_area.new_test"))
    return render_template("test_created.html", run=run)


@test_area_bp.get("/subtypes/<area>")
def subtypes(area: str):
    return jsonify(test_types_for_area(area))


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
            "default_runner": spec.get("default_runner", ""),
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
    selected_test_type = form.test_type.data or None
    resolved_test_type = _resolved_test_type(area, selected_test_type)
    resolved_runner = default_runner_mode(area, selected_test_type)
    target_cfg = _build_target_config(form)

    ok, message = validate_target_config(target_cfg)
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

    return jsonify(
        {
            "ok": True,
            "message": "Validation successful.",
            "target_config": target_cfg,
            "parameters": _build_parameters(form),
            "test_area": area,
            "selected_test_type": selected_test_type,
            "resolved_test_type": resolved_test_type,
            "resolved_runner": resolved_runner,
        }
    )


from flask import request, render_template
from sqlalchemy import asc, desc

@test_area_bp.get("/runs")
def list_runs():
    # ----------------------------
    # Query params
    # ----------------------------
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    sort_by = request.args.get("sort_by", "start_time")
    sort_dir = request.args.get("sort_dir", "desc")

    test_area = request.args.get("test_area", "").strip()
    start_date = request.args.get("start_date", "").strip()

    # ----------------------------
    # Base query
    # ----------------------------
    query = TestRun.query

    # ----------------------------
    # Filters
    # ----------------------------
    if test_area:
        query = query.filter(TestRun.test_area == test_area)

    if start_date:
        query = query.filter(TestRun.start_time >= start_date)

    # ----------------------------
    # Sorting (DB-level, not Python)
    # ----------------------------
    allowed_sort_columns = {
        "test_id": TestRun.test_id,
        "test_area": TestRun.test_area,
        "test_name": TestRun.test_name,
        "execution_state": TestRun.execution_state,
        "start_time": TestRun.start_time,
        "end_time": TestRun.end_time,
    }

    sort_column = allowed_sort_columns.get(sort_by, TestRun.start_time)

    if sort_dir == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # ----------------------------
    # Pagination
    # ----------------------------
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    runs = pagination.items

    # ----------------------------
    # Render
    # ----------------------------
    return render_template(
        "test_runs.html",
        runs=runs,
        pagination=pagination,
        per_page=per_page,
        sort_by=sort_by,
        sort_dir=sort_dir,
        test_area=test_area,
        start_date=start_date,
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
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    log_tail = get_run_log_tail(test_id)
    if log_tail and "No log file exists" not in log_tail:
        return jsonify({"ok": True, "log": log_tail})

    lines = [
        f"Test ID      : {run.test_id}",
        f"Test Name    : {run.test_name}",
        f"Area         : {run.test_area}",
        f"State        : {run.execution_state}",
        f"Start Time   : {_safe_ts(run.start_time) or 'N/A'}",
        f"End Time     : {_safe_ts(run.end_time) or 'N/A'}",
        "",
        "[Target Configuration]",
        run.target_config or "{}",
        "",
        "[Parameters]",
        run.test_parameters or "{}",
    ]
    if run.failure_reason:
        lines.extend(["", "[Failure Reason]", run.failure_reason])
    return jsonify({"ok": True, "log": "\n".join(lines)})


@test_area_bp.post("/create")
def create_test():
    form = CreateTestRunForm()
    _fill_test_type_choices(form)

    if not form.validate_on_submit():
        flash("Please fix the form errors and try again.", "error")
        return (
            render_template(
                "test_create.html",
                form=form,
                active_run=_get_active_run(),
                taxonomy_meta={area: get_area_meta(area) for area, _ in form.test_area.choices},
            ),
            400,
        )

    active_run = _get_active_run()
    if active_run:
        flash(
            f"Another test is already active: {active_run.test_name} ({active_run.test_id}).",
            "error",
        )
        return (
            render_template(
                "test_create.html",
                form=form,
                active_run=active_run,
                taxonomy_meta={area: get_area_meta(area) for area, _ in form.test_area.choices},
            ),
            409,
        )

    target_cfg = _build_target_config(form)
    ok, message = validate_target_config(target_cfg)
    if not ok:
        flash(message, "error")
        return (
            render_template(
                "test_create.html",
                form=form,
                active_run=None,
                taxonomy_meta={area: get_area_meta(area) for area, _ in form.test_area.choices},
            ),
            400,
        )

    if form.level.data == "full" and (form.baseline_seconds.data or 0) < 60:
        flash("Full phase requires a mandatory baseline of at least 60 seconds.", "error")
        return (
            render_template(
                "test_create.html",
                form=form,
                active_run=None,
                taxonomy_meta={area: get_area_meta(area) for area, _ in form.test_area.choices},
            ),
            400,
        )

    area = form.test_area.data
    selected_test_type = form.test_type.data or None
    test_id = str(uuid.uuid4())
    tax_name = _make_taxonomy_run_name(area, selected_test_type)
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

    #  START THE TEST 
    result = start_test_run(run)

    if not result.get("ok"):
        run.execution_state = "FAILED"
        run.failure_reason = result.get("message", "Failed to start test")
        db.session.commit()
        flash(f"Test created but FAILED to start: {run.failure_reason}", "error")
    else:
        flash(f"Test run created and started: {tax_name}", "success")

    return redirect(url_for("test_area.test_created", test_id=test_id))


@test_area_bp.post("/start/<test_id>")
def start_test(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    try:
        ok, message = start_test_run(run)
    except Exception as exc:
        current_app.logger.exception("Failed to start test %s", test_id)
        return jsonify({"ok": False, "message": f"Internal error starting run: {exc}"}), 500

    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    updated_run = db.session.get(TestRun, test_id)
    return jsonify({
        "ok": True,
        "message": message,
        "run": _serialize_run(updated_run) if updated_run else None,
    }), 200

@test_area_bp.post("/stop/<test_id>")
def stop_test(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    ok, message = stop_test_run(test_id)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    updated_run = db.session.get(TestRun, test_id)
    return jsonify({"ok": True, "message": message, "run": _serialize_run(updated_run) if updated_run else None})


@test_area_bp.post("/cancel/<test_id>")
def cancel_test(test_id: str):
    run = db.session.get(TestRun, test_id)
    if not run:
        return jsonify({"ok": False, "message": "Run not found."}), 404

    ok, message = cancel_test_run(test_id)
    if not ok:
        return jsonify({"ok": False, "message": message}), 400

    updated_run = db.session.get(TestRun, test_id)
    return jsonify({"ok": True, "message": message, "run": _serialize_run(updated_run) if updated_run else None})


@test_area_bp.route("/runs/cleanup-stale", methods=["POST"])
def cleanup_stale_runs():
    stale_runs = TestRun.query.filter(
        TestRun.execution_state.in_(["QUEUED", "RUNNING", "BASELINE", "STOPPING"])
    ).all()

    cleaned_count = 0
    now = datetime.now(timezone.utc)

    for run in stale_runs:
        run.execution_state = "FAILED"
        run.end_time = now
        if not run.failure_reason:
            run.failure_reason = "Manually cleared stale run from UI"
        cleaned_count += 1

    db.session.commit()

    with REGISTRY_LOCK:
        RUNNING_PROCESSES.clear()

    if cleaned_count:
        flash(f"{cleaned_count} stale run(s) were cleaned successfully.", "success")
    else:
        flash("No stale runs were found.", "info")

    return redirect(url_for("test_area.list_runs"))