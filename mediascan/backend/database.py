"""
SQLAlchemy Models for MediScan AI.
Supports both SQLite (local dev / tests) and PostgreSQL (production via Supabase).
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import logging
from werkzeug.security import generate_password_hash
from sqlalchemy import text, inspect, event
from sqlalchemy.engine import Engine
import sqlite3

logger = logging.getLogger(__name__)

def hash_password(password):
    try:
        return generate_password_hash(password)
    except (AttributeError, ValueError):
        return generate_password_hash(password, method="pbkdf2:sha256")


db = SQLAlchemy()


# Enable WAL mode for SQLite (improves concurrent reads; no-op on Postgres)
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="user", server_default="user")
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, server_default="true")
    
    # Relationships
    predictions = db.relationship('Prediction', backref='user', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'age': self.age,
            'gender': self.gender,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(64), nullable=False)
    
    # Image Paths
    eye_image_path = db.Column(db.String(256))
    palm_image_path = db.Column(db.String(256))
    retina_image_path = db.Column(db.String(256))
    skin_image_path = db.Column(db.String(256))
    
    # GradCAM Paths
    eye_gradcam_path = db.Column(db.String(256))
    palm_gradcam_path = db.Column(db.String(256))
    retina_gradcam_path = db.Column(db.String(256))
    skin_gradcam_path = db.Column(db.String(256))
    
    # Individual Predictions
    eye_prediction = db.Column(db.String(20))
    eye_confidence = db.Column(db.Float)
    palm_prediction = db.Column(db.String(20))
    palm_confidence = db.Column(db.Float)
    retina_prediction = db.Column(db.String(20))
    retina_confidence = db.Column(db.Float)
    skin_prediction = db.Column(db.String(20))
    skin_confidence = db.Column(db.Float)
    
    # Fused Results
    anemia_result = db.Column(db.String(20))
    anemia_confidence = db.Column(db.Float)
    anemia_risk = db.Column(db.String(10))
    
    diabetes_result = db.Column(db.String(20))
    diabetes_confidence = db.Column(db.Float)
    diabetes_risk = db.Column(db.String(10))
    
    dfu_result = db.Column(db.String(20))
    dfu_confidence = db.Column(db.Float)
    dfu_risk = db.Column(db.String(10))
    
    overall_risk = db.Column(db.String(10))
    model_type = db.Column(db.String(20), default='fusion') # Added for single scan tracking
    recommendations = db.Column(db.Text)  # JSON string
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='completed')

    def to_dict(self):
        # Determine primary URLs based on model_type
        # For single scans, we use the specific model. For fusion, we pick the first available image.
        image_key = self.model_type if self.model_type in ['eye', 'palm', 'retina', 'skin'] else None
        
        if image_key:
            image_path = getattr(self, f"{image_key}_image_path")
            gradcam_path = getattr(self, f"{image_key}_gradcam_path")
        else:
            # Multi-image/Fusion fallback: Pick the first non-null available path
            image_path = self.eye_image_path or self.palm_image_path or self.retina_image_path or self.skin_image_path
            gradcam_path = self.eye_gradcam_path or self.palm_gradcam_path or self.retina_gradcam_path or self.skin_gradcam_path
        
        # Primary confidence based on model_type
        if self.model_type == 'eye':
            prim_conf = self.eye_confidence
        elif self.model_type == 'palm':
            prim_conf = self.palm_confidence
        elif self.model_type == 'retina':
            prim_conf = self.retina_confidence
        elif self.model_type == 'skin':
            prim_conf = self.skin_confidence
        else:
            prim_conf = max(filter(None, [self.eye_confidence, self.palm_confidence, self.retina_confidence, self.skin_confidence]), default=0.0)

        # Authoritative Selection Logic (Improved Multi-Domain Support)
        # We now avoid hard-masking "Not Scanned" if data actually exists for that domain
        if self.model_type in ['palm', 'eye']:
            primary_diag = "Anemia"
            primary_stat = self.anemia_result or "Not Detected"
            primary_risk = self.anemia_risk or "none"
        elif self.model_type == 'skin':
            primary_diag = "Diabetes"
            primary_stat = self.dfu_result or "Not Detected"
            primary_risk = self.dfu_risk or "none"
        elif self.model_type == 'retina':
            primary_diag = "Diabetes"
            primary_stat = self.diabetes_result or "Not Detected"
            primary_risk = self.diabetes_risk or "none"
        else: # Fusion/History
            primary_diag = "Health Analysis"
            primary_stat = "Multi-Domain"
            primary_risk = self.overall_risk or "none"

        # Safe recommendation parsing (Handles legacy plain-text and new JSON lists)
        recs_list = []
        if self.recommendations:
            try:
                decoded = json.loads(self.recommendations)
                if isinstance(decoded, list):
                    recs_list = decoded
                else:
                    recs_list = [str(decoded)]
            except (json.JSONDecodeError, TypeError):
                # Fallback for legacy plain-text recommendations
                recs_list = [r.strip() for r in self.recommendations.split('•') if r.strip()]
                if not recs_list:
                    recs_list = [self.recommendations]

        # Detailed Display Mapping (Relaxed fallback)
        anemia_disp = self.anemia_result or ("Not Detected" if self.model_type in ['eye', 'palm'] else "Not Scanned")
        anemia_risk_disp = self.anemia_risk or "none"
        
        # Diabetes display prefers clinical diabetes_result, then DFU result
        diabetes_disp = self.diabetes_result or (self.dfu_result if self.dfu_result and self.dfu_result != 'Not Scanned' else "Not Scanned")
        diabetes_risk_disp = self.diabetes_risk or (self.dfu_risk if self.dfu_risk and self.dfu_risk != 'Low' else "none")

        data = {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'model_type': self.model_type,
            'image_url': f"/api/uploads/{image_path}" if image_path else None,
            'heatmap_url': f"/api/uploads/{gradcam_path}" if gradcam_path else None,
            'confidence': prim_conf or 0.0,
            
            # Authoritative Result (Main Display)
            'primary_diagnosis': primary_diag,
            'primary_status': primary_stat,
            'primary_risk_level': primary_risk,
            
            # Detailed Classification Result (Internal/History)
            'anemia_status': anemia_disp,
            'anemia_risk': anemia_risk_disp,
            'diabetes_status': diabetes_disp,
            'diabetes_risk': diabetes_risk_disp,
            'dfu_status': self.dfu_result or "Not Scanned",
            'dfu_risk': self.dfu_risk or "none",
            
            'overall_risk': self.overall_risk,
            'recommendations': " • ".join(recs_list),
            'interpretation': f"Final neural consensus identified {primary_stat} markers in the {self.model_type} domain. Clinical risk is assessed as {primary_risk}.",
            'images': {
                'eye': f"/api/uploads/{self.eye_image_path}" if self.eye_image_path else None,
                'palm': f"/api/uploads/{self.palm_image_path}" if self.palm_image_path else None,
                'retina': f"/api/uploads/{self.retina_image_path}" if self.retina_image_path else None,
                'skin': f"/api/uploads/{self.skin_image_path}" if self.skin_image_path else None
            },
            'gradcams': {
                'eye': f"/api/uploads/{self.eye_gradcam_path}" if self.eye_gradcam_path else None,
                'palm': f"/api/uploads/{self.palm_gradcam_path}" if self.palm_gradcam_path else None,
                'retina': f"/api/uploads/{self.retina_gradcam_path}" if self.retina_gradcam_path else None,
                'skin': f"/api/uploads/{self.skin_gradcam_path}" if self.skin_gradcam_path else None
            },
            'results': {
                'eye': {'prediction': self.eye_prediction, 'confidence': self.eye_confidence},
                'palm': {'prediction': self.palm_prediction, 'confidence': self.palm_confidence},
                'retina': {'prediction': self.retina_prediction, 'confidence': self.retina_confidence},
                'skin': {'prediction': self.skin_prediction, 'confidence': self.skin_confidence}
            },
            'summary': {
                'anemia': {'result': self.anemia_result, 'confidence': self.anemia_confidence, 'risk': self.anemia_risk},
                'diabetes': {'result': self.diabetes_result, 'confidence': self.diabetes_confidence, 'risk': self.diabetes_risk},
                'dfu': {'result': self.dfu_result, 'confidence': self.dfu_confidence, 'risk': self.dfu_risk},
                'overall_risk': self.overall_risk
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': getattr(self, 'status', 'completed')
        }
        
        # Build Multi-Image List (Domain, Scan, GradCAM triplet)
        multi_images = []
        for domain in ['eye', 'palm', 'retina', 'skin']:
            img_path = getattr(self, f"{domain}_image_path")
            grad_path = getattr(self, f"{domain}_gradcam_path")
            if img_path:
                multi_images.append({
                    'domain': domain,
                    'image_url': f"/api/uploads/{img_path}",
                    'heatmap_url': f"/api/uploads/{grad_path}" if grad_path else None,
                    'name': f"{domain.capitalize()} Analysis"
                })
        data['multi_images'] = multi_images
        
        return data

def _is_sqlite(engine) -> bool:
    return engine.dialect.name == "sqlite"


def init_db(app):
    """
    Initialise the database on startup.

    Strategy:
      - SQLite (local dev / CI): call db.create_all() so tests work without
        running `flask db upgrade`.  We also apply lightweight ALTER TABLE
        migrations for columns added after the initial release.
      - PostgreSQL (production): skip create_all(); rely exclusively on
        `flask db upgrade` (Alembic) to manage schema.  create_all() on an
        already-running Postgres DB is a no-op when tables exist, but it
        can mis-detect column differences and produce incorrect DDL.
    """
    with app.app_context():
        if _is_sqlite(db.engine):
            # ── SQLite only ────────────────────────────────────────────── #
            db.create_all()

            # Back-fill columns added after the initial schema
            try:
                columns = [c["name"] for c in inspect(db.engine).get_columns("predictions")]

                if "model_type" not in columns:
                    try:
                        db.session.execute(
                            text("ALTER TABLE predictions ADD COLUMN model_type VARCHAR(20) DEFAULT 'fusion'")
                        )
                        db.session.commit()
                        logger.info("Migration: Added model_type column.")
                    except Exception as e:
                        db.session.rollback()
                        logger.error("Migration error (model_type): %s", e)

                if "status" not in columns:
                    try:
                        db.session.execute(
                            text("ALTER TABLE predictions ADD COLUMN status VARCHAR(20) DEFAULT 'completed'")
                        )
                        db.session.commit()
                        logger.info("Migration: Added status column.")
                    except Exception as e:
                        db.session.rollback()
                        logger.error("Migration error (status): %s", e)
            except Exception as e:
                logger.error("Column inspection failed: %s", e)

        # ── Both backends ──────────────────────────────────────────────── #
        # Idempotent admin seeding: only insert if the row is absent.
        try:
            admin = User.query.filter(
                User.email == "admin@mediascan.ai"
            ).first()
            if not admin:
                admin = User(
                    name="Systems Administrator",
                    email="admin@mediascan.ai",
                    password_hash=hash_password("Admin@123"),
                    role="admin",
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user seeded: admin@mediascan.ai")
        except Exception as e:
            db.session.rollback()
            logger.error("Admin seeding failed: %s", e)
