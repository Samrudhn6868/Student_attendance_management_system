"""Attendance Routes with Role-Based Access Control (SAS-88).

This module provides attendance management endpoints with RBAC:
- /attendance/view - View attendance (all roles)
- /attendance/mark - Mark attendance (teacher, admin)
- /attendance/override - Override attendance (admin only)

These routes support both Flask-Login session auth and JWT token auth.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from auth_middleware import jwt_role_required, jwt_required
from rbac import require_role, get_user_role


# Create Blueprint for attendance routes
attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/view', methods=['GET'])
@login_required
@require_role('student', 'teacher', 'admin')
def view_attendance():
    """View attendance records.
    
    Accessible by: student, teacher, admin
    
    Students can view their own attendance.
    Teachers and admins can view all attendance.
    
    Returns:
        JSON response with attendance data
    """
    user_role = get_user_role()
    
    # In a real application, you would query attendance records from the database
    # For this demo, we'll return mock data
    
    if user_role == 'student':
        # Students see only their own attendance
        attendance_data = {
            'user_id': current_user.id,
            'username': current_user.username,
            'name': current_user.name,
            'attendance': [
                {'date': '2025-11-01', 'status': 'present', 'subject': 'Mathematics'},
                {'date': '2025-11-02', 'status': 'present', 'subject': 'Physics'},
                {'date': '2025-11-03', 'status': 'absent', 'subject': 'Chemistry'},
                {'date': '2025-11-04', 'status': 'present', 'subject': 'English'},
            ],
            'summary': {
                'total_classes': 4,
                'present': 3,
                'absent': 1,
                'percentage': 75.0
            }
        }
    else:
        # Teachers and admins see all attendance
        attendance_data = {
            'all_students': [
                {
                    'user_id': 1,
                    'username': 'PES1UG23CS001',
                    'name': 'Student One',
                    'percentage': 85.0
                },
                {
                    'user_id': 2,
                    'username': 'PES1UG23CS002',
                    'name': 'Student Two',
                    'percentage': 90.0
                },
                {
                    'user_id': 3,
                    'username': 'PES1UG23CS003',
                    'name': 'Student Three',
                    'percentage': 78.0
                }
            ],
            'summary': {
                'total_students': 3,
                'average_attendance': 84.3
            }
        }
    
    return jsonify({
        'success': True,
        'message': 'Attendance records retrieved successfully',
        'role': user_role,
        'data': attendance_data
    }), 200


@attendance_bp.route('/mark', methods=['POST'])
@login_required
@require_role('teacher', 'admin')
def mark_attendance():
    """Mark attendance for students.
    
    Accessible by: teacher, admin
    
    Expected JSON payload:
    {
        "student_id": 123,
        "subject": "Mathematics",
        "date": "2025-11-08",
        "status": "present" | "absent"
    }
    
    Returns:
        JSON response confirming attendance was marked
    """
    user_role = get_user_role()
    
    # Get request data
    data = request.get_json() or {}
    
    student_id = data.get('student_id')
    subject = data.get('subject')
    date = data.get('date')
    status = data.get('status')
    
    # Validate required fields
    if not all([student_id, subject, date, status]):
        return jsonify({
            'success': False,
            'error': 'Missing required fields',
            'required': ['student_id', 'subject', 'date', 'status']
        }), 400
    
    if status not in ['present', 'absent']:
        return jsonify({
            'success': False,
            'error': 'Invalid status',
            'message': 'Status must be either "present" or "absent"'
        }), 400
    
    # In a real application, you would:
    # 1. Verify the student exists
    # 2. Check if teacher is authorized to mark attendance for this subject
    # 3. Save the attendance record to database
    
    # For this demo, we'll just return a success response
    return jsonify({
        'success': True,
        'message': 'Attendance marked successfully',
        'marked_by': {
            'user_id': current_user.id,
            'username': current_user.username,
            'name': current_user.name,
            'role': user_role
        },
        'attendance': {
            'student_id': student_id,
            'subject': subject,
            'date': date,
            'status': status,
            'timestamp': '2025-11-08T10:30:00Z'
        }
    }), 201


@attendance_bp.route('/override', methods=['PUT'])
@login_required
@require_role('admin')
def override_attendance():
    """Override or modify existing attendance records.
    
    Accessible by: admin only
    
    This is a privileged operation that allows admins to correct
    attendance records that were marked incorrectly.
    
    Expected JSON payload:
    {
        "attendance_id": 456,
        "new_status": "present" | "absent",
        "reason": "Correction reason"
    }
    
    Returns:
        JSON response confirming the override
    """
    user_role = get_user_role()
    
    # Get request data
    data = request.get_json() or {}
    
    attendance_id = data.get('attendance_id')
    new_status = data.get('new_status')
    reason = data.get('reason')
    
    # Validate required fields
    if not all([attendance_id, new_status, reason]):
        return jsonify({
            'success': False,
            'error': 'Missing required fields',
            'required': ['attendance_id', 'new_status', 'reason']
        }), 400
    
    if new_status not in ['present', 'absent']:
        return jsonify({
            'success': False,
            'error': 'Invalid status',
            'message': 'Status must be either "present" or "absent"'
        }), 400
    
    # In a real application, you would:
    # 1. Fetch the existing attendance record
    # 2. Store the old value for audit trail
    # 3. Update the record with new status
    # 4. Log the override action with admin details and reason
    
    # For this demo, we'll return a success response
    return jsonify({
        'success': True,
        'message': 'Attendance record overridden successfully',
        'overridden_by': {
            'user_id': current_user.id,
            'username': current_user.username,
            'name': current_user.name,
            'role': user_role
        },
        'override': {
            'attendance_id': attendance_id,
            'previous_status': 'absent',  # Mock data
            'new_status': new_status,
            'reason': reason,
            'timestamp': '2025-11-08T10:35:00Z'
        }
    }), 200


# ============================================================================
# JWT-Based API Endpoints (Alternative Authentication)
# ============================================================================

@attendance_bp.route('/api/view', methods=['GET'])
@jwt_required
def api_view_attendance():
    """View attendance records via JWT authentication.
    
    This endpoint uses JWT tokens instead of session cookies.
    Accessible by all authenticated users via JWT.
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        JSON response with attendance data
    """
    jwt_user = request.jwt_user
    user_role = jwt_user.get('role')
    
    if user_role == 'student':
        attendance_data = {
            'user_id': jwt_user['user_id'],
            'username': jwt_user['username'],
            'name': jwt_user['name'],
            'attendance': [
                {'date': '2025-11-01', 'status': 'present', 'subject': 'Mathematics'},
                {'date': '2025-11-02', 'status': 'present', 'subject': 'Physics'},
                {'date': '2025-11-03', 'status': 'absent', 'subject': 'Chemistry'},
            ]
        }
    else:
        attendance_data = {
            'all_students': [
                {'username': 'PES1UG23CS001', 'name': 'Student One', 'percentage': 85.0},
                {'username': 'PES1UG23CS002', 'name': 'Student Two', 'percentage': 90.0},
            ]
        }
    
    return jsonify({
        'success': True,
        'message': 'Attendance retrieved via JWT',
        'auth_method': 'JWT',
        'role': user_role,
        'data': attendance_data
    }), 200


@attendance_bp.route('/api/mark', methods=['POST'])
@jwt_role_required('teacher', 'admin')
def api_mark_attendance():
    """Mark attendance via JWT authentication.
    
    Accessible by: teacher, admin (via JWT)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Body: Same as /attendance/mark
    
    Returns:
        JSON response confirming attendance was marked
    """
    jwt_user = request.jwt_user
    data = request.get_json() or {}
    
    student_id = data.get('student_id')
    subject = data.get('subject')
    date = data.get('date')
    status = data.get('status')
    
    if not all([student_id, subject, date, status]):
        return jsonify({
            'success': False,
            'error': 'Missing required fields'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'Attendance marked via JWT',
        'auth_method': 'JWT',
        'marked_by': jwt_user,
        'attendance': {
            'student_id': student_id,
            'subject': subject,
            'date': date,
            'status': status
        }
    }), 201


@attendance_bp.route('/api/override', methods=['PUT'])
@jwt_role_required('admin')
def api_override_attendance():
    """Override attendance via JWT authentication.
    
    Accessible by: admin only (via JWT)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Body: Same as /attendance/override
    
    Returns:
        JSON response confirming the override
    """
    jwt_user = request.jwt_user
    data = request.get_json() or {}
    
    attendance_id = data.get('attendance_id')
    new_status = data.get('new_status')
    reason = data.get('reason')
    
    if not all([attendance_id, new_status, reason]):
        return jsonify({
            'success': False,
            'error': 'Missing required fields'
        }), 400
    
    return jsonify({
        'success': True,
        'message': 'Attendance overridden via JWT',
        'auth_method': 'JWT',
        'overridden_by': jwt_user,
        'override': {
            'attendance_id': attendance_id,
            'new_status': new_status,
            'reason': reason
        }
    }), 200
