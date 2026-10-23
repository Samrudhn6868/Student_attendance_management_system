"""Database models for the attendance management system.

This module defines the SQLAlchemy models for user management and attendance tracking.
"""
from datetime import date, datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Encryption utilities (SAS-92)
from encryption_utils import encrypt_data, decrypt_data, hash_value

# SAS-86: Import password security functions
from password_security import (
    hash_password,
    verify_password,
    generate_password_hash,
    check_password_hash,
    upgrade_password_hash,
    needs_rehash
)

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
        """Hash and set the user's password.
        
        Args:
            password: Plaintext password to hash and store
            
        Note:
            Empty passwords are allowed but will never validate during login
        """
        if not password:
            # Set a special marker that will never match any password
            self.password_hash = "INVALID_EMPTY_PASSWORD"
        else:
            self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the given plaintext password matches the stored hash.
        
        Args:
            password: Plaintext password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        if not password or not self.password_hash:
            return False
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
    # Store encrypted ciphertext in the DB column names to remain backward compatible
    # while exposing plaintext via Python properties. We also store deterministic
    # hashes to allow filtering/searching without revealing plaintext (privacy-preserving).
    _student_srn = db.Column('student_srn', db.String(500), nullable=True)
    student_srn_hash = db.Column(db.String(64), nullable=True, index=True)

    _course_id = db.Column('course_id', db.String(500), nullable=True)
    course_id_hash = db.Column(db.String(64), nullable=True, index=True)

    _status = db.Column('status', db.String(500), nullable=True)
    status_hash = db.Column(db.String(64), nullable=True, index=True)

    # marked_by is less sensitive but still encrypted at rest
    _marked_by = db.Column('marked_by', db.String(500), nullable=True)
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

    # ---------------------------
    # Transparent encryption helpers
    # ---------------------------
    # Hybrid-style properties expose plaintext to application code while
    # storing ciphertext in the underlying DB columns. The comparator
    # implementations below allow queries like
    # Attendance.query.filter_by(student_srn="PES1UG23CS001") to work by
    # comparing deterministic hashes in SQL instead of plaintext.
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlalchemy.ext.hybrid import Comparator

    class _HashComparator(Comparator):
        """Comparator that compares the stored hash column to the hash of rhs."""
        def __init__(self, expr):
            super().__init__(expr)

        def __eq__(self, other):
            # Compare hashed values in the DB for deterministic searching.
            return self.__clause_element__() == hash_value(other)

    @hybrid_property
    def student_srn(self):
        """Return decrypted student SRN."""
        if self._student_srn:
            try:
                return decrypt_data(self._student_srn)
            except Exception:
                return None
        return None

    @student_srn.setter
    def student_srn(self, value):
        if value is None:
            self._student_srn = None
            self.student_srn_hash = None
        else:
            self._student_srn = encrypt_data(value)
            self.student_srn_hash = hash_value(value)

    @student_srn.comparator
    def student_srn(cls):
        """Return hash comparator for encrypted student SRN."""
        return cls._HashComparator(cls.student_srn_hash)

    @hybrid_property
    def course_id(self):
        """Decrypt and return course ID."""
        if self._course_id:
            try:
                return decrypt_data(self._course_id)
            except Exception:
                return None
        return None

    @course_id.setter
    def course_id(self, value):
        """Encrypt and set course ID."""
        if value is None:
            self._course_id = None
            self.course_id_hash = None
        else:
            self._course_id = encrypt_data(value)
            self.course_id_hash = hash_value(value)

    @course_id.comparator
    def course_id(cls):
        """Return hash comparator for encrypted course ID."""
        return cls._HashComparator(cls.course_id_hash)

    @hybrid_property
    def status(self):
        if self._status:
            try:
                return decrypt_data(self._status)
            except Exception:
                return None
        return None

    @status.setter
    def status(self, value):
        if value is None:
            self._status = None
            self.status_hash = None
        else:
            self._status = encrypt_data(value)
            self.status_hash = hash_value(value)

    @status.comparator
    def status(cls):
        """Return hash comparator for encrypted attendance status."""
        return cls._HashComparator(cls.status_hash)

    @hybrid_property
    def marked_by(self):
        """Decrypt and return the name of faculty who marked attendance."""
        if self._marked_by:
            try:
                return decrypt_data(self._marked_by)
            except Exception:
                return None
        return None

    @marked_by.setter
    def marked_by(self, value):
        """Encrypt and set the name of faculty who marked attendance."""
        if value is None:
            self._marked_by = None
        else:
            self._marked_by = encrypt_data(value)


class AttendanceCorrectionRequest(db.Model):
    """Model for attendance correction requests submitted by students.
    
    Allows students to request a correction/change to their attendance status
    for a specific course on a specific date. Tracks request status and reason.
    
    Attributes:
        id (int): Primary key for the request
        student_id (int): ID of the student submitting the request
        student_name (str): Name of the student (for easy reference)
        course_id (str): Course identifier for which correction is requested
        date (date): Date of the attendance record being corrected
        current_status (str): Current status of attendance ('present' or 'absent')
        requested_status (str): Requested new status for attendance
        reason (str): Reason provided by student for the correction
        status (str): Status of the request ('pending', 'approved', 'rejected', 'cancelled', 'expired')
        submitted_at (datetime): Timestamp when request was submitted
        reviewed_at (datetime): Timestamp when request was reviewed (nullable)
        reviewed_by (int): ID of admin/faculty who reviewed (nullable)
        admin_notes (str): Notes from reviewer (nullable)
    """
    id = db.Column(db.Integer, primary_key=True)

    # Student information
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)

    # Attendance details
    course_id = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    current_status = db.Column(db.String(20), nullable=False)  # 'present' or 'absent'
    requested_status = db.Column(db.String(20), nullable=False)  # 'present' or 'absent'

    # Request information
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected, cancelled

    # Timestamps
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Reviewer information
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

    # Relationship to student
    student = db.relationship('User', foreign_keys=[student_id], backref='correction_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        """String representation of correction request."""
        return (f"<AttendanceCorrectionRequest id={self.id} "
                f"student={self.student_name} course={self.course_id} "
                f"date={self.date} status={self.status}>")
