from flask import Blueprint

ui_bp = Blueprint("ui", __name__)

from .test_area.routes import test_area_bp  # noqa