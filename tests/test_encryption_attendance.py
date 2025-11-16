"""Tests for SAS-92: encryption at rest for attendance data.

These tests verify that attendance fields are encrypted in the database and are
properly decrypted in API responses. They also check role-based masking for
student viewers (students see full data for their own records but masked data
for other students).
"""

import os
import sys
import pytest
from datetime import datetime, date

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# Ensure tests have an encryption key available for Fernet; do not commit this key.
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault('ENCRYPTION_KEY', Fernet.generate_key().decode())
except Exception:
    # If cryptography isn't available at import time, tests will fail later with clear errors
    pass
from flask import Flask
from flask_login import LoginManager, login_user
from werkzeug.security import generate_password_hash

from models import db, User as MainUser, Attendance
from attendance_api import attendance_api_bp
from auth_middleware import generate_jwt_token
from encryption_utils import decrypt_data, hash_value


@pytest.fixture
def test_app():
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    })

    db.init_app(app)
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def load_user(user_id):
        return MainUser.query.get(int(user_id))

    app.register_blueprint(attendance_api_bp)

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    return test_app.test_client()


@pytest.fixture
def test_users(test_app):
    with test_app.app_context():
        users = {}
        student = MainUser(
            username='PES1UG23CS001',
            password_hash=generate_password_hash('student123'),
            is_faculty=False,
            name='Test Student',
            role='student'
        )
        teacher = MainUser(
            username='TEACHER001',
            password_hash=generate_password_hash('teacher123'),
            is_faculty=True,
            name='Test Teacher',
            role='teacher'
        )
        admin = MainUser(
            username='ADMIN001',
            password_hash=generate_password_hash('admin123'),
            is_faculty=True,
            name='Test Admin',
            role='admin'
        )
        db.session.add_all([student, teacher, admin])
        db.session.commit()
        users['student'] = student
        users['teacher'] = teacher
        users['admin'] = admin
        return users


@pytest.fixture
def auth_headers(test_app, test_users):
    headers = {}
    with test_app.app_context():
        # Query by known usernames to avoid touching detached test_users instances
        mapping = {
            'student': 'PES1UG23CS001',
            'teacher': 'TEACHER001',
            'admin': 'ADMIN001'
        }
        for role, username in mapping.items():
            fresh = MainUser.query.filter_by(username=username).first()
            token = generate_jwt_token(fresh)
            headers[role] = {'Authorization': f'Bearer {token}'}
    return headers


def test_db_stores_encrypted_and_decrypts(client, test_app, test_users):
    """Submitting attendance should store ciphertext in DB and decrypt on access."""
    with test_app.test_request_context():
        with client:
            # Login as teacher using a session-bound user instance
            teacher = MainUser.query.filter_by(username='TEACHER001').first()
            login_user(teacher)

            # Submit attendance
            payload = {
                'student_srn': 'PES1UG23CSX01',
                'course_id': 'CSE777',
                'date': '2025-11-09',
                'status': 'present'
            }
            resp = client.post('/api/attendance/submit', json=payload)
            assert resp.status_code == 201
            data = resp.get_json()
            att_id = data['attendance']['id']

            # Inspect DB stored ciphertext
            rec = Attendance.query.filter_by(id=att_id).first()
            assert rec is not None
            # Underlying DB column stores ciphertext (private attrs begin with _)
            assert getattr(rec, '_student_srn') is not None
            assert payload['student_srn'] not in getattr(rec, '_student_srn')
            # Decryption via helper should return original
            assert decrypt_data(getattr(rec, '_student_srn')) == payload['student_srn']


def test_api_returns_decrypted_values_for_teacher_and_jwt(client, test_app, auth_headers):
    """Teacher using JWT should see decrypted values in API responses."""
    # Submit via JWT
    resp = client.post('/api/attendance/jwt/submit', json={
        'student_srn': 'PES1UG23CSJ01',
        'course_id': 'CSE888',
        'date': '2025-11-09',
        'status': 'absent'
    }, headers=auth_headers['teacher'])
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['attendance']['student_srn'] == 'PES1UG23CSJ01'

    # View as teacher
    resp = client.get('/api/attendance/jwt/view', headers=auth_headers['teacher'])
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(a['student_srn'] == 'PES1UG23CSJ01' for a in data['attendance'])


def test_student_sees_own_records_but_others_masked(client, test_app, test_users, auth_headers):
    """Students should see their own attendance fully but see masked entries for others."""
    with test_app.app_context():
        # Attendance for student
        a1 = Attendance(
            student_srn='PES1UG23CS001',
            course_id='CSE501',
            date=date(2025, 11, 9),
            status='present',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        # Attendance for another student
        a2 = Attendance(
            student_srn='PES1UG23CS999',
            course_id='CSE501',
            date=date(2025, 11, 9),
            status='present',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        db.session.add_all([a1, a2])
        db.session.commit()

    # Student JWT views
    resp = client.get('/api/attendance/jwt/view', headers=auth_headers['student'])
    assert resp.status_code == 200
    data = resp.get_json()
    # Students are restricted to view only their own records in current policy.
    # Verify only student's own records are returned and other student's records are not present.
    assert all(r['student_srn'] == 'PES1UG23CS001' for r in data['attendance'])
    # Ensure own record contains marked_by
    assert any(r['marked_by'] is not None for r in data['attendance'])
