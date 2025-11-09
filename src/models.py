"""Database models for the attendance management system.

This module defines the SQLAlchemy models for user management and attendance tracking.
"""
from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and role management.
    
    This model supports both the legacy interface (user_id, name, is_faculty)
    and the enhanced interface with authentication fields (id, username, password_hash).
    
    Attributes:
        id (int): Primary key for user identification (maps to user_id)
        user_id (int): Alternative name for id (legacy compatibility)
        username (str): Username for login (SRN for students, ID for faculty)
        password_hash (str): Hashed password for authentication
        name (str): User's full name
        is_faculty (bool): Flag indicating if user is a teacher
        role (str): User's role (teacher/student/admin)
    """
    # Primary key - supports both 'id' and 'user_id' names
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication fields (SAS-83)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=True)
    
    # User information
    name = db.Column(db.String(100), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), nullable=False, default='student')

    def __init__(self, user_id=None, name=None, is_faculty=False, **kwargs):
        """Initialize a new User.
        
        Supports both legacy and enhanced initialization:
        - Legacy: User(user_id=1, name='John', is_faculty=True)
        - Enhanced: User(username='john', name='John', password_hash='...', role='teacher')

        Args:
            user_id (int): User's unique identifier (optional)
            name (str): User's full name
            is_faculty (bool): Whether the user is a teacher
            **kwargs: Additional fields (username, password_hash, role, etc.)
        """
        # Handle legacy initialization
        if user_id is not None:
            self.id = user_id
        
        # Set name
        if name:
            self.name = name
        elif 'name' in kwargs:
            self.name = kwargs['name']
        
        # Set is_faculty
        self.is_faculty = is_faculty
        
        # Set role
        if 'role' in kwargs:
            self.role = kwargs['role']
        else:
            self.role = 'teacher' if is_faculty else 'student'
        
        # Set authentication fields if provided
        if 'username' in kwargs:
            self.username = kwargs['username']
        if 'password_hash' in kwargs:
            self.password_hash = kwargs['password_hash']
    
    @property
    def user_id(self):
        """Legacy compatibility: user_id is an alias for id."""
        return self.id
    
    @user_id.setter
    def user_id(self, value):
        """Legacy compatibility: setting user_id sets id."""
        self.id = value

    def get_id(self):
        """Override UserMixin get_id to use id."""
        return str(self.id)

class Attendance(db.Model):
    """Attendance record model for SAS-93.
    
    Enhanced model with support for multiple courses, detailed tracking,
    and audit trail capabilities.
    
    Attributes:
        id (int): Primary key for attendance record
        student_id (int): ID of the student (legacy, for backward compatibility)
        student_srn (str): Student SRN identifier (SAS-93)
        course_id (str): Course identifier (SAS-93)
        date (str): Date of attendance in YYYY-MM-DD format (SAS-93)
        status (str): Attendance status - 'present' or 'absent' (SAS-93)
        marked_by (str): Username of teacher/admin who marked attendance (SAS-93)
        updated_at (datetime): Timestamp of last update, auto-updates (SAS-93)
        is_present (bool): Whether student was present (legacy, for backward compatibility)
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Legacy fields (for backward compatibility with existing code)
    student_id = db.Column(db.Integer, nullable=True)
    date = db.Column(db.Date, default=date.today, nullable=True)
    is_present = db.Column(db.Boolean, default=True)
    
    # SAS-93: New fields for enhanced attendance tracking
    student_srn = db.Column(db.String(50), nullable=True)
    course_id = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=True)  # 'present' or 'absent'
    marked_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        """String representation of Attendance record."""
        return (f"<Attendance id={self.id} student_srn={self.student_srn} "
                f"course={self.course_id} date={self.date} status={self.status}>")
