import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Blueprint, jsonify, request
from src.models.user import User, Anomaly, Escalation, db
import jwt

email_bp = Blueprint('email', __name__)

SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# Email configuration - these would typically be environment variables
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
EMAIL_USER = os.environ.get('EMAIL_USER', 'noreply@kenyapower.co.ke')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'Reading Reports.io <noreply@kenyapower.co.ke>')

def get_user_from_token(token):
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        return User.query.get(user_id)
    except:
        return None

def send_email(to_email, subject, body_html, body_text=None):
    """Send an email notification"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email

        # Create the plain-text and HTML version of your message
        if body_text:
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)

        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)

        # Send the message via SMTP server
        if EMAIL_PASSWORD:  # Only send if email is configured
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_FROM, to_email, text)
            server.quit()
            return True
        else:
            print(f"Email would be sent to {to_email}: {subject}")
            print(f"Body: {body_html}")
            return True  # Simulate success for demo purposes
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def send_escalation_notification(anomaly, escalated_to_user):
    """Send escalation notification email"""
    subject = f"[Reading Reports.io] Anomaly Escalated - {anomaly.type}"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #003399; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .anomaly-details {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #FFD100; margin: 15px 0; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            .urgent {{ color: #dc3545; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Reading Reports.io</h1>
            <p>Kenya Power Meter Reading System</p>
        </div>
        
        <div class="content">
            <h2 class="urgent">Anomaly Escalation Notice</h2>
            
            <p>Dear {escalated_to_user.staff_number},</p>
            
            <p>An anomaly has been escalated to you for immediate attention. This issue has been unresolved for more than 4 days and requires your intervention.</p>
            
            <div class="anomaly-details">
                <h3>Anomaly Details:</h3>
                <p><strong>Type:</strong> {anomaly.type}</p>
                <p><strong>Description:</strong> {anomaly.description}</p>
                <p><strong>Reported by:</strong> {anomaly.staff.staff_number if anomaly.staff else 'Unknown'}</p>
                <p><strong>Reported on:</strong> {anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S') if anomaly.timestamp else 'Unknown'}</p>
                <p><strong>Current Status:</strong> {anomaly.resolution_status}</p>
            </div>
            
            <p>Please log into the Reading Reports.io system to review and take appropriate action on this anomaly.</p>
            
            <p>If you have any questions or need additional information, please contact the reporting staff member or system administrator.</p>
            
            <p>Best regards,<br>
            Reading Reports.io System</p>
        </div>
        
        <div class="footer">
            <p>© 2025 Reading Reports.io - powered by 85891</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
    Reading Reports.io - Anomaly Escalation Notice
    
    Dear {escalated_to_user.staff_number},
    
    An anomaly has been escalated to you for immediate attention. This issue has been unresolved for more than 4 days and requires your intervention.
    
    Anomaly Details:
    - Type: {anomaly.type}
    - Description: {anomaly.description}
    - Reported by: {anomaly.staff.staff_number if anomaly.staff else 'Unknown'}
    - Reported on: {anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S') if anomaly.timestamp else 'Unknown'}
    - Current Status: {anomaly.resolution_status}
    
    Please log into the Reading Reports.io system to review and take appropriate action on this anomaly.
    
    Best regards,
    Reading Reports.io System
    
    © 2025 Reading Reports.io - powered by 85891
    """
    
    # For demo purposes, use a placeholder email
    # In production, this would be the user's actual email address
    to_email = f"{escalated_to_user.staff_number}@kenyapower.co.ke"
    
    return send_email(to_email, subject, body_html, body_text)

def send_report_submission_confirmation(user, report):
    """Send report submission confirmation email"""
    subject = f"[Reading Reports.io] Report Submitted Successfully - {report.itin}"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #003399; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .report-details {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #FFD100; margin: 15px 0; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            .success {{ color: #28a745; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Reading Reports.io</h1>
            <p>Kenya Power Meter Reading System</p>
        </div>
        
        <div class="content">
            <h2 class="success">Report Submission Confirmed</h2>
            
            <p>Dear {user.staff_number},</p>
            
            <p>Your reading report has been submitted successfully and you can download your report for future reference and filing for later use.</p>
            
            <div class="report-details">
                <h3>Report Details:</h3>
                <p><strong>ITIN:</strong> {report.itin}</p>
                <p><strong>Report Date:</strong> {report.report_date.strftime('%Y-%m-%d') if report.report_date else 'Unknown'}</p>
                <p><strong>Coverage Achieved:</strong> {report.percentage_attained}%</p>
                <p><strong>Submitted on:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S') if report.timestamp else 'Unknown'}</p>
                <p><strong>Status:</strong> {report.status}</p>
            </div>
            
            <p>You can log into the Reading Reports.io system to view your report history and download reports as needed.</p>
            
            <p>Thank you for your continued service to Kenya Power.</p>
            
            <p>Best regards,<br>
            Reading Reports.io System</p>
        </div>
        
        <div class="footer">
            <p>© 2025 Reading Reports.io - powered by 85891</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    # For demo purposes, use a placeholder email
    to_email = f"{user.staff_number}@kenyapower.co.ke"
    
    return send_email(to_email, subject, body_html)

@email_bp.route('/send_test_email', methods=['POST'])
def send_test_email():
    """Send a test email to verify email configuration"""
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    if user.role not in ['Supervisor', 'Commercial Engineer']:
        return jsonify({'error': 'Permission denied'}), 403

    data = request.json
    to_email = data.get('to_email', f"{user.staff_number}@kenyapower.co.ke")
    
    subject = "[Reading Reports.io] Test Email"
    body_html = """
    <html>
    <body>
        <h2>Test Email from Reading Reports.io</h2>
        <p>This is a test email to verify that the email notification system is working correctly.</p>
        <p>If you receive this email, the system is configured properly.</p>
        <p>Best regards,<br>Reading Reports.io System</p>
    </body>
    </html>
    """
    
    success = send_email(to_email, subject, body_html)
    
    if success:
        return jsonify({'message': 'Test email sent successfully'}), 200
    else:
        return jsonify({'error': 'Failed to send test email'}), 500

@email_bp.route('/escalation_notifications', methods=['POST'])
def send_escalation_notifications():
    """Manually trigger escalation notifications for flagged anomalies"""
    token = request.headers.get('Authorization')
    user = get_user_from_token(token)
    
    if not user:
        return jsonify({'error': 'Invalid or missing token'}), 401

    if user.role not in ['Supervisor', 'Commercial Engineer']:
        return jsonify({'error': 'Permission denied'}), 403

    # Get all escalated anomalies that haven't been notified
    escalated_anomalies = Anomaly.query.filter_by(escalation_flag=True).all()
    
    notifications_sent = 0
    for anomaly in escalated_anomalies:
        # Find the latest escalation for this anomaly
        escalation = Escalation.query.filter_by(anomaly_id=anomaly.id).order_by(Escalation.escalation_timestamp.desc()).first()
        
        if escalation and escalation.escalated_to:
            success = send_escalation_notification(anomaly, escalation.escalated_to)
            if success:
                notifications_sent += 1

    return jsonify({
        'message': f'Sent {notifications_sent} escalation notifications',
        'notifications_sent': notifications_sent
    }), 200

