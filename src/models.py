"""Database models for the attendance management system.

This module defines the SQLAlchemy models for user management and attendance tracking.
"""
from datetime import date, datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# SAS-86: Import password security functions
from password_security import hash_password, verify_password

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

    # Account locking fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked = db.Column(db.Boolean, default=False)
    locked_at = db.Column(db.DateTime, nullable=True)

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

        # Initialize account locking fields
        self.failed_login_attempts = kwargs.get('failed_login_attempts', 0)
        self.account_locked = kwargs.get('account_locked', False)
        self.locked_at = kwargs.get('locked_at', None)

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
    
    def set_password(self, password):
        """Hash and set the user's password using bcrypt (SAS-86).
        
        Args:
            password (str): Plaintext password to hash
        """
        self.password_hash = hash_password(password)
    
    def check_password(self, password):
        """Verify if the given plaintext password matches the stored hash (SAS-86).
        
        Args:
            password (str): Plaintext password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        if password is None:
            return False
        return verify_password(password, self.password_hash)

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the given plaintext password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        """Check if account is locked.
        
        Automatically unlocks if locked for more than 30 minutes.
        """
        if not self.account_locked:
            return False
        
        # Auto-unlock after 30 minutes
        if self.locked_at:
            unlock_time = self.locked_at + timedelta(minutes=30)
            if datetime.utcnow() >= unlock_time:
                self.unlock_account()
                return False
        else:
            # If locked_at is None but account is marked as locked, unlock it
            self.unlock_account()
            return False
        
        return True

    def lock_account(self):
        """Lock the account after too many failed attempts."""
        self.account_locked = True
        self.locked_at = datetime.utcnow()
        db.session.commit()

    def unlock_account(self):
        """Unlock the account and reset failed attempts."""
        self.account_locked = False
        self.locked_at = None
        self.failed_login_attempts = 0
        db.session.commit()

    def record_failed_login(self):
        """Increment failed login attempts and lock if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 3:
            self.lock_account()
        else:
            db.session.commit()

    def reset_failed_attempts(self):
        """Reset failed login attempts counter on successful login."""
        self.failed_login_attempts = 0
        db.session.commit()

class Attendance(db.Model):
    """Attendance record model combining SAS-90 and SAS-93 features.

    Enhanced model with support for multiple courses, detailed tracking,
    override capabilities, and audit trail.

    Attributes:
        id (int): Primary key for attendance record
        student_id (int): ID of the student (legacy, for backward compatibility)
        date (date): Date of attendance
        is_present (bool): Whether student was present (legacy)
        student_srn (str): Student SRN identifier (SAS-93)
        course_id (str): Course identifier (SAS-93)
        status (str): Attendance status - 'present' or 'absent' (SAS-93)
        marked_by (str): Username of teacher/admin who marked attendance (SAS-93)
        updated_at (datetime): Timestamp of last update, auto-updates (SAS-93)
        is_overridden (bool): Whether attendance was overridden by admin (SAS-90)
        override_reason (str): Reason for override (SAS-90)
        overridden_by (int): ID of admin who overrode attendance (SAS-90)
        override_timestamp (str): ISO timestamp of when override occurred (SAS-90)
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

    # SAS-90: Override fields for admin attendance correction
    is_overridden = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.String(500), nullable=True)
    overridden_by = db.Column(db.Integer, nullable=True)
    override_timestamp = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        """String representation of Attendance record."""
        return (f"<Attendance id={self.id} student_srn={self.student_srn} "
                f"course={self.course_id} date={self.date} status={self.status}>")
