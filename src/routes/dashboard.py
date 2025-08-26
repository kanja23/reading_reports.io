from flask import Blueprint, jsonify, request
from src.models.user import User, Report, Anomaly, db
import jwt
import os
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

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

@dashboard_bp.route('/dashboard/reader', methods=['GET'])
def get_reader_dashboard():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Get current month's reports for this user
    current_month = datetime.now().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)
    
    current_month_reports = Report.query.filter(
        Report.staff_id == user.id,
        Report.report_date >= current_month
    ).all()
    
    previous_month_reports = Report.query.filter(
        Report.staff_id == user.id,
        Report.report_date >= previous_month,
        Report.report_date < current_month
    ).all()

    # Calculate average percentage for current and previous month
    current_avg = sum(r.percentage_attained for r in current_month_reports) / len(current_month_reports) if current_month_reports else 0
    previous_avg = sum(r.percentage_attained for r in previous_month_reports) / len(previous_month_reports) if previous_month_reports else 0

    # Get recent anomalies
    recent_anomalies = Anomaly.query.filter_by(staff_id=user.id).order_by(Anomaly.timestamp.desc()).limit(5).all()

    # Get pending reports
    pending_reports = Report.query.filter_by(staff_id=user.id, status='Pending').count()

    return jsonify({
        'current_month_average': round(current_avg, 2),
        'previous_month_average': round(previous_avg, 2),
        'improvement': round(current_avg - previous_avg, 2),
        'total_reports_current_month': len(current_month_reports),
        'pending_reports': pending_reports,
        'recent_anomalies': [anomaly.to_dict() for anomaly in recent_anomalies],
        'user': user.to_dict()
    })

@dashboard_bp.route('/dashboard/supervisor', methods=['GET'])
def get_supervisor_dashboard():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    if user.role not in ['Supervisor', 'Commercial Engineer']:
        return jsonify({'error': 'Permission denied'}), 403

    # Get all meter readers
    meter_readers = User.query.filter_by(role='Meter Reader').all()
    
    # Get current month data
    current_month = datetime.now().replace(day=1)
    
    reader_performance = []
    for reader in meter_readers:
        # Get current month reports
        reports = Report.query.filter(
            Report.staff_id == reader.id,
            Report.report_date >= current_month
        ).all()
        
        # Calculate average percentage
        avg_percentage = sum(r.percentage_attained for r in reports) / len(reports) if reports else 0
        
        # Get pending reports
        pending_reports = Report.query.filter_by(staff_id=reader.id, status='Pending').count()
        
        # Get open anomalies
        open_anomalies = Anomaly.query.filter_by(staff_id=reader.id, resolution_status='Open').count()
        
        # Get escalated anomalies
        escalated_anomalies = Anomaly.query.filter_by(staff_id=reader.id, escalation_flag=True).count()

        reader_performance.append({
            'staff_number': reader.staff_number,
            'staff_id': reader.id,
            'average_percentage': round(avg_percentage, 2),
            'total_reports': len(reports),
            'pending_reports': pending_reports,
            'open_anomalies': open_anomalies,
            'escalated_anomalies': escalated_anomalies
        })

    # Get overall statistics
    total_reports = Report.query.filter(Report.report_date >= current_month).count()
    total_anomalies = Anomaly.query.filter(Anomaly.timestamp >= current_month).count()
    escalated_anomalies = Anomaly.query.filter(
        Anomaly.timestamp >= current_month,
        Anomaly.escalation_flag == True
    ).count()

    # Get anomaly distribution
    anomaly_distribution = db.session.query(
        Anomaly.type,
        func.count(Anomaly.id).label('count')
    ).filter(
        Anomaly.timestamp >= current_month
    ).group_by(Anomaly.type).all()

    return jsonify({
        'reader_performance': reader_performance,
        'total_reports': total_reports,
        'total_anomalies': total_anomalies,
        'escalated_anomalies': escalated_anomalies,
        'anomaly_distribution': [{'type': item[0], 'count': item[1]} for item in anomaly_distribution],
        'user': user.to_dict()
    })

@dashboard_bp.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Get date range from query parameters
    days = int(request.args.get('days', 30))
    start_date = datetime.now() - timedelta(days=days)

    # Get reports trend
    reports_by_date = db.session.query(
        func.date(Report.report_date).label('date'),
        func.count(Report.id).label('count'),
        func.avg(Report.percentage_attained).label('avg_percentage')
    ).filter(
        Report.report_date >= start_date.date()
    ).group_by(func.date(Report.report_date)).all()

    # Get anomalies trend
    anomalies_by_date = db.session.query(
        func.date(Anomaly.timestamp).label('date'),
        func.count(Anomaly.id).label('count')
    ).filter(
        Anomaly.timestamp >= start_date
    ).group_by(func.date(Anomaly.timestamp)).all()

    return jsonify({
        'reports_trend': [
            {
                'date': item[0].isoformat() if item[0] else None,
                'count': item[1],
                'avg_percentage': round(float(item[2]), 2) if item[2] else 0
            }
            for item in reports_by_date
        ],
        'anomalies_trend': [
            {
                'date': item[0].isoformat() if item[0] else None,
                'count': item[1]
            }
            for item in anomalies_by_date
        ]
    })

