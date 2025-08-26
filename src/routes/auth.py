from flask import Blueprint, jsonify, request
from src.models.user import User, db
import jwt
from datetime import datetime, timedelta
import os

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    staff_number = data.get('staff_number')
    pin = data.get('pin')

    if not staff_number or not pin:
        return jsonify({'error': 'Staff number and PIN are required'}), 400

    user = User.query.filter_by(staff_number=staff_number).first()
    
    if not user or not user.check_pin(pin):
        return jsonify({'error': 'Invalid staff number or PIN'}), 401

    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'staff_number': user.staff_number,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, SECRET_KEY, algorithm='HS256')

    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/change_pin', methods=['POST'])
def change_pin():
    data = request.json
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 401

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    old_pin = data.get('old_pin')
    new_pin = data.get('new_pin')

    if not old_pin or not new_pin:
        return jsonify({'error': 'Old PIN and new PIN are required'}), 400

    user = User.query.get(user_id)
    if not user or not user.check_pin(old_pin):
        return jsonify({'error': 'Invalid old PIN'}), 400

    user.set_pin(new_pin)
    db.session.commit()

    return jsonify({'message': 'PIN changed successfully'}), 200

@auth_bp.route('/forgot_pin', methods=['POST'])
def forgot_pin():
    data = request.json
    staff_number = data.get('staff_number')
    security_answer = data.get('security_answer')
    new_pin = data.get('new_pin')

    if not staff_number or not security_answer or not new_pin:
        return jsonify({'error': 'Staff number, security answer, and new PIN are required'}), 400

    user = User.query.filter_by(staff_number=staff_number).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not user.check_security_answer(security_answer):
        return jsonify({'error': 'Invalid security answer'}), 400

    user.set_pin(new_pin)
    db.session.commit()

    return jsonify({'message': 'PIN reset successfully'}), 200

@auth_bp.route('/verify_token', methods=['POST'])
def verify_token():
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 401

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired', 'valid': False}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token', 'valid': False}), 401

