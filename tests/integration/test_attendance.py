"""Tests for attendance marking functionality.

This module contains tests for teacher attendance marking feature, including:
- GET request to view attendance form
- POST request to submit attendance
"""
# pylint: disable=redefined-outer-name
# ^ Disabled because pytest fixtures are meant to be used this way
import os
import sys
import pytest
from flask import Flask
from flask_login import LoginManager

# Add src to sys.path so we can import application modules
_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_SRC_DIR = os.path.join(_REPO_ROOT, 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from attendance.views import attendance_bp
from models import Attendance, User, db


class MockUser:
    """Mock user class for testing authentication."""

    def __init__(self, user_id, name, is_faculty):
        """Initialize mock user.
        
        Args:
            user_id (int): User identifier
            name (str): User's name
            is_faculty (bool): Whether user is a teacher
        """
        self.user_id = user_id
        self.name = name
        self.is_faculty = is_faculty
        self.role = 'teacher' if is_faculty else 'student'
        self._is_authenticated = True

    @property
    def is_authenticated(self):
        """Check if user is authenticated."""
        return self._is_authenticated

    @property
    def is_active(self):
        """Check if user account is active."""
        return True

    @property
    def is_anonymous(self):
        """Check if user is anonymous."""
        return False

    def get_id(self):
        """Get user identifier."""
        return str(self.user_id)


@pytest.fixture
def test_app():
    """Create Flask application for testing."""
    template_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'src', 'templates'))
    app = Flask(__name__, template_folder=template_path)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SECRET_KEY='test-key'
    )
    db.init_app(app)
    LoginManager(app)
    app.register_blueprint(attendance_bp)
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def test_teacher(test_app):
    """Create test teacher user."""
    with test_app.app_context():
        teacher = User(user_id=1, name='Teacher', is_faculty=True)
        db.session.add(teacher)
        db.session.commit()
        return teacher


@pytest.fixture
def test_students(test_app):
    """Create test student users."""
    with test_app.app_context():
        students = []
        for i in range(2, 5):
            student = User(user_id=i, name=f'Student{i}', is_faculty=False)
            db.session.add(student)
            students.append(student)
        db.session.commit()
        return students


def test_mark_attendance_get(client, test_app, test_teacher, monkeypatch):
    """Test GET request to attendance marking page."""
    with test_app.app_context():
        db.session.add(test_teacher)
        monkeypatch.setattr('flask_login.utils._get_user', lambda: test_teacher)
        response = client.get('/attendance/mark')
        assert response.status_code == 200
        assert b'Mark Attendance' in response.data


def test_mark_attendance_post(client, test_app, test_teacher, test_students, monkeypatch):
    """Test POST request for marking attendance."""
    with test_app.app_context():
        db.session.add(test_teacher)
        for student in test_students:
            db.session.add(student)
        monkeypatch.setattr('flask_login.utils._get_user', lambda: test_teacher)
        data = {'absentees': ['2', '3']}
        response = client.post('/attendance/mark', data=data, follow_redirects=True)
        assert response.status_code == 200
        records = Attendance.query.all()
        assert len(records) == 3
        absent_ids = {r.student_id for r in records if not r.is_present}
        assert absent_ids == {2, 3}
