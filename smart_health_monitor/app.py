"""
Smart Community Health Monitoring System
------------------------------------------
A Flask web application that lets community members log their vital
health readings, automatically flags abnormal readings, generates
alerts, and gives community health workers/admins a dashboard to
monitor overall community health trends.
"""

import os
from datetime import datetime, timedelta

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

from models import db, User, HealthRecord, Alert

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'health_monitor.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --------------------------------------------------------------------------
# Normal vital ranges used to auto-classify readings
# --------------------------------------------------------------------------
NORMAL_RANGES = {
    'heart_rate': (60, 100),          # bpm
    'bp_systolic': (90, 120),         # mmHg
    'bp_diastolic': (60, 80),         # mmHg
    'temperature': (36.1, 37.5),      # Celsius
    'oxygen_level': (95, 100),        # SpO2 %
    'glucose_level': (70, 140),       # mg/dL
}


def evaluate_record(record):
    """
    Inspects a HealthRecord's vitals against NORMAL_RANGES and returns
    a (status, reasons) tuple. status is one of: normal, warning, critical
    """
    reasons = []
    critical = False
    warning = False

    checks = {
        'Heart rate': (record.heart_rate, NORMAL_RANGES['heart_rate']),
        'Systolic BP': (record.bp_systolic, NORMAL_RANGES['bp_systolic']),
        'Diastolic BP': (record.bp_diastolic, NORMAL_RANGES['bp_diastolic']),
        'Temperature': (record.temperature, NORMAL_RANGES['temperature']),
        'Oxygen level': (record.oxygen_level, NORMAL_RANGES['oxygen_level']),
        'Glucose level': (record.glucose_level, NORMAL_RANGES['glucose_level']),
    }

    for label, (value, (low, high)) in checks.items():
        if value is None:
            continue
        if value < low * 0.85 or value > high * 1.2:
            reasons.append(f"{label} critically abnormal ({value})")
            critical = True
        elif value < low or value > high:
            reasons.append(f"{label} out of normal range ({value})")
            warning = True

    if critical:
        return 'critical', reasons
    if warning:
        return 'warning', reasons
    return 'normal', reasons


# --------------------------------------------------------------------------
# Public routes
# --------------------------------------------------------------------------
@app.route('/')
def index():
    total_users = User.query.filter_by(role='patient').count()
    total_records = HealthRecord.query.count()
    active_alerts = Alert.query.filter_by(resolved=False).count()
    return render_template('index.html',
                            total_users=total_users,
                            total_records=total_records,
                            active_alerts=active_alerts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        age = request.form.get('age') or None
        gender = request.form.get('gender', '')
        phone = request.form.get('phone', '')
        role = request.form.get('role', 'patient')

        if not username or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('register'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already registered.', 'danger')
            return redirect(url_for('register'))

        # Only allow 'patient' or 'doctor' from public form; admin created separately
        if role not in ('patient', 'doctor'):
            role = 'patient'

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            age=int(age) if age else None,
            gender=gender,
            phone=phone,
            role=role,
        )
        db.session.add(user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))

        flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# --------------------------------------------------------------------------
# Patient routes
# --------------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin' or current_user.role == 'doctor':
        return redirect(url_for('admin_dashboard'))

    records = (HealthRecord.query
               .filter_by(user_id=current_user.id)
               .order_by(HealthRecord.recorded_at.desc())
               .limit(10).all())

    latest = records[0] if records else None

    alerts = (Alert.query
              .filter_by(user_id=current_user.id, resolved=False)
              .order_by(Alert.created_at.desc())
              .all())

    chart_records = list(reversed(records))
    chart_data = {
        'labels': [r.recorded_at.strftime('%d %b %H:%M') for r in chart_records],
        'heart_rate': [r.heart_rate for r in chart_records],
        'bp_systolic': [r.bp_systolic for r in chart_records],
        'bp_diastolic': [r.bp_diastolic for r in chart_records],
        'temperature': [r.temperature for r in chart_records],
        'oxygen_level': [r.oxygen_level for r in chart_records],
        'glucose_level': [r.glucose_level for r in chart_records],
    }

    return render_template('dashboard.html',
                            latest=latest,
                            records=records,
                            alerts=alerts,
                            chart_data=chart_data)


@app.route('/add_record', methods=['GET', 'POST'])
@login_required
def add_record():
    if request.method == 'POST':
        try:
            record = HealthRecord(
                user_id=current_user.id,
                heart_rate=float(request.form['heart_rate']),
                bp_systolic=float(request.form['bp_systolic']),
                bp_diastolic=float(request.form['bp_diastolic']),
                temperature=float(request.form['temperature']),
                oxygen_level=float(request.form['oxygen_level']),
                glucose_level=float(request.form['glucose_level']),
                weight=float(request.form['weight']) if request.form.get('weight') else None,
                notes=request.form.get('notes', '').strip(),
                recorded_at=datetime.utcnow(),
            )
        except (ValueError, KeyError):
            flash('Please enter valid numeric values for all vitals.', 'danger')
            return redirect(url_for('add_record'))

        status, reasons = evaluate_record(record)
        record.status = status

        db.session.add(record)
        db.session.commit()

        if status in ('warning', 'critical'):
            alert = Alert(
                user_id=current_user.id,
                record_id=record.id,
                message='; '.join(reasons) if reasons else 'Abnormal reading detected.',
                severity=status,
                created_at=datetime.utcnow(),
                resolved=False,
            )
            db.session.add(alert)
            db.session.commit()
            flash(f'Record saved. Status: {status.upper()} - please review your alert.', 'warning')
        else:
            flash('Health record saved. All vitals look normal!', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_record.html')


@app.route('/records')
@login_required
def records():
    page = request.args.get('page', 1, type=int)
    pagination = (HealthRecord.query
                  .filter_by(user_id=current_user.id)
                  .order_by(HealthRecord.recorded_at.desc())
                  .paginate(page=page, per_page=10, error_out=False))
    return render_template('records.html', pagination=pagination)


@app.route('/records/<int:record_id>/delete', methods=['POST'])
@login_required
def delete_record(record_id):
    record = db.session.get(HealthRecord, record_id)
    if not record or (record.user_id != current_user.id and current_user.role not in ('admin', 'doctor')):
        flash('Record not found or access denied.', 'danger')
        return redirect(url_for('records'))

    Alert.query.filter_by(record_id=record.id).delete()
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted.', 'info')
    return redirect(url_for('records'))


@app.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    alert = db.session.get(Alert, alert_id)
    if not alert or (alert.user_id != current_user.id and current_user.role not in ('admin', 'doctor')):
        flash('Alert not found or access denied.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    alert.resolved = True
    db.session.commit()
    flash('Alert marked as resolved.', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.age = request.form.get('age') or current_user.age
        current_user.gender = request.form.get('gender', current_user.gender)
        current_user.phone = request.form.get('phone', current_user.phone)
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html')


# --------------------------------------------------------------------------
# Admin / doctor routes -- community-wide monitoring
# --------------------------------------------------------------------------
def admin_required():
    return current_user.is_authenticated and current_user.role in ('admin', 'doctor')


@app.route('/admin')
@login_required
def admin_dashboard():
    if not admin_required():
        flash('Access restricted to health workers/admins.', 'danger')
        return redirect(url_for('dashboard'))

    total_patients = User.query.filter_by(role='patient').count()
    total_records = HealthRecord.query.count()
    active_alerts = Alert.query.filter_by(resolved=False).order_by(Alert.created_at.desc()).all()
    critical_count = HealthRecord.query.filter_by(status='critical').count()
    warning_count = HealthRecord.query.filter_by(status='warning').count()
    normal_count = HealthRecord.query.filter_by(status='normal').count()

    # community averages (last 30 days)
    since = datetime.utcnow() - timedelta(days=30)
    averages = db.session.query(
        func.avg(HealthRecord.heart_rate),
        func.avg(HealthRecord.bp_systolic),
        func.avg(HealthRecord.bp_diastolic),
        func.avg(HealthRecord.temperature),
        func.avg(HealthRecord.oxygen_level),
        func.avg(HealthRecord.glucose_level),
    ).filter(HealthRecord.recorded_at >= since).first()

    recent_patients = (User.query
                        .filter_by(role='patient')
                        .order_by(User.created_at.desc())
                        .limit(10).all())

    return render_template('admin_dashboard.html',
                            total_patients=total_patients,
                            total_records=total_records,
                            active_alerts=active_alerts,
                            critical_count=critical_count,
                            warning_count=warning_count,
                            normal_count=normal_count,
                            averages=averages,
                            recent_patients=recent_patients)


@app.route('/admin/patients')
@login_required
def admin_patients():
    if not admin_required():
        flash('Access restricted to health workers/admins.', 'danger')
        return redirect(url_for('dashboard'))

    patients = User.query.filter_by(role='patient').order_by(User.username).all()
    return render_template('admin_patients.html', patients=patients)


@app.route('/admin/patients/<int:user_id>')
@login_required
def admin_patient_detail(user_id):
    if not admin_required():
        flash('Access restricted to health workers/admins.', 'danger')
        return redirect(url_for('dashboard'))

    patient = db.session.get(User, user_id)
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('admin_patients'))

    patient_records = (HealthRecord.query
                        .filter_by(user_id=patient.id)
                        .order_by(HealthRecord.recorded_at.desc())
                        .limit(20).all())
    patient_alerts = (Alert.query
                       .filter_by(user_id=patient.id)
                       .order_by(Alert.created_at.desc())
                       .all())

    return render_template('admin_patient_detail.html',
                            patient=patient,
                            records=patient_records,
                            alerts=patient_alerts)


# --------------------------------------------------------------------------
# Simple JSON API (bonus, useful for IoT devices / mobile apps)
# --------------------------------------------------------------------------
@app.route('/api/records', methods=['POST'])
@login_required
def api_add_record():
    data = request.get_json(silent=True) or {}
    required = ['heart_rate', 'bp_systolic', 'bp_diastolic', 'temperature', 'oxygen_level', 'glucose_level']
    if not all(k in data for k in required):
        return jsonify({'error': 'missing fields', 'required': required}), 400

    record = HealthRecord(
        user_id=current_user.id,
        heart_rate=data['heart_rate'],
        bp_systolic=data['bp_systolic'],
        bp_diastolic=data['bp_diastolic'],
        temperature=data['temperature'],
        oxygen_level=data['oxygen_level'],
        glucose_level=data['glucose_level'],
        weight=data.get('weight'),
        notes=data.get('notes', ''),
        recorded_at=datetime.utcnow(),
    )
    status, reasons = evaluate_record(record)
    record.status = status
    db.session.add(record)
    db.session.commit()

    if status in ('warning', 'critical'):
        alert = Alert(
            user_id=current_user.id,
            record_id=record.id,
            message='; '.join(reasons),
            severity=status,
            created_at=datetime.utcnow(),
            resolved=False,
        )
        db.session.add(alert)
        db.session.commit()

    return jsonify({'id': record.id, 'status': status, 'reasons': reasons}), 201


# --------------------------------------------------------------------------
# CLI helper: create database + a default admin account
# --------------------------------------------------------------------------
@app.cli.command('init-db')
def init_db():
    """Initialize the database and create a default admin account."""
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@healthmonitor.local',
            password_hash=generate_password_hash('admin123'),
            role='admin',
        )
        db.session.add(admin)
        db.session.commit()
        print('Database initialized. Default admin created -> username: admin / password: admin123')
    else:
        print('Database initialized.')


def create_default_admin():
    """Ensure DB tables + a default admin exist (used on normal `python app.py` run)."""
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@healthmonitor.local',
            password_hash=generate_password_hash('admin123'),
            role='admin',
        )
        db.session.add(admin)
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        create_default_admin()
    app.run(debug=True)
