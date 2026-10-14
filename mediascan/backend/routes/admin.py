"""
Admin Routes for MediScan AI
Dashboard statistics and user/scan management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from database import db, User, Prediction

admin_bp = Blueprint('admin', __name__)

def admin_required(fn):
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return jwt_required()(wrapper)

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    total_users = User.query.count()
    total_scans = Prediction.query.count()
    
    anemia_cases = Prediction.query.filter_by(anemia_result='Anemic').count()
    diabetes_cases = Prediction.query.filter_by(diabetes_result='Diabetic').count()
    dfu_cases = Prediction.query.filter(Prediction.dfu_result.ilike('%abnormal%')).count()
    high_risk = Prediction.query.filter_by(overall_risk='High').count()
    
    # Recent activity (last 7 days)
    last_week = datetime.utcnow() - timedelta(days=7)
    recent_scans = Prediction.query.filter(Prediction.created_at >= last_week).count()
    new_users = User.query.filter(User.created_at >= last_week).count()
    
    return jsonify({
        'total_users': total_users,
        'total_scans': total_scans,
        'anemia_cases': anemia_cases,
        'diabetes_cases': diabetes_cases,
        'dfu_cases': dfu_cases,
        'high_risk_cases': high_risk,
        'recent_scans_week': recent_scans,
        'new_users_week': new_users
    }), 200

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    pagination = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    }), 200

@admin_bp.route('/predictions', methods=['GET'])
@admin_required
def get_all_predictions():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    pagination = Prediction.query.order_by(Prediction.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'predictions': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    }), 200

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.role == 'admin':
        return jsonify({'error': 'Cannot deactivate admin accounts'}), 400
        
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({
        'message': f"User {'activated' if user.is_active else 'deactivated'} successfully",
        'user': user.to_dict()
    }), 200
