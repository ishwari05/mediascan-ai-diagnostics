"""
MediScan AI - Backend Application Factory
Main entry point for the Flask-based health diagnostics API.
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from datetime import timedelta
from dotenv import load_dotenv

# Load Local Imports
from database import db, init_db
from routes import auth_bp, predictions_bp, reports_bp, admin_bp, chatbot_bp, ml_bp
from models.ai_models import model_manager


def _resolve_database_url(raw_url: str) -> tuple[str, bool]:
    """
    Return (resolved_url, is_postgres).

    SQLAlchemy 1.4+ requires "postgresql://" but Supabase / Heroku / Render
    connection strings ship with the legacy "postgres://" scheme.  We fix
    that here so the app never blows up regardless of what the env var says.
    """
    if raw_url.startswith("postgres://"):
        raw_url = "postgresql://" + raw_url[len("postgres://"):]
    is_postgres = raw_url.startswith("postgresql://")
    return raw_url, is_postgres


def create_app():
    # Load environment variables
    load_dotenv()

    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    # Database URL — resolve "postgres://" → "postgresql://"              #
    # ------------------------------------------------------------------ #
    raw_db_url = os.getenv("DATABASE_URL", "sqlite:///mediascan.db")
    db_url, is_postgres = _resolve_database_url(raw_db_url)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if is_postgres:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,       # drop stale connections immediately
            "pool_recycle": 300,         # recycle connections every 5 min
            "pool_size": 5,
            "max_overflow": 5,
            "connect_args": {"sslmode": "require"},
        }

    # ------------------------------------------------------------------ #
    # General configuration                                               #
    # ------------------------------------------------------------------ #
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "mediascan-secret-dev")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret-dev")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    app.config["MODELS_FOLDER"] = os.getenv("MODEL_DIR", os.path.join(BASE_DIR, "models"))
    app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

    # Ensure upload sub-directories exist
    for sf in ["eye", "palm", "retina", "skin", "gradcam", "temp"]:
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sf), exist_ok=True)

    # ------------------------------------------------------------------ #
    # Extensions                                                          #
    # ------------------------------------------------------------------ #
    CORS(app)
    db.init_app(app)
    Migrate(app, db)          # enables `flask db init / migrate / upgrade`
    JWTManager(app)

    # ------------------------------------------------------------------ #
    # Blueprints                                                          #
    # ------------------------------------------------------------------ #
    app.register_blueprint(auth_bp,         url_prefix="/api/auth")
    app.register_blueprint(predictions_bp,  url_prefix="/api/predictions")
    app.register_blueprint(reports_bp,      url_prefix="/api/reports")
    app.register_blueprint(admin_bp,        url_prefix="/api/admin")
    app.register_blueprint(chatbot_bp,      url_prefix="/api/chatbot")
    app.register_blueprint(ml_bp,           url_prefix="/api/ml")

    # ------------------------------------------------------------------ #
    # Utility routes                                                      #
    # ------------------------------------------------------------------ #
    @app.route("/api/uploads/<path:filename>")
    def serve_uploads(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/api/health")
    def health_check():
        from datetime import datetime
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "MediScan AI Backend",
            "db_backend": "postgresql" if is_postgres else "sqlite",
        }), 200

    # ------------------------------------------------------------------ #
    # Startup: DB schema + AI models                                      #
    # ------------------------------------------------------------------ #
    with app.app_context():
        init_db(app)
        model_manager.load_models(app.config["MODELS_FOLDER"])

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app = create_app()
    app.run(host="0.0.0.0", port=port)
