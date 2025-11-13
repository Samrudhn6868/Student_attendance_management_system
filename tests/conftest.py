"""Pytest configuration and fixtures for bunk allowance tests."""

import os
import sys
import pytest
from datetime import datetime

# Ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


@pytest.fixture(scope='function')
def app():
    """Create and configure a test Flask application."""
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    
    # Create fresh Flask app for testing
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['WTF_CSRF_ENABLED'] = False
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize fresh db instance
    test_db = SQLAlchemy(test_app)
    
    # Import models after db is created
    with test_app.app_context():
        # Import base models
        from models import User, Attendance
        
        # Define bunk allowance models inline to avoid re-import issues
        class CourseConfig(test_db.Model):
            __tablename__ = 'course_config'
            id = test_db.Column(test_db.Integer, primary_key=True)
            course_id = test_db.Column(test_db.String(50), unique=True, nullable=False, index=True)
            course_name = test_db.Column(test_db.String(200), nullable=False)
            total_classes = test_db.Column(test_db.Integer, nullable=False, default=60)
            bunk_allowance_percentage = test_db.Column(test_db.Float, nullable=False, default=25.0)
            min_attendance_percentage = test_db.Column(test_db.Float, nullable=False, default=75.0)
            created_at = test_db.Column(test_db.DateTime, nullable=False, default=datetime.utcnow)
            updated_at = test_db.Column(test_db.DateTime, nullable=False, default=datetime.utcnow)
            
            def get_max_bunk_allowed(self):
                return int((self.bunk_allowance_percentage / 100.0) * self.total_classes)
            
            def get_min_classes_required(self):
                return int((self.min_attendance_percentage / 100.0) * self.total_classes)
            
            def to_dict(self):
                return {
                    'id': self.id,
                    'course_id': self.course_id,
                    'course_name': self.course_name,
                    'total_classes': self.total_classes,
                    'bunk_allowance_percentage': self.bunk_allowance_percentage,
                    'min_attendance_percentage': self.min_attendance_percentage,
                    'max_bunk_allowed': self.get_max_bunk_allowed(),
                    'min_classes_required': self.get_min_classes_required(),
                    'created_at': self.created_at.isoformat() if self.created_at else None,
                    'updated_at': self.updated_at.isoformat() if self.updated_at else None
                }
        
        class StudentBunkAllowance(test_db.Model):
            __tablename__ = 'student_bunk_allowance'
            id = test_db.Column(test_db.Integer, primary_key=True)
            student_srn = test_db.Column(test_db.String(100), nullable=False, index=True)
            course_id = test_db.Column(test_db.String(50), nullable=False, index=True)
            total_classes_held = test_db.Column(test_db.Integer, nullable=False, default=0)
            classes_attended = test_db.Column(test_db.Integer, nullable=False, default=0)
            classes_missed = test_db.Column(test_db.Integer, nullable=False, default=0)
            current_attendance_percentage = test_db.Column(test_db.Float, nullable=False, default=100.0)
            remaining_bunk_allowance = test_db.Column(test_db.Integer, nullable=False, default=0)
            is_attendance_critical = test_db.Column(test_db.Boolean, default=False)
            last_updated = test_db.Column(test_db.DateTime, nullable=False, default=datetime.utcnow)
            __table_args__ = (test_db.UniqueConstraint('student_srn', 'course_id', name='unique_student_course'),)
            
            def calculate_attendance_percentage(self):
                if self.total_classes_held == 0:
                    return 100.0
                return (self.classes_attended / self.total_classes_held) * 100.0
            
            def update_from_attendance_records(self, course_config):
                self.current_attendance_percentage = self.calculate_attendance_percentage()
                max_bunks = course_config.get_max_bunk_allowed()
                self.remaining_bunk_allowance = max(0, max_bunks - self.classes_missed)
                self.is_attendance_critical = (
                    self.current_attendance_percentage < course_config.min_attendance_percentage
                )
                self.last_updated = datetime.utcnow()
            
            def to_dict(self):
                return {
                    'id': self.id,
                    'student_srn': self.student_srn,
                    'course_id': self.course_id,
                    'total_classes_held': self.total_classes_held,
                    'classes_attended': self.classes_attended,
                    'classes_missed': self.classes_missed,
                    'current_attendance_percentage': round(self.current_attendance_percentage, 2),
                    'remaining_bunk_allowance': self.remaining_bunk_allowance,
                    'is_attendance_critical': self.is_attendance_critical,
                    'last_updated': self.last_updated.isoformat() if self.last_updated else None
                }
        
        # Make models available
        test_app.CourseConfig = CourseConfig
        test_app.StudentBunkAllowance = StudentBunkAllowance
        test_app.db = test_db
        
        # Create all tables
        test_db.create_all()
        
        yield test_app
        
        # Cleanup
        test_db.session.remove()
        test_db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the Flask application."""
    return app.test_cli_runner()
