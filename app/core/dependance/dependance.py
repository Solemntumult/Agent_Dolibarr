import os
from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from commons.config.config import Config
from core.blueprint.blueprint import initialize_blueprint_route
from commons.errors.errors import register_error_handlers


def create_app():
    # Le module vit dans app/core/dependance/ : on remonte pour pointer vers app/templates
    # et app/static (interface web de dialogue — cahier des charges §4.4).
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )
    app.config.from_object(Config)

    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    register_error_handlers(app)
    initialize_blueprint_route(app)

    jwt = JWTManager(app)

    @app.route("/")
    def index():
        """Application web de dialogue (§4.4) — interface réservée aux utilisateurs internes."""
        return render_template("index.html")

    return app
