"""
Authentication Routes for MediScan AI
Handles JWT-based login, signup, and profile management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

from database import db, User, hash_password

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    age = data.get('age')
    gender = data.get('gender')
    phone = data.get('phone')
    
    # Handle empty numeric/optional fields
    if age == '' or age is None:
        age_val = None
    else:
        try:
            age_val = int(age)
        except (ValueError, TypeError):
            age_val = None

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
        
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
        
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
        
    try:
        new_user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            age=age_val,
            gender=gender,
            phone=phone
        )
        
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Signup Database Error: {str(e)}")
        return jsonify({'error': 'Internal server error during registration'}), 500
    
    access_token = create_access_token(identity=str(new_user.id))
    
    return jsonify({
        'message': 'User registered successfully',
        'token': access_token,
        'user': new_user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
        
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401
        
    if not user.is_active:
        return jsonify({'error': 'Your account is deactivated. Please contact support.'}), 403
        
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Login successful',
        'token': access_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify({'user': user.to_dict()}), 200

@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if 'name' in data: user.name = data['name'].strip()
    if 'age' in data: user.age = data['age']
    if 'gender' in data: user.gender = data['gender']
    if 'phone' in data: user.phone = data['phone']
    
    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        user.password_hash = hash_password(data['password'])
        
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200
