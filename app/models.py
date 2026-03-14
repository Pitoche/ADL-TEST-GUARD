from .extensions import db


class TestRun(db.Model):
    __tablename__ = "test_runs"

    # Primary key
    test_id = db.Column(db.String, primary_key=True)

    # Basic identification
    test_area = db.Column(db.String, nullable=False)
    test_name = db.Column(db.String, nullable=False)

    # JSON stored as TEXT
    test_parameters = db.Column(db.Text, nullable=False)
    target_config = db.Column(db.Text, nullable=False)

    # Execution state
    execution_state = db.Column(
        db.String,
        nullable=False
    )

    # Timing
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)

    # Optional failure info
    failure_reason = db.Column(db.Text)