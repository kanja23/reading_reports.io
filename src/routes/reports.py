from flask import Blueprint, jsonify, request, send_file
from src.models.user import User, Report, db
import jwt
import os
from datetime import datetime, date
from src.routes.email_service import send_report_submission_confirmation
import pandas as pd
from io import BytesIO

reports_bp = Blueprint('reports', __name__)

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

@reports_bp.route('/reports', methods=['POST'])
def create_report():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    data = request.json
    itin = data.get('itin')
    report_date_str = data.get('report_date')
    percentage_attained = data.get('percentage_attained')
    reasons_not_attained = data.get('reasons_not_attained')
    notes_comments = data.get('notes_comments', '')

    if not itin or not report_date_str or percentage_attained is None:
        return jsonify({'error': 'ITIN, report date, and percentage attained are required'}), 400

    try:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    report = Report(
        itin=itin,
        report_date=report_date,
        percentage_attained=percentage_attained,
        reasons_not_attained=reasons_not_attained,
        staff_id=user.id,
        notes_comments=notes_comments
    )

    db.session.add(report)
    db.session.commit()

    # Send confirmation email
    try:
        send_report_submission_confirmation(user, report)
    except Exception as e:
        print(f"Failed to send confirmation email: {str(e)}")

    return jsonify({
        'message': 'Report submitted successfully',
        'report': report.to_dict()
    }), 201

@reports_bp.route('/reports', methods=['GET'])
def get_reports():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Get query parameters for filtering
    staff_id = request.args.get('staff_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')

    query = Report.query

    # If user is not a supervisor, only show their own reports
    if user.role not in ['Supervisor', 'Commercial Engineer']:
        query = query.filter_by(staff_id=user.id)
    elif staff_id:
        query = query.filter_by(staff_id=staff_id)

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Report.report_date >= start_date_obj)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Report.report_date <= end_date_obj)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400

    if status:
        query = query.filter_by(status=status)

    reports = query.order_by(Report.timestamp.desc()).all()
    return jsonify([report.to_dict() for report in reports])

@reports_bp.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    report = Report.query.get_or_404(report_id)
    
    # Check if user has permission to view this report
    if user.role not in ['Supervisor', 'Commercial Engineer'] and report.staff_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403

    return jsonify(report.to_dict())

@reports_bp.route('/reports/<int:report_id>', methods=['PUT'])
def update_report(report_id):
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    report = Report.query.get_or_404(report_id)
    
    # Check if user has permission to update this report
    if user.role not in ['Supervisor', 'Commercial Engineer'] and report.staff_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.json
    
    if 'status' in data:
        report.status = data['status']
    if 'notes_comments' in data:
        report.notes_comments = data['notes_comments']
    if 'percentage_attained' in data and report.staff_id == user.id:
        report.percentage_attained = data['percentage_attained']
    if 'reasons_not_attained' in data and report.staff_id == user.id:
        report.reasons_not_attained = data['reasons_not_attained']

    db.session.commit()
    return jsonify(report.to_dict())

@reports_bp.route('/reports/download', methods=['GET'])
def download_reports():
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    # Get query parameters for filtering
    format_type = request.args.get('format', 'excel')  # excel or csv
    staff_id = request.args.get('staff_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')

    query = Report.query

    # If user is not a supervisor, only show their own reports
    if user.role not in ['Supervisor', 'Commercial Engineer']:
        query = query.filter_by(staff_id=user.id)
    elif staff_id:
        query = query.filter_by(staff_id=staff_id)

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Report.report_date >= start_date_obj)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Report.report_date <= end_date_obj)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400

    if status:
        query = query.filter_by(status=status)

    reports = query.order_by(Report.timestamp.desc()).all()
    
    # Convert to DataFrame
    data = []
    for report in reports:
        data.append({
            'ID': report.id,
            'ITIN': report.itin,
            'Report Date': report.report_date.strftime('%Y-%m-%d') if report.report_date else '',
            'Percentage Attained': report.percentage_attained,
            'Reasons Not Attained': report.reasons_not_attained or '',
            'Staff Number': report.staff.staff_number if report.staff else '',
            'Timestamp': report.timestamp.strftime('%Y-%m-%d %H:%M:%S') if report.timestamp else '',
            'Status': report.status,
            'Notes/Comments': report.notes_comments or ''
        })

    df = pd.DataFrame(data)
    
    if format_type == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Reports')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'reading_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    else:
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'reading_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

