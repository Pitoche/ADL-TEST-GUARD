from flask import Flask
from .config import Config
from .extensions import db

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)


    from .ui.test_area import test_area_bp
    app.register_blueprint(test_area_bp)


    @app.get("/health")
    def health():
        return {"status": "Work In Progress. By Angel De  Luis"}

    return app