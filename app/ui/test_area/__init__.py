from flask import Blueprint

test_area_bp = Blueprint(
    "test_area",
    __name__,
    url_prefix="/tests",
    template_folder="templates"
)

from . import routes  # noqa