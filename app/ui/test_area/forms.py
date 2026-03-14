from flask_wtf import FlaskForm
from wtforms import (
    SelectField,
    StringField,
    IntegerField,
    TextAreaField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import DataRequired, NumberRange, Optional, Length, IPAddress


class CreateTestRunForm(FlaskForm):
    # =========================================================
    # Core test selection
    # =========================================================
    test_area = SelectField(
        "Test Area",
        choices=[
            ("TA1", "TA1 - Volumetric Application-Layer Flood"),
            ("TA2", "TA2 - Protocol / Connection Abuse"),
            ("TA3", "TA3 - Application Logic Abuse"),
            ("TA4", "TA4 - Endpoint / API Service Abuse"),
            ("TA5", "TA5 - Adaptive / Custom Flood"),
        ],
        validators=[DataRequired()],
    )

    # Populated dynamically from routes.py using taxonomy
    test_type = SelectField(
        "Test Subtype",
        choices=[],
        validators=[DataRequired()],
    )

    level = SelectField(
        "Execution Level",
        choices=[
            ("baseline", "Baseline"),
            ("light", "Light"),
            ("medium", "Medium"),
            ("full", "Full"),
        ],
        validators=[DataRequired()],
        default="baseline",
    )

    runner_mode = SelectField(
        "Runner Mode",
        choices=[
            ("framework", "Framework-based (Locust)"),
            ("custom", "Custom-based (Python AsyncIO)"),
        ],
        validators=[DataRequired()],
        default="framework",
    )

    # =========================================================
    # Target configuration
    # =========================================================
    protocol = SelectField(
        "Protocol",
        choices=[
            ("http", "HTTP"),
            ("https", "HTTPS"),
        ],
        validators=[DataRequired()],
        default="http",
    )

    host = StringField(
        "Target Host / IP",
        validators=[
            DataRequired(),
            Length(max=255),
        ],
        render_kw={"placeholder": "e.g. 192.168.42.10 or vulnerable-app.local"},
    )

    port = IntegerField(
        "Port",
        validators=[
            DataRequired(),
            NumberRange(min=1, max=65535),
        ],
        default=80,
    )

    endpoints = TextAreaField(
        "Endpoints (one per line)",
        validators=[Optional(), Length(max=5000)],
        render_kw={
            "rows": 5,
            "placeholder": "/\n/login\n/search\n/api/v1/items"
        },
    )

    # =========================================================
    # Run controls / execution policy
    # =========================================================
    baseline_seconds = IntegerField(
        "Baseline Phase Duration (seconds)",
        validators=[
            DataRequired(),
            NumberRange(min=10, max=3600),
        ],
        default=60,
    )

    escalation_schedule = TextAreaField(
        "Escalation Schedule (optional)",
        validators=[Optional(), Length(max=2000)],
        render_kw={
            "rows": 4,
            "placeholder": "Example:\n0s=10 users\n30s=50 users\n60s=100 users"
        },
    )

    dry_run = BooleanField(
        "Dry Run / Validate only",
        default=False,
    )

    # =========================================================
    # Generic optional attack parameters
    # These are useful across several test areas
    # =========================================================
    users = IntegerField(
        "Concurrent Users / Workers",
        validators=[Optional(), NumberRange(min=1, max=100000)],
    )

    spawn_rate = IntegerField(
        "Spawn Rate / Ramp-up per second",
        validators=[Optional(), NumberRange(min=1, max=100000)],
    )

    duration_seconds = IntegerField(
        "Attack Duration (seconds)",
        validators=[Optional(), NumberRange(min=1, max=86400)],
    )

    request_timeout = IntegerField(
        "Request Timeout (seconds)",
        validators=[Optional(), NumberRange(min=1, max=600)],
        default=10,
    )

    think_time_ms = IntegerField(
        "Think Time (ms)",
        validators=[Optional(), NumberRange(min=0, max=60000)],
    )

    connection_count = IntegerField(
        "Connection Count",
        validators=[Optional(), NumberRange(min=1, max=100000)],
    )

    header_count = IntegerField(
        "Header Count",
        validators=[Optional(), NumberRange(min=1, max=1000)],
    )

    payload_size = IntegerField(
        "Payload Size (bytes)",
        validators=[Optional(), NumberRange(min=1, max=100000000)],
    )

    rate_limit = IntegerField(
        "Rate Limit (requests/sec)",
        validators=[Optional(), NumberRange(min=1, max=1000000)],
    )

    # =========================================================
    # Behaviour toggles
    # =========================================================
    keep_alive = BooleanField("Use Keep-Alive", default=True)
    follow_redirects = BooleanField("Follow Redirects", default=False)
    verify_tls = BooleanField("Verify TLS Certificate", default=False)
    randomize_endpoints = BooleanField("Randomize Endpoint Selection", default=False)
    store_artifacts = BooleanField("Store Runner Artifacts", default=True)
    collect_telemetry = BooleanField("Collect Telemetry Samples", default=True)

    # =========================================================
    # Manual / custom command section
    # For your requirement 1.3
    # =========================================================
    custom_flags = TextAreaField(
        "Custom Parameters / Flags",
        validators=[Optional(), Length(max=4000)],
        render_kw={
            "rows": 4,
            "placeholder": "--header X-Test:1\n--burst 250\n--connections 500"
        },
    )

    notes = TextAreaField(
        "Run Notes",
        validators=[Optional(), Length(max=2000)],
        render_kw={
            "rows": 3,
            "placeholder": "Optional notes for this run"
        },
    )

    # =========================================================
    # Buttons
    # =========================================================
    validate_submit = SubmitField("Validate Configuration")
    create_submit = SubmitField("Create Test Run")