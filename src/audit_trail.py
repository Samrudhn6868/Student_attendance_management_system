"""Audit Trail System with Encrypted Sensitive Data (SAS-94 + Encryption).

Provides comprehensive audit logging for all attendance-related changes
with encryption for sensitive fields to ensure compliance and privacy.

Features:
- Automatic logging of all attendance modifications
- Encryption of sensitive fields (IP addresses, changes, reasons)
- Read-only audit entries accessible only to admins
- Audit report generation by date range or user
- Tracks create, update, and delete operations
- Log sanitization for sensitive data

Security:
- IP addresses encrypted at rest
- Changes and values encrypted at rest
- User agents sanitized before storage
- Personal identifiers protected
"""

from datetime import datetime
from functools import wraps
from flask import request
from flask_login import current_user
from models import db
import json

# Import encryption utilities for sensitive data
from encryption_utils import (
    encrypt_data,
    decrypt_data,
    encrypt_json,
    decrypt_json,
    sanitize_log_message,
    sanitize_dict
)


class AuditLog(db.Model):
    """Audit log model with encrypted sensitive fields.
    
    Attributes:
        id (int): Primary key
        user_id (int): ID of user who performed the action
        username (str): Username of user who performed the action
        user_role (str): Role of user (student/teacher/admin)
        action_type (str): Type of action (CREATE/UPDATE/DELETE)
        record_type (str): Type of record affected (attendance)
        record_id (int): ID of the affected attendance record
        timestamp (datetime): When the action occurred
        _ip_address (str): ENCRYPTED IP address of the user
        _changes (str): ENCRYPTED JSON string of changes made
        _old_values (str): ENCRYPTED JSON string of old values (for UPDATE/DELETE)
        _new_values (str): ENCRYPTED JSON string of new values (for CREATE/UPDATE)
        student_srn (str): SRN of student whose attendance was modified
        course_id (str): Course ID for the attendance record
        attendance_date (str): Date of the attendance record
        _reason (str): ENCRYPTED optional reason for the change
    
    Note: Fields prefixed with _ are encrypted at rest. Use properties to access.
    """
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)

    # User information (not encrypted - needed for queries)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    username = db.Column(db.String(80), nullable=True)
    user_role = db.Column(db.String(20), nullable=True)

    # Action details
    action_type = db.Column(db.String(20), nullable=False, index=True)
    record_type = db.Column(db.String(50), nullable=False, default='attendance')
    record_id = db.Column(db.Integer, nullable=True, index=True)

    # Timestamp and tracking
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # ENCRYPTED FIELDS (sensitive data at rest)
    _ip_address = db.Column('ip_address', db.String(500), nullable=True)  # Encrypted
    _changes = db.Column('changes', db.Text, nullable=True)  # Encrypted JSON
    _old_values = db.Column('old_values', db.Text, nullable=True)  # Encrypted JSON
    _new_values = db.Column('new_values', db.Text, nullable=True)  # Encrypted JSON
    _reason = db.Column('reason', db.String(1000), nullable=True)  # Encrypted

    # Attendance-specific fields for quick filtering (not encrypted)
    student_srn = db.Column(db.String(50), nullable=True, index=True)
    course_id = db.Column(db.String(50), nullable=True, index=True)
    attendance_date = db.Column(db.String(20), nullable=True, index=True)

    # Properties for transparent encryption/decryption
    @property
    def ip_address(self):
        """Decrypt IP address."""
        if self._ip_address:
            try:
                return decrypt_data(self._ip_address)
            except Exception:
                return '[DECRYPTION_ERROR]'
        return None

    @ip_address.setter
    def ip_address(self, value):
        """Encrypt IP address."""
        if value:
            self._ip_address = encrypt_data(value)
        else:
            self._ip_address = None

    @property
    def changes(self):
        """Decrypt changes."""
        if self._changes:
            try:
                decrypted = decrypt_data(self._changes)
                return decrypted if decrypted else None
            except Exception:
                return None
        return None

    @changes.setter
    def changes(self, value):
        """Encrypt changes (JSON string)."""
        if value:
            # Sanitize before encryption
            if isinstance(value, str):
                value = sanitize_log_message(value)
            self._changes = encrypt_data(value)
        else:
            self._changes = None

    @property
    def old_values(self):
        """Decrypt old values."""
        if self._old_values:
            try:
                return decrypt_data(self._old_values)
            except Exception:
                return None
        return None

    @old_values.setter
    def old_values(self, value):
        """Encrypt old values (JSON string)."""
        if value:
            if isinstance(value, str):
                value = sanitize_log_message(value)
            self._old_values = encrypt_data(value)
        else:
            self._old_values = None

    @property
    def new_values(self):
        """Decrypt new values."""
        if self._new_values:
            try:
                return decrypt_data(self._new_values)
            except Exception:
                return None
        return None

    @new_values.setter
    def new_values(self, value):
        """Encrypt new values (JSON string)."""
        if value:
            if isinstance(value, str):
                value = sanitize_log_message(value)
            self._new_values = encrypt_data(value)
        else:
            self._new_values = None

    @property
    def reason(self):
        """Decrypt reason."""
        if self._reason:
            try:
                return decrypt_data(self._reason)
            except Exception:
                return '[DECRYPTION_ERROR]'
        return None

    @reason.setter
    def reason(self, value):
        """Encrypt reason."""
        if value:
            # Sanitize before encryption
            value = sanitize_log_message(str(value))
            self._reason = encrypt_data(value)
        else:
            self._reason = None

    def __repr__(self):
        return (f"<AuditLog {self.id}: {self.action_type} by {self.username} "
                f"at {self.timestamp}>")

    def to_dict(self):
        """Convert audit log to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'user_role': self.user_role,
            'action_type': self.action_type,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address,
            'changes': json.loads(self.changes) if self.changes else None,
            'old_values': json.loads(self.old_values) if self.old_values else None,
            'new_values': json.loads(self.new_values) if self.new_values else None,
            'student_srn': self.student_srn,
            'course_id': self.course_id,
            'attendance_date': self.attendance_date,
            'reason': self.reason
        }


def create_audit_entry(action_type, record_type='attendance', record_id=None,
                      old_values=None, new_values=None, reason=None, **kwargs):
    """Create an audit log entry.
    
    Args:
        action_type (str): Type of action (CREATE/UPDATE/DELETE)
        record_type (str): Type of record (default: 'attendance')
        record_id (int): ID of affected record
        old_values (dict): Old values before change
        new_values (dict): New values after change
        reason (str): Optional reason for the change
        **kwargs: Additional fields (student_srn, course_id, attendance_date)
    
    Returns:
        AuditLog: Created audit log entry
    """
    # Get current user information
    user_id = current_user.id if current_user.is_authenticated else None
    username = current_user.username if current_user.is_authenticated else 'system'
    user_role = getattr(current_user, 'role', 'unknown') if current_user.is_authenticated else 'system'

    # Get IP address
    ip_address = request.remote_addr if request else None

    # Calculate changes
    changes = None
    if old_values and new_values:
        changes = {}
        for key in set(list(old_values.keys()) + list(new_values.keys())):
            old_val = old_values.get(key)
            new_val = new_values.get(key)
            if old_val != new_val:
                changes[key] = {'old': old_val, 'new': new_val}

    # Create audit entry
    audit_entry = AuditLog(
        user_id=user_id,
        username=username,
        user_role=user_role,
        action_type=action_type,
        record_type=record_type,
        record_id=record_id,
        ip_address=ip_address,
        changes=json.dumps(changes) if changes else None,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        student_srn=kwargs.get('student_srn'),
        course_id=kwargs.get('course_id'),
        attendance_date=kwargs.get('attendance_date'),
        reason=reason
    )

    db.session.add(audit_entry)
    db.session.commit()

    return audit_entry


def audit_attendance_action(action_type):
    """Decorator to automatically audit attendance actions.
    
    Args:
        action_type (str): Type of action (CREATE/UPDATE/DELETE)
    
    Usage:
        @audit_attendance_action('CREATE')
        def create_attendance(data):
            # Create attendance logic
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)

            # Extract audit information from result
            if isinstance(result, dict) and 'audit_info' in result:
                audit_info = result['audit_info']
                create_audit_entry(
                    action_type=action_type,
                    **audit_info
                )

            return result
        return wrapper
    return decorator


# TODO-PERFORMANCE: Add database indexes on commonly queried columns:
# CREATE INDEX idx_audit_action ON audit_log(action_type);
# CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
# CREATE INDEX idx_audit_user ON audit_log(user_id);
# CREATE INDEX idx_audit_student ON audit_log(student_srn);
# This will significantly improve query performance for filtered searches
def get_audit_logs(filters=None, start_date=None, end_date=None,
                   user_id=None, student_srn=None, course_id=None,
                   action_type=None, limit=100, offset=0):
    """Retrieve audit logs with optional filters.
    
    Args:
        filters (dict): Additional filter criteria
        start_date (datetime): Start date for date range filter
        end_date (datetime): End date for date range filter
        user_id (int): Filter by user ID
        student_srn (str): Filter by student SRN
        course_id (str): Filter by course ID
        action_type (str): Filter by action type
        limit (int): Maximum number of records to return
        offset (int): Number of records to skip
    
    Returns:
        tuple: (list of AuditLog entries, total count)
    """
    query = AuditLog.query

    # Apply filters
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)

    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if student_srn:
        query = query.filter(AuditLog.student_srn == student_srn)

    if course_id:
        query = query.filter(AuditLog.course_id == course_id)

    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    if filters:
        for key, value in filters.items():
            if hasattr(AuditLog, key):
                query = query.filter(getattr(AuditLog, key) == value)

    # Get total count
    total_count = query.count()

    # Apply pagination and ordering
    logs = query.order_by(AuditLog.timestamp.desc())\
               .limit(limit)\
               .offset(offset)\
               .all()

    return logs, total_count


def generate_audit_report(start_date=None, end_date=None, user_id=None,
                         student_srn=None, course_id=None, format='json'):
    """Generate an audit report.
    
    Args:
        start_date (datetime): Start date for report
        end_date (datetime): End date for report
        user_id (int): Filter by user ID
        student_srn (str): Filter by student SRN
        course_id (str): Filter by course ID
        format (str): Output format ('json', 'csv', 'summary')
    
    Returns:
        dict or str: Report data in requested format
    """
    logs, total_count = get_audit_logs(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        student_srn=student_srn,
        course_id=course_id,
        limit=10000  # High limit for reports
    )

    if format == 'json':
        return {
            'total_records': total_count,
            'filters': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'user_id': user_id,
                'student_srn': student_srn,
                'course_id': course_id
            },
            'logs': [log.to_dict() for log in logs]
        }

    elif format == 'summary':
        # Generate summary statistics
        action_counts = {}
        user_counts = {}

        for log in logs:
            action_counts[log.action_type] = action_counts.get(log.action_type, 0) + 1
            user_counts[log.username] = user_counts.get(log.username, 0) + 1

        return {
            'total_records': total_count,
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'action_breakdown': action_counts,
            'user_activity': user_counts,
            'filters_applied': {
                'user_id': user_id,
                'student_srn': student_srn,
                'course_id': course_id
            }
        }

    elif format == 'csv':
        # Generate CSV format
        import io
        output = io.StringIO()

        # Header
        headers = ['ID', 'Timestamp', 'Username', 'Role', 'Action', 'Student SRN',
                  'Course ID', 'Date', 'Reason', 'IP Address']
        output.write(','.join(headers) + '\n')

        # Data rows
        for log in logs:
            row = [
                str(log.id),
                log.timestamp.isoformat() if log.timestamp else '',
                log.username or '',
                log.user_role or '',
                log.action_type or '',
                log.student_srn or '',
                log.course_id or '',
                log.attendance_date or '',
                log.reason or '',
                log.ip_address or ''
            ]
            output.write(','.join(row) + '\n')

        return output.getvalue()

    else:
        raise ValueError(f"Unsupported format: {format}")


def log_attendance_creation(attendance_record, reason=None):
    """Log the creation of an attendance record.
    
    Args:
        attendance_record: Attendance model instance
        reason (str): Optional reason for creation
    """
    new_values = {
        'student_srn': attendance_record.student_srn,
        'course_id': attendance_record.course_id,
        'date': str(attendance_record.date),
        'status': attendance_record.status,
        'marked_by': attendance_record.marked_by
    }

    create_audit_entry(
        action_type='CREATE',
        record_type='attendance',
        record_id=attendance_record.id,
        new_values=new_values,
        student_srn=attendance_record.student_srn,
        course_id=attendance_record.course_id,
        attendance_date=str(attendance_record.date),
        reason=reason
    )


def log_attendance_update(attendance_record, old_values, reason=None):
    """Log the update of an attendance record.
    
    Args:
        attendance_record: Updated Attendance model instance
        old_values (dict): Dictionary of old values
        reason (str): Optional reason for update
    """
    new_values = {
        'student_srn': attendance_record.student_srn,
        'course_id': attendance_record.course_id,
        'date': str(attendance_record.date),
        'status': attendance_record.status,
        'marked_by': attendance_record.marked_by,
        'is_overridden': attendance_record.is_overridden,
        'override_reason': attendance_record.override_reason
    }

    create_audit_entry(
        action_type='UPDATE',
        record_type='attendance',
        record_id=attendance_record.id,
        old_values=old_values,
        new_values=new_values,
        student_srn=attendance_record.student_srn,
        course_id=attendance_record.course_id,
        attendance_date=str(attendance_record.date),
        reason=reason
    )


def log_attendance_deletion(attendance_record, reason=None):
    """Log the deletion of an attendance record.
    
    Args:
        attendance_record: Attendance model instance being deleted
        reason (str): Optional reason for deletion
    """
    old_values = {
        'student_srn': attendance_record.student_srn,
        'course_id': attendance_record.course_id,
        'date': str(attendance_record.date),
        'status': attendance_record.status,
        'marked_by': attendance_record.marked_by
    }

    create_audit_entry(
        action_type='DELETE',
        record_type='attendance',
        record_id=attendance_record.id,
        old_values=old_values,
        student_srn=attendance_record.student_srn,
        course_id=attendance_record.course_id,
        attendance_date=str(attendance_record.date),
        reason=reason
    )
