"""SAS-96: Bunk Allowance Data Models.

This module defines the database models for tracking student bunk allowances
and remaining classes. It integrates with the existing Attendance system.

Models:
    CourseConfig:
        Configuration for course-level bunk allowance policies.
        Stores total classes, bunk percentage, and minimum attendance requirements.
    
    StudentBunkAllowance:
        Per-student, per-course tracking of bunk allowance and attendance.
        Automatically calculates remaining bunks and critical status.

Database Schema:
    - course_config: Course-level configuration (indexed on course_id)
    - student_bunk_allowance: Student attendance tracking (composite key: student_srn + course_id)

Relationships:
    - Integrates with existing Attendance model for real-time calculations
    - Links to User model via student_srn field
"""

from datetime import datetime
from sqlalchemy import func
from models import db


class CourseConfig(db.Model):
    """Configuration for courses including bunk allowance policies.

    Attributes:
        id (int): Primary key
        course_id (str): Unique course identifier (e.g., 'CS101', 'MATH201')
        course_name (str): Full course name
        total_classes (int): Total number of classes in the course
        bunk_allowance_percentage (float): Percentage of classes that can be bunked (0-100)
        min_attendance_percentage (float): Minimum required attendance percentage (0-100)
        created_at (datetime): Timestamp when course was created
        updated_at (datetime): Timestamp when course was last updated
    """
    __tablename__ = 'course_config'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    course_name = db.Column(db.String(200), nullable=False)
    total_classes = db.Column(db.Integer, nullable=False, default=60)
    bunk_allowance_percentage = db.Column(db.Float, nullable=False, default=25.0)
    min_attendance_percentage = db.Column(db.Float, nullable=False, default=75.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                          onupdate=datetime.utcnow)

    def __repr__(self):
        return (f"<CourseConfig {self.course_id}: {self.course_name}, "
                f"bunk_allowance={self.bunk_allowance_percentage}%>")

    def get_max_bunk_allowed(self):
        """Calculate maximum number of classes that can be bunked.
        
        Returns:
            int: Maximum number of classes that can be missed
        """
        return int((self.bunk_allowance_percentage / 100.0) * self.total_classes)

    def get_min_classes_required(self):
        """Calculate minimum number of classes required to attend.
        
        Returns:
            int: Minimum number of classes required
        """
        return int((self.min_attendance_percentage / 100.0) * self.total_classes)

    def to_dict(self):
        """Convert course config to dictionary.
        
        Returns:
            dict: Course configuration data
        """
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


class StudentBunkAllowance(db.Model):
    """Tracks individual student bunk allowance and attendance statistics.

    This model maintains a cache of student attendance data for quick lookups
    and provides bunk allowance calculations based on course configurations.

    Attributes:
        id (int): Primary key
        student_srn (str): Student SRN identifier
        course_id (str): Course identifier
        total_classes_held (int): Total classes held so far
        classes_attended (int): Number of classes attended
        classes_missed (int): Number of classes missed (bunked)
        current_attendance_percentage (float): Current attendance percentage
        remaining_bunk_allowance (int): Remaining classes that can be bunked
        is_attendance_critical (bool): Whether student is below minimum threshold
        last_updated (datetime): Last time this record was updated
    """
    __tablename__ = 'student_bunk_allowance'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    student_srn = db.Column(db.String(100), nullable=False, index=True)
    course_id = db.Column(db.String(50), nullable=False, index=True)
    total_classes_held = db.Column(db.Integer, nullable=False, default=0)
    classes_attended = db.Column(db.Integer, nullable=False, default=0)
    classes_missed = db.Column(db.Integer, nullable=False, default=0)
    current_attendance_percentage = db.Column(db.Float, nullable=False, default=100.0)
    remaining_bunk_allowance = db.Column(db.Integer, nullable=False, default=0)
    is_attendance_critical = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('student_srn', 'course_id', name='unique_student_course'),
    )

    def __repr__(self):
        return (f"<StudentBunkAllowance {self.student_srn} - {self.course_id}: "
                f"{self.current_attendance_percentage:.1f}% "
                f"(remaining bunks: {self.remaining_bunk_allowance})>")

    def calculate_attendance_percentage(self):
        """Calculate current attendance percentage.
        
        Returns:
            float: Attendance percentage (0-100)
        """
        if self.total_classes_held == 0:
            return 100.0
        return (self.classes_attended / self.total_classes_held) * 100.0

    def update_from_attendance_records(self, course_config):
        """Update statistics based on attendance records and course config.
        
        Args:
            course_config (CourseConfig): Course configuration object
        """
        # Calculate current stats
        self.current_attendance_percentage = self.calculate_attendance_percentage()

        # Calculate remaining bunk allowance
        max_bunks = course_config.get_max_bunk_allowed()
        self.remaining_bunk_allowance = max(0, max_bunks - self.classes_missed)

        # Check if attendance is critical
        self.is_attendance_critical = (
            self.current_attendance_percentage < course_config.min_attendance_percentage
        )

        self.last_updated = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary representation.
        
        Returns:
            dict: Student bunk allowance data
        """
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
