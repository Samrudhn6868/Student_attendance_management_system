import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from src.attendance.views import attendance_bp
from src.models import Attendance, User, db
from datetime import date

class DummyUser:
    def __init__(self, id, name, is_faculty):
        self.id = id
        self.name = name
        self.is_faculty = is_faculty
        self.role = 'teacher' if is_faculty else 'student'
        self._is_authenticated = True

    @property
    def is_authenticated(self):
        return self._is_authenticated

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

import os

@pytest.fixture
def app():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'templates'))
    app = Flask(__name__, template_folder=template_dir)
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
def teacher(app):
    with app.app_context():
        teacher = User(id=1, name='Teacher', is_faculty=True)
        db.session.add(teacher)
        db.session.commit()
        return teacher

@pytest.fixture
def students(app):
    with app.app_context():
        students = []
        for i in range(2, 5):
            student = User(id=i, name=f'Student{i}', is_faculty=False)
            db.session.add(student)
            students.append(student)
        db.session.commit()
        return students

# Test GET attendance marking page
def test_mark_attendance_get(client, app, teacher, monkeypatch):
    with app.app_context():
        db.session.add(teacher)  # Re-attach to session
        monkeypatch.setattr('flask_login.utils._get_user', lambda: teacher)
        response = client.get('/attendance/mark')
        assert response.status_code == 200
        assert b'Mark Attendance' in response.data

# Test POST attendance marking
def test_mark_attendance_post(client, app, teacher, students, monkeypatch):
    with app.app_context():
        db.session.add(teacher)  # Re-attach to session
        for student in students:
            db.session.add(student)  # Re-attach to session
        monkeypatch.setattr('flask_login.utils._get_user', lambda: teacher)
        # Simulate marking student 2 and 3 as absent
        data = {'absentees': ['2', '3']}
        response = client.post('/attendance/mark', data=data, follow_redirects=True)
        assert response.status_code == 200
        # Check attendance records
        records = Attendance.query.all()
        assert len(records) == 3
        absent_ids = [r.student_id for r in records if not r.is_present]
        assert set(absent_ids) == {2, 3}
