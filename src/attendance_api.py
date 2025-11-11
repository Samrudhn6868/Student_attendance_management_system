"""SAS-93: API for Attendance Submission and Updates.

This module provides REST API endpoints for attendance management:
- POST /api/attendance/submit - Submit attendance records (teacher, admin)
- PUT /api/attendance/update - Update existing attendance (teacher, admin)
- GET /api/attendance/view - View attendance records (all users)

The API supports both Flask-Login session and JWT token authentication.
All endpoints enforce role-based access control (RBAC).
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

# SAS-83, SAS-88: Import authentication and RBAC
from auth_middleware import jwt_role_required, jwt_required, get_token_from_header, verify_jwt_token
from rbac import require_role, get_user_role
from models import db, Attendance, User

# SAS-94: Import audit trail functions
from audit_trail import (
    log_attendance_creation,
    log_attendance_update,
    log_attendance_deletion
)


# Create Blueprint for attendance API
attendance_api_bp = Blueprint('attendance_api', __name__, url_prefix='/api/attendance')


def validate_attendance_data(data, require_id=False):
    """Validate attendance submission/update data.

    Args:
        data (dict): Request data to validate
        require_id (bool): Whether attendance_id is required (for updates)

    Returns:
        tuple: (is_valid, error_message)
    """
    if require_id and not data.get('attendance_id'):
        return False, "attendance_id is required"

    if not require_id:
        # For submission, these fields are required
        required_fields = ['student_srn', 'course_id', 'date', 'status']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

    # Validate status
    status = data.get('status')
    if status and status not in ['present', 'absent']:
        return False, "status must be 'present' or 'absent'"

    # Validate date format if provided
    date_str = data.get('date')
    if date_str:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return False, "date must be in YYYY-MM-DD format"

    return True, None


def get_current_user_info():
    """Get current user info from session or JWT token.

    Returns:
        dict: User information (username, role) or None
    """
    # Try JWT token first
    token = get_token_from_header()
    if token:
        payload = verify_jwt_token(token)
        if payload:
            return {
                'username': payload.get('username'),
                'role': payload.get('role'),
                'name': payload.get('name'),
                'user_id': payload.get('user_id')
            }

    # Fall back to Flask-Login session
    if current_user.is_authenticated:
        return {
            'username': getattr(current_user, 'username', 'unknown'),
            'role': get_user_role(),
            'name': getattr(current_user, 'name', 'Unknown'),
            'user_id': getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None)
        }

    return None


def _mask_value(val: str, keep_start: int = 3, keep_end: int = 3) -> str:
    """Mask middle of a value, keeping start and end characters visible.

    Example: PES1UG23CS001 -> PES*******001
    """
    if not val:
        return val
    if len(val) <= (keep_start + keep_end):
        return '*' * len(val)
    return val[:keep_start] + ('*' * (len(val) - keep_start - keep_end)) + val[-keep_end:]


def _format_record_for_view(record, viewer_info: dict):
    """Format a single Attendance record for API response.

    Applies role-based masking for student viewers: students can view full
    details for their own records but see masked/limited data for others.
    Teachers and admins receive fully decrypted fields.
    """
    # Decrypted values are exposed via model hybrid properties
    student_plain = record.student_srn
    course_plain = record.course_id
    status_plain = record.status
    marked_by_plain = record.marked_by

    if viewer_info and viewer_info.get('role') == 'student':
        viewer_username = viewer_info.get('username')
        # If the student is viewing their own records, show full details.
        if student_plain and viewer_username and student_plain == viewer_username:
            student_val = student_plain
            course_val = course_plain
            status_val = status_plain
            marked_by_val = marked_by_plain
        else:
            # Mask sensitive fields for other students
            student_val = _mask_value(student_plain)
            course_val = _mask_value(course_plain)
            status_val = status_plain if status_plain else None
            # Do not expose who marked attendance to students for privacy
            marked_by_val = None
    else:
        # Teachers and admins see full decrypted values
        student_val = student_plain
        course_val = course_plain
        status_val = status_plain
        marked_by_val = marked_by_plain

    return {
        'id': record.id,
        'student_srn': student_val,
        'course_id': course_val,
        'date': str(record.date) if record.date else None,
        'status': status_val,
        'marked_by': marked_by_val,
        'updated_at': record.updated_at.isoformat() if record.updated_at else None
    }


# ============================================================================
# Session-based endpoints (Flask-Login)
# ============================================================================

@attendance_api_bp.route('/submit', methods=['POST'])
@login_required
@require_role('teacher', 'admin')
def submit_attendance():
    """Submit new attendance record (Session Auth).

    Only teachers and admins can submit attendance.
    Records who marked the attendance and when.

    Expected JSON payload:
    {
        "student_srn": "PES1UG23CS001",
        "course_id": "CSE101",
        "date": "2025-11-09",
        "status": "present"
    }

    Returns:
        201: Attendance created successfully
        400: Invalid input data
        403: Access denied
        500: Server error
    """
    try:
        data = request.get_json() or {}

        # Validate input
        is_valid, error_msg = validate_attendance_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'message': error_msg
            }), 400

        # Get current user
        user_info = get_current_user_info()
        if not user_info:
            return jsonify({
                'success': False,
                'error': 'Authentication error',
                'message': 'Unable to identify current user'
            }), 401

        # Check if attendance already exists for this student/course/date
        existing = Attendance.query.filter_by(
            student_srn=data['student_srn'],
            course_id=data['course_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date()
        ).first()

        if existing:
            return jsonify({
                'success': False,
                'error': 'Duplicate record',
                'message': 'Attendance already exists for this student, course, and date',
                'existing_id': existing.id
            }), 400

        # Create new attendance record
        attendance = Attendance(
            student_srn=data['student_srn'],
            course_id=data['course_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            status=data['status'],
            marked_by=user_info['username'],
            updated_at=datetime.utcnow()
        )

        db.session.add(attendance)
        db.session.commit()

        # SAS-94: Log attendance creation in audit trail
        log_attendance_creation(attendance, reason=data.get('reason'))

        return jsonify({
            'success': True,
            'message': 'Attendance submitted successfully',
            'attendance': {
                'id': attendance.id,
                'student_srn': attendance.student_srn,
                'course_id': attendance.course_id,
                'date': str(attendance.date),
                'status': attendance.status,
                'marked_by': attendance.marked_by,
                'updated_at': attendance.updated_at.isoformat()
            }
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500


@attendance_api_bp.route('/update', methods=['PUT'])
@login_required
@require_role('teacher', 'admin')
def update_attendance():
    """Update existing attendance record (Session Auth).

    Only teachers and admins can update attendance.
    Logs each change for audit trail (SAS-94).

    Expected JSON payload:
    {
        "attendance_id": 123,
        "status": "present",
        "reason": "Correction needed" (optional)
    }

    Returns:
        200: Attendance updated successfully
        400: Invalid input data
        403: Access denied
        404: Attendance record not found
        500: Server error
    """
    try:
        data = request.get_json() or {}

        # Validate input
        is_valid, error_msg = validate_attendance_data(data, require_id=True)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'message': error_msg
            }), 400

        # Get current user
        user_info = get_current_user_info()
        if not user_info:
            return jsonify({
                'success': False,
                'error': 'Authentication error',
                'message': 'Unable to identify current user'
            }), 401

        # Find attendance record
        attendance = db.session.get(Attendance, data['attendance_id'])
        if not attendance:
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': f"Attendance record {data['attendance_id']} not found"
            }), 404

        # Store old values for audit
        old_values = {
            'status': attendance.status,
            'marked_by': attendance.marked_by,
            'student_srn': attendance.student_srn,
            'course_id': attendance.course_id,
            'date': str(attendance.date)
        }

        # Update fields if provided
        if 'status' in data and data['status']:
            attendance.status = data['status']
        if 'student_srn' in data and data['student_srn']:
            attendance.student_srn = data['student_srn']
        if 'course_id' in data and data['course_id']:
            attendance.course_id = data['course_id']
        if 'date' in data and data['date']:
            attendance.date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Update marked_by to current user (to track who made the update)
        attendance.marked_by = user_info['username']
        # updated_at will auto-update via onupdate

        db.session.commit()

        # SAS-94: Log attendance update in audit trail
        log_attendance_update(attendance, old_values, reason=data.get('reason'))

        return jsonify({
            'success': True,
            'message': 'Attendance updated successfully',
            'attendance': {
                'id': attendance.id,
                'student_srn': attendance.student_srn,
                'course_id': attendance.course_id,
                'date': str(attendance.date),
                'status': attendance.status,
                'marked_by': attendance.marked_by,
                'updated_at': attendance.updated_at.isoformat()
            },
            'changes': {
                'old_status': old_values['status'],
                'new_status': attendance.status
            }
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500


@attendance_api_bp.route('/view', methods=['GET'])
@login_required
@require_role('student', 'teacher', 'admin')
def view_attendance():
    """View attendance records (Session Auth).

    Students can only view their own attendance.
    Teachers and admins can view all attendance or filter by parameters.

    Query parameters:
        student_srn: Filter by student SRN (teachers/admins)
        course_id: Filter by course
        date: Filter by specific date (YYYY-MM-DD)
        status: Filter by status ('present' or 'absent')

    Returns:
        200: Attendance records
        403: Access denied
        500: Server error
    """
    try:
        # Get current user
        user_info = get_current_user_info()
        if not user_info:
            return jsonify({
                'success': False,
                'error': 'Authentication error',
                'message': 'Unable to identify current user'
            }), 401

        # Build query
        query = Attendance.query

        # Students can only see their own records
        if user_info['role'] == 'student':
            # Get student's SRN from username or User table
            user = User.query.filter_by(user_id=user_info['user_id']).first()
            if user:
                # Assuming username is the SRN for students
                student_srn = getattr(current_user, 'username', None)
                if student_srn:
                    query = query.filter_by(student_srn=student_srn)
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Data error',
                        'message': 'Unable to determine student SRN'
                    }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Not found',
                    'message': 'User record not found'
                }), 404
        else:
            # Teachers and admins can filter
            student_srn = request.args.get('student_srn')
            if student_srn:
                query = query.filter_by(student_srn=student_srn)

        # Common filters
        course_id = request.args.get('course_id')
        if course_id:
            query = query.filter_by(course_id=course_id)

        date_str = request.args.get('date')
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter_by(date=date_obj)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format',
                    'message': 'Date must be in YYYY-MM-DD format'
                }), 400

        status = request.args.get('status')
        if status:
            if status not in ['present', 'absent']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid status',
                    'message': "Status must be 'present' or 'absent'"
                }), 400
            query = query.filter_by(status=status)

        # Execute query
        records = query.order_by(Attendance.date.desc()).all()

        # Format results with role-aware masking
        attendance_list = [_format_record_for_view(record, user_info) for record in records]

        return jsonify({
            'success': True,
            'message': f'Retrieved {len(attendance_list)} attendance record(s)',
            'role': user_info['role'],
            'count': len(attendance_list),
            'attendance': attendance_list
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500


# ============================================================================
# JWT-based endpoints (Alternative Authentication)
# ============================================================================

@attendance_api_bp.route('/jwt/submit', methods=['POST'])
@jwt_role_required('teacher', 'admin')
def jwt_submit_attendance():
    """Submit new attendance record (JWT Auth).

    Same as /submit but uses JWT token authentication.

    Headers:
        Authorization: Bearer <jwt_token>

    Expected JSON payload: Same as /submit

    Returns: Same as /submit
    """
    try:
        data = request.get_json() or {}

        # Validate input
        is_valid, error_msg = validate_attendance_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'message': error_msg
            }), 400

        # Get JWT user
        jwt_user = request.jwt_user

        # Check for duplicate
        existing = Attendance.query.filter_by(
            student_srn=data['student_srn'],
            course_id=data['course_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date()
        ).first()

        if existing:
            return jsonify({
                'success': False,
                'error': 'Duplicate record',
                'message': 'Attendance already exists for this student, course, and date',
                'existing_id': existing.id
            }), 400

        # Create attendance record
        attendance = Attendance(
            student_srn=data['student_srn'],
            course_id=data['course_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            status=data['status'],
            marked_by=jwt_user['username'],
            updated_at=datetime.utcnow()
        )

        db.session.add(attendance)
        db.session.commit()

        # SAS-94: Log attendance creation in audit trail
        log_attendance_creation(attendance, reason=data.get('reason'))

        return jsonify({
            'success': True,
            'message': 'Attendance submitted successfully via JWT',
            'auth_method': 'JWT',
            'attendance': {
                'id': attendance.id,
                'student_srn': attendance.student_srn,
                'course_id': attendance.course_id,
                'date': str(attendance.date),
                'status': attendance.status,
                'marked_by': attendance.marked_by,
                'updated_at': attendance.updated_at.isoformat()
            }
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500


@attendance_api_bp.route('/jwt/update', methods=['PUT'])
@jwt_role_required('teacher', 'admin')
def jwt_update_attendance():
    """Update existing attendance record (JWT Auth).

    Same as /update but uses JWT token authentication.

    Headers:
        Authorization: Bearer <jwt_token>

    Expected JSON payload: Same as /update

    Returns: Same as /update
    """
    try:
        data = request.get_json() or {}

        # Validate input
        is_valid, error_msg = validate_attendance_data(data, require_id=True)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation error',
                'message': error_msg
            }), 400

        # Get JWT user
        jwt_user = request.jwt_user

        # Find attendance record
        attendance = db.session.get(Attendance, data['attendance_id'])
        if not attendance:
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': f"Attendance record {data['attendance_id']} not found"
            }), 404

        # Store old values for audit
        old_values = {
            'status': attendance.status,
            'marked_by': attendance.marked_by,
            'student_srn': attendance.student_srn,
            'course_id': attendance.course_id,
            'date': str(attendance.date)
        }

        # Update fields
        if 'status' in data and data['status']:
            attendance.status = data['status']
        if 'student_srn' in data and data['student_srn']:
            attendance.student_srn = data['student_srn']
        if 'course_id' in data and data['course_id']:
            attendance.course_id = data['course_id']
        if 'date' in data and data['date']:
            attendance.date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        attendance.marked_by = jwt_user['username']

        db.session.commit()

        # SAS-94: Log attendance update in audit trail
        log_attendance_update(attendance, old_values, reason=data.get('reason'))

        return jsonify({
            'success': True,
            'message': 'Attendance updated successfully via JWT',
            'auth_method': 'JWT',
            'attendance': {
                'id': attendance.id,
                'student_srn': attendance.student_srn,
                'course_id': attendance.course_id,
                'date': str(attendance.date),
                'status': attendance.status,
                'marked_by': attendance.marked_by,
                'updated_at': attendance.updated_at.isoformat()
            },
            'changes': {
                'old_status': old_values['status'],
                'new_status': attendance.status
            }
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500


@attendance_api_bp.route('/jwt/view', methods=['GET'])
@jwt_required
def jwt_view_attendance():
    """View attendance records (JWT Auth).

    Same as /view but uses JWT token authentication.

    Headers:
        Authorization: Bearer <jwt_token>

    Query parameters: Same as /view

    Returns: Same as /view
    """
    try:
        # Get JWT user
        jwt_user = request.jwt_user
        user_role = jwt_user.get('role')

        # Build query
        query = Attendance.query

        # Students can only see their own records
        if user_role == 'student':
            # Use username from JWT as student SRN
            student_srn = jwt_user.get('username')
            if student_srn:
                query = query.filter_by(student_srn=student_srn)
        else:
            # Teachers and admins can filter
            student_srn = request.args.get('student_srn')
            if student_srn:
                query = query.filter_by(student_srn=student_srn)

        # Common filters
        course_id = request.args.get('course_id')
        if course_id:
            query = query.filter_by(course_id=course_id)

        date_str = request.args.get('date')
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter_by(date=date_obj)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format',
                    'message': 'Date must be in YYYY-MM-DD format'
                }), 400

        status = request.args.get('status')
        if status:
            if status not in ['present', 'absent']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid status',
                    'message': "Status must be 'present' or 'absent'"
                }), 400
            query = query.filter_by(status=status)

        # Execute query
        records = query.order_by(Attendance.date.desc()).all()

        # Format results with role-aware masking
        attendance_list = [_format_record_for_view(record, {'role': user_role, 'username': jwt_user.get('username')}) for record in records]

        return jsonify({
            'success': True,
            'message': f'Retrieved {len(attendance_list)} attendance record(s) via JWT',
            'auth_method': 'JWT',
            'role': user_role,
            'count': len(attendance_list),
            'attendance': attendance_list
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': str(e)
        }), 500
