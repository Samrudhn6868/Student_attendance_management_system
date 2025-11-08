import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from src.attendance.views import attendance_bp
from src.models import Attendance, db
from datetime import date

class DummyUser(UserMixin):
    def __init__(self, id, name, is_faculty):
        self.id = id
        self.name = name
        self.is_faculty = is_faculty
        self.role = 'teacher' if is_faculty else 'student'
        self.is_authenticated = True

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test'
    db.init_app(app)
    login_manager = LoginManager(app)
    app.register_blueprint(attendance_bp)
    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def teacher():
    return DummyUser(1, 'Teacher', True)

@pytest.fixture
def students():
    return [DummyUser(i, f'Student{i}', False) for i in range(2, 5)]

# Test GET attendance marking page
def test_mark_attendance_get(client, teacher, monkeypatch):
    monkeypatch.setattr('flask_login.utils._get_user', lambda: teacher)
    response = client.get('/attendance/mark')
    assert response.status_code == 200
    assert b'Mark Attendance' in response.data

# Test POST attendance marking
def test_mark_attendance_post(client, teacher, students, monkeypatch):
    monkeypatch.setattr('flask_login.utils._get_user', lambda: teacher)
    # Simulate marking student 2 and 3 as absent
    data = {'absentees': ['2', '3']}
    response = client.post('/attendance/mark', data=data, follow_redirects=True)
    assert response.status_code == 200
    # Check attendance records
    with client.application.app_context():
        records = Attendance.query.all()
        assert len(records) == 3
        absent_ids = [r.student_id for r in records if not r.is_present]
        assert set(absent_ids) == {2, 3}
