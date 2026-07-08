from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='patient')  # patient, doctor, admin
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship('HealthRecord', backref='patient', lazy=True,
                               cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='patient', lazy=True,
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class HealthRecord(db.Model):
    __tablename__ = 'health_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    heart_rate = db.Column(db.Float, nullable=False)        # bpm
    bp_systolic = db.Column(db.Float, nullable=False)       # mmHg
    bp_diastolic = db.Column(db.Float, nullable=False)      # mmHg
    temperature = db.Column(db.Float, nullable=False)       # Celsius
    oxygen_level = db.Column(db.Float, nullable=False)      # SpO2 %
    glucose_level = db.Column(db.Float, nullable=False)     # mg/dL
    weight = db.Column(db.Float)                            # kg

    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='normal')     # normal, warning, critical
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    alerts = db.relationship('Alert', backref='record', lazy=True,
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f'<HealthRecord user={self.user_id} status={self.status}>'


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('health_records.id'), nullable=True)

    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='warning')  # warning, critical
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Alert user={self.user_id} severity={self.severity} resolved={self.resolved}>'
