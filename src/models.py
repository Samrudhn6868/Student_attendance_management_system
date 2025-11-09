"""Database models for the attendance management system.

This module defines the SQLAlchemy models for user management and attendance tracking.
"""
from datetime import date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and role management.
    
    Attributes:
        id (int): Primary key for user identification
        name (str): User's full name
        is_faculty (bool): Flag indicating if user is a teacher
        role (str): User's role (teacher/student)
    """
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), nullable=False)

    def __init__(self, user_id, name, is_faculty):
        """Initialize a new User.

        Args:
            user_id (int): User's unique identifier
            name (str): User's full name
            is_faculty (bool): Whether the user is a teacher
        """
        self.user_id = user_id
        self.name = name
        self.is_faculty = is_faculty
        self.role = 'teacher' if is_faculty else 'student'

    def get_id(self):
        """Override UserMixin get_id to use user_id instead of id."""
        return str(self.user_id)

class Attendance(db.Model):
    """Attendance record model.
    
    Attributes:
        id (int): Primary key for attendance record
        student_id (int): ID of the student
        date (date): Date of attendance
        is_present (bool): Whether student was present
        is_overridden (bool): Whether attendance was overridden by admin
        override_reason (str): Reason for override (if any)
        overridden_by (int): ID of admin who overrode attendance
        override_timestamp (str): ISO timestamp of when override occurred
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    is_present = db.Column(db.Boolean, default=True)
    is_overridden = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.String(500), nullable=True)
    overridden_by = db.Column(db.Integer, nullable=True)
    override_timestamp = db.Column(db.String(50), nullable=True)
