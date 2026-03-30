import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import TestRun  # noqa: E402


ACTIVE_STATES = {"QUEUED", "BASELINE", "RUNNING", "STOPPING"}


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(scope="session")
def app():
    os.environ.setdefault("FLASK_ENV", "testing")

    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    with app.app_context():
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_active_runs(app):
    with app.app_context():
        stale_runs = (
            TestRun.query
            .filter(TestRun.execution_state.in_(ACTIVE_STATES))
            .all()
        )

        for run in stale_runs:
            run.execution_state = "FAILED"
            run.failure_reason = "Cleared automatically by pytest fixture"
            if not run.end_time:
                run.end_time = _utcnow_iso()

        db.session.commit()

    yield

    with app.app_context():
        db.session.rollback()
