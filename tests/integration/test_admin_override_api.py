"""Integration tests to increase coverage for admin_override_api (low coverage).

Tests cover:
- Successful override
- Validation errors (missing fields, invalid status, short reason, long reason)
- Record not found
- Undo override (success & not overridden conflict)
- Student records listing with date filters & overridden_only
- Override history (with admin_id filter)
- Student search (error & success)
- Override statistics
"""

import os
import sys
from datetime import datetime, timedelta

import pytest
from flask import Flask
from flask_login import LoginManager

# Ensure src on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from models import db, User, Attendance  # noqa: E402
from admin_override_api import admin_override_bp  # noqa: E402


@pytest.fixture(scope="module")
def app():
    app = Flask(__name__)
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret"
    })
    db.init_app(app)
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(admin_override_bp)

    with app.app_context():
        db.create_all()
        # Create users
        admin = User(username="admin1", name="Admin One", role="admin", is_faculty=True)
        admin.set_password("password")
        student = User(username="stud1", name="Student One", role="student")
        student.set_password("password")
        db.session.add_all([admin, student])
        db.session.commit()

        # Create attendance records for student
        # Two records: one present, one absent
        a1 = Attendance(student_id=student.id, student_srn=student.username, course_id="CS101",
                        date=datetime.utcnow().date() - timedelta(days=1), status="present", is_present=True,
                        marked_by=admin.username)
        a2 = Attendance(student_id=student.id, student_srn=student.username, course_id="CS101",
                        date=datetime.utcnow().date(), status="absent", is_present=False,
                        marked_by=admin.username)
        db.session.add_all([a1, a2])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_admin(client, app):
    with app.app_context():
        admin = User.query.filter_by(username="admin1").first()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True


def get_student_and_record(app):
    with app.app_context():
        student = User.query.filter_by(username="stud1").first()
        record = Attendance.query.filter_by(student_id=student.id, is_present=False).first()
        if record is None:
            # Create a fresh absent record to ensure tests are independent of prior mutations
            new_record = Attendance(
                student_id=student.id,
                student_srn=student.username,
                course_id="CS101",
                date=datetime.utcnow().date(),
                status="absent",
                is_present=False,
                marked_by="admin1",
            )
            db.session.add(new_record)
            db.session.commit()
            record = new_record
        # Return primitive IDs to avoid detached instance issues
        return student.id, record.id


def test_override_success(client, app):
    login_admin(client, app)
    _, rid = get_student_and_record(app)
    resp = client.post(f"/api/admin/override/attendance/{rid}", json={
        "new_status": "present",
        "reason": "System error corrected"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['record']['original_status'] == 'absent'
    assert data['record']['new_status'] == 'present'


@pytest.mark.parametrize("payload,expected_code", [
    ({}, 400),
    ({"reason": "Test"}, 400),
    ({"new_status": "present"}, 400),
])
def test_override_missing_fields(client, app, payload, expected_code):
    login_admin(client, app)
    _, rid = get_student_and_record(app)
    resp = client.post(f"/api/admin/override/attendance/{rid}", json=payload)
    assert resp.status_code == expected_code


def test_override_invalid_status(client, app):
    login_admin(client, app)
    _, rid = get_student_and_record(app)
    resp = client.post(f"/api/admin/override/attendance/{rid}", json={
        "new_status": "unknown",
        "reason": "Bad status"
    })
    assert resp.status_code == 400


def test_override_short_reason(client, app):
    login_admin(client, app)
    _, rid = get_student_and_record(app)
    resp = client.post(f"/api/admin/override/attendance/{rid}", json={
        "new_status": "present",
        "reason": "bad"
    })
    assert resp.status_code == 400


def test_override_long_reason(client, app):
    login_admin(client, app)
    _, rid = get_student_and_record(app)
    long_reason = "x" * 501
    resp = client.post(f"/api/admin/override/attendance/{rid}", json={
        "new_status": "present",
        "reason": long_reason
    })
    assert resp.status_code == 400


def test_override_not_found(client, app):
    login_admin(client, app)
    resp = client.post("/api/admin/override/attendance/99999", json={
        "new_status": "present",
        "reason": "Does not exist"
    })
    assert resp.status_code == 404


def test_undo_override_success(client, app):
    login_admin(client, app)
    _, rid = get_student_and_record(app)
    # Ensure overridden first
    pre = client.post(f"/api/admin/override/attendance/{rid}", json={
        "new_status": "present",
        "reason": "Fixed issue"
    })
    assert pre.status_code == 200
    resp = client.post(f"/api/admin/override/attendance/{rid}/undo")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['record']['is_overridden'] is False


def test_undo_override_conflict(client, app):
    login_admin(client, app)
    # Pick a non-overridden record (create fresh)
    with app.app_context():
        student = User.query.filter_by(username="stud1").first()
        new_record = Attendance(student_id=student.id, student_srn=student.username, course_id="CS102",
                                date=datetime.utcnow().date(), status="present", is_present=True,
                                marked_by="admin1")
        db.session.add(new_record)
        db.session.commit()
        rid = new_record.id
    resp = client.post(f"/api/admin/override/attendance/{rid}/undo")
    assert resp.status_code == 409


def test_get_student_records_filters(client, app):
    login_admin(client, app)
    sid, _ = get_student_and_record(app)
    # Basic fetch
    base = client.get(f"/api/admin/override/student/{sid}/records")
    assert base.status_code == 200
    # Date filter invalid
    bad = client.get(f"/api/admin/override/student/{sid}/records?from_date=2025-13-40")
    assert bad.status_code == 400
    # Overridden only filter
    overridden_only = client.get(f"/api/admin/override/student/{sid}/records?overridden_only=true")
    assert overridden_only.status_code == 200


def test_override_history(client, app):
    login_admin(client, app)
    # Override one record to populate history
    _, rid = get_student_and_record(app)
    client.post(f"/api/admin/override/attendance/{rid}", json={
        "new_status": "present",
        "reason": "History test"
    })
    hist = client.get("/api/admin/override/override-history?limit=10")
    assert hist.status_code == 200
    data = hist.get_json()
    assert 'history' in data
    # Filter by admin id
    with app.app_context():
        admin = User.query.filter_by(username="admin1").first()
    filt = client.get(f"/api/admin/override/override-history?admin_id={admin.id}")
    assert filt.status_code == 200


def test_search_students_errors_and_success(client, app):
    login_admin(client, app)
    # Too short
    short = client.get("/api/admin/override/search-students?query=a")
    assert short.status_code == 400
    # Valid search
    ok = client.get("/api/admin/override/search-students?query=Stud")
    assert ok.status_code == 200
    data = ok.get_json()
    assert data['total'] >= 1


def test_override_statistics(client, app):
    login_admin(client, app)
    stats = client.get("/api/admin/override/stats")
    assert stats.status_code == 200
    data = stats.get_json()
    assert 'stats' in data
    assert 'total_overrides' in data['stats']
