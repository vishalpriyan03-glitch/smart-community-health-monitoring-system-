# Smart Community Health Monitoring System

A full-stack Flask web application for community-level health monitoring.
Community members log their vital signs, the system auto-detects abnormal
readings and raises alerts, and health workers/admins get a real-time
dashboard of community health trends.

## Features

- **User accounts** — register/login as a Patient (community member) or Doctor/Health Worker, with secure password hashing (Werkzeug) and session management (Flask-Login).
- **Vitals tracking** — log heart rate, blood pressure, temperature, SpO2 (oxygen level), glucose, and weight.
- **Automatic risk classification** — every reading is checked against clinical normal ranges and tagged `normal`, `warning`, or `critical`.
- **Alerts** — abnormal readings automatically create an alert that patients and health workers can resolve.
- **Patient dashboard** — latest vitals, interactive Chart.js trend graph, active alerts.
- **Records history** — paginated table of all past readings, with delete support.
- **Admin/Doctor dashboard** — community-wide stats: total patients, total readings, critical/warning/normal counts, 30-day community averages, active alerts across all patients, and a per-patient detail view.
- **JSON API** (`POST /api/records`) — for future IoT/wearable device or mobile app integration.
- **Clean, responsive UI** — no external UI framework required, custom CSS.

## Tech Stack

- **Backend**: Flask 3, Flask-SQLAlchemy, Flask-Login
- **Database**: SQLite (file-based, zero config)
- **Frontend**: Jinja2 templates, vanilla CSS/JS, Chart.js (via CDN) for graphs
- **Auth**: Werkzeug password hashing + Flask-Login sessions

## Project Structure

```
smart_health_monitor/
├── app.py                  # Main Flask application (routes, logic)
├── models.py                # SQLAlchemy models: User, HealthRecord, Alert
├── requirements.txt
├── instance/                 # SQLite DB is created here automatically
├── static/
│   ├── css/style.css
│   └── js/script.js
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── add_record.html
    ├── records.html
    ├── profile.html
    ├── admin_dashboard.html
    ├── admin_patients.html
    └── admin_patient_detail.html
```

## Setup & Run

1. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python app.py
   ```
   This automatically creates the SQLite database (`instance/health_monitor.db`)
   and a default admin account on first run:
   - **Username:** `admin`
   - **Password:** `admin123`

   Alternatively, initialize explicitly with the Flask CLI:
   ```bash
   flask --app app init-db
   ```

4. **Open your browser** at `http://127.0.0.1:5000`

## Usage

- Register as a **Community Member (Patient)** to log your own vitals.
- Register as a **Health Worker / Doctor** (or use the default `admin` account)
  to access the community-wide monitoring dashboard at `/admin`.
- Add a reading from **Dashboard → + Add New Reading**. If any vital falls
  outside the normal clinical range, the system automatically flags it as
  `warning` or `critical` and raises an alert.

### Normal ranges used for auto-classification

| Vital           | Normal Range     |
|------------------|-----------------|
| Heart Rate       | 60–100 bpm       |
| Blood Pressure   | 90–120 / 60–80 mmHg |
| Temperature      | 36.1–37.5 °C     |
| Oxygen (SpO2)    | 95–100 %         |
| Glucose          | 70–140 mg/dL     |

Values slightly outside range → `warning`. Values far outside range → `critical`.

## Security Notes (for production use)

This project is built for learning/demo purposes. Before deploying publicly:
- Change `SECRET_KEY` to a strong random value via environment variable.
- Switch `debug=True` off.
- Move from SQLite to PostgreSQL/MySQL for concurrent multi-user load.
- Add HTTPS, CSRF protection (Flask-WTF), and rate limiting.
- Add email verification for new accounts.

## Possible Extensions

- SMS/Email alert notifications (Twilio/SMTP) when a critical reading is logged.
- Role-based permissions with doctor-to-patient assignment.
- Export patient records to PDF/CSV.
- Wearable device integration via the existing `/api/records` JSON endpoint.
- Geographic/community-cluster analytics for outbreak detection.

---
Built with Flask 🐍 for the **Smart Community Health Monitoring System** project.
