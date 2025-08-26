from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_number = db.Column(db.String(20), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    security_question = db.Column(db.String(255))
    security_answer_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.staff_number}>'

    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(str(pin))

    def check_pin(self, pin):
        return check_password_hash(self.pin_hash, str(pin))

    def set_security_answer(self, answer):
        self.security_answer_hash = generate_password_hash(answer.lower())

    def check_security_answer(self, answer):
        return check_password_hash(self.security_answer_hash, answer.lower())

    def to_dict(self):
        return {
            'id': self.id,
            'staff_number': self.staff_number,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    itin = db.Column(db.String(50), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    percentage_attained = db.Column(db.Float, nullable=False)
    reasons_not_attained = db.Column(db.Text)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')
    notes_comments = db.Column(db.Text)

    staff = db.relationship('User', backref=db.backref('reports', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'itin': self.itin,
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'percentage_attained': self.percentage_attained,
            'reasons_not_attained': self.reasons_not_attained,
            'staff_id': self.staff_id,
            'staff_number': self.staff.staff_number if self.staff else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'notes_comments': self.notes_comments
        }

class Anomaly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=True)
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    escalation_flag = db.Column(db.Boolean, default=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolution_status = db.Column(db.String(20), default='Open')
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    report = db.relationship('Report', backref=db.backref('anomalies', lazy=True))
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref=db.backref('assigned_anomalies', lazy=True))
    staff = db.relationship('User', foreign_keys=[staff_id], backref=db.backref('reported_anomalies', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'type': self.type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'escalation_flag': self.escalation_flag,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_staff_number': self.assigned_to.staff_number if self.assigned_to else None,
            'resolution_status': self.resolution_status,
            'staff_id': self.staff_id,
            'staff_number': self.staff.staff_number if self.staff else None
        }

class Escalation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anomaly_id = db.Column(db.Integer, db.ForeignKey('anomaly.id'), nullable=False)
    escalation_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    escalated_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resolution_status = db.Column(db.String(20), default='Pending')

    anomaly = db.relationship('Anomaly', backref=db.backref('escalations', lazy=True))
    escalated_to = db.relationship('User', backref=db.backref('escalations_received', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'anomaly_id': self.anomaly_id,
            'escalation_timestamp': self.escalation_timestamp.isoformat() if self.escalation_timestamp else None,
            'escalated_to_id': self.escalated_to_id,
            'escalated_to_staff_number': self.escalated_to.staff_number if self.escalated_to else None,
            'resolution_status': self.resolution_status
        }

