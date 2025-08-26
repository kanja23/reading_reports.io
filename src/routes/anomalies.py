from flask import Blueprint, jsonify, request
from src.models.user import User, Anomaly, Escalation, db
import jwt
import os
from src.routes.email_service import send_escalation_notification
from datetime import datetime, timedelta

anomalies_bp = Blueprint('anomalies', __name__)

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

def get_user_from_token(token):
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        return User.query.get(user_id)
    except:
        return None

@anomalies_bp.route('/anomalies', methods=['POST'])
def create_anomaly():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    data = request.json
    anomaly_type = data.get('type')
    description = data.get('description')
    report_id = data.get('report_id')

    if not anomaly_type:
        return jsonify({'error': 'Anomaly type is required'}), 400

    anomaly = Anomaly(
        type=anomaly_type,
        description=description,
        report_id=report_id,
        staff_id=user.id
    )

    db.session.add(anomaly)
    db.session.commit()

    return jsonify({
        'message': 'Anomaly submitted successfully',
        'anomaly': anomaly.to_dict()
    }), 201

@anomalies_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Get query parameters for filtering
    staff_id = request.args.get('staff_id')
    anomaly_type = request.args.get('type')
    resolution_status = request.args.get('resolution_status')
    escalation_flag = request.args.get('escalation_flag')

    query = Anomaly.query

    # If user is not a supervisor, only show their own anomalies
    if user.role not in ['Supervisor', 'Commercial Engineer']:
        query = query.filter_by(staff_id=user.id)
    elif staff_id:
        query = query.filter_by(staff_id=staff_id)

    if anomaly_type:
        query = query.filter_by(type=anomaly_type)

    if resolution_status:
        query = query.filter_by(resolution_status=resolution_status)

    if escalation_flag:
        escalation_flag_bool = escalation_flag.lower() == 'true'
        query = query.filter_by(escalation_flag=escalation_flag_bool)

    anomalies = query.order_by(Anomaly.timestamp.desc()).all()
    return jsonify([anomaly.to_dict() for anomaly in anomalies])

@anomalies_bp.route('/anomalies/<int:anomaly_id>', methods=['PUT'])
def update_anomaly(anomaly_id):
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Check if user has permission to update this anomaly
    if user.role not in ['Supervisor', 'Commercial Engineer'] and anomaly.staff_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.json
    
    if 'resolution_status' in data:
        anomaly.resolution_status = data['resolution_status']
    if 'assigned_to_id' in data and user.role in ['Supervisor', 'Commercial Engineer']:
        anomaly.assigned_to_id = data['assigned_to_id']
    if 'escalation_flag' in data and user.role in ['Supervisor', 'Commercial Engineer']:
        anomaly.escalation_flag = data['escalation_flag']

    db.session.commit()
    return jsonify(anomaly.to_dict())

@anomalies_bp.route('/escalate', methods=['POST'])
def escalate_anomaly():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    data = request.json
    anomaly_id = data.get('anomaly_id')
    escalated_to_id = data.get('escalated_to_id')

    if not anomaly_id or not escalated_to_id:
        return jsonify({'error': 'Anomaly ID and escalated_to_id are required'}), 400

    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Check if user has permission to escalate this anomaly
    if user.role not in ['Supervisor', 'Commercial Engineer'] and anomaly.staff_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403

    # Update anomaly escalation flag
    anomaly.escalation_flag = True
    
    # Create escalation record
    escalation = Escalation(
        anomaly_id=anomaly_id,
        escalated_to_id=escalated_to_id
    )

    db.session.add(escalation)
    db.session.commit()

    # Send escalation notification email
    try:
        escalated_to_user = User.query.get(escalated_to_id)
        if escalated_to_user:
            send_escalation_notification(anomaly, escalated_to_user)
    except Exception as e:
        print(f"Failed to send escalation email: {str(e)}")

    return jsonify({
        'message': 'Anomaly escalated successfully',
        'escalation': escalation.to_dict()
    }), 201

@anomalies_bp.route('/escalations', methods=['GET'])
def get_escalations():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Only supervisors and commercial engineers can view all escalations
    if user.role not in ['Supervisor', 'Commercial Engineer']:
        return jsonify({'error': 'Permission denied'}), 403

    escalations = Escalation.query.order_by(Escalation.escalation_timestamp.desc()).all()
    return jsonify([escalation.to_dict() for escalation in escalations])

@anomalies_bp.route('/anomalies/check_escalation', methods=['POST'])
def check_escalation():
    """Check for anomalies that need to be escalated (older than 4 days without resolution)"""
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Only supervisors and commercial engineers can trigger escalation checks
    if user.role not in ['Supervisor', 'Commercial Engineer']:
        return jsonify({'error': 'Permission denied'}), 403

    four_days_ago = datetime.utcnow() - timedelta(days=4)
    
    # Find anomalies older than 4 days that are still open and not escalated
    anomalies_to_escalate = Anomaly.query.filter(
        Anomaly.timestamp <= four_days_ago,
        Anomaly.resolution_status == 'Open',
        Anomaly.escalation_flag == False
    ).all()

    escalated_count = 0
    for anomaly in anomalies_to_escalate:
        anomaly.escalation_flag = True
        
        # Find a commercial engineer to escalate to
        commercial_engineer = User.query.filter_by(role='Commercial Engineer').first()
        if commercial_engineer:
            escalation = Escalation(
                anomaly_id=anomaly.id,
                escalated_to_id=commercial_engineer.id
            )
            db.session.add(escalation)
            escalated_count += 1
            
            # Send escalation notification email
            try:
                send_escalation_notification(anomaly, commercial_engineer)
            except Exception as e:
                print(f"Failed to send escalation email: {str(e)}")

    db.session.commit()

    return jsonify({
        'message': f'{escalated_count} anomalies escalated due to 4-day timeout',
        'escalated_count': escalated_count
    }), 200

