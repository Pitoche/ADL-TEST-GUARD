import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

class Config:
    # Basic Flask security key (change later in production)
    SECRET_KEY = "dev-secret-key-change-later"

    # SQLite database inside instance/ folder
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(PROJECT_ROOT, "instance", "adl_guard.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Paths to your existing folders (very useful later)
    TEST_AREA_DIR = os.path.join(PROJECT_ROOT, "test-area")
    REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports-area")
    DETECTION_DIR = os.path.join(PROJECT_ROOT, "detection-area")