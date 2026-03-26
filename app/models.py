from .extensions import db
from datetime import datetime


class TestRun(db.Model):
    __tablename__ = "test_runs"

    test_id = db.Column(db.String, primary_key=True)
    test_area = db.Column(db.String, nullable=False)
    test_name = db.Column(db.String, nullable=False)

    test_parameters = db.Column(db.Text, nullable=False)
    target_config = db.Column(db.Text, nullable=False)

    execution_state = db.Column(db.String, nullable=False)

    # Kept as strings to avoid forcing a schema migration on an existing SQLite DB.
    # The service layer stores ISO-8601 timestamps here.
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)

    failure_reason = db.Column(db.Text)


