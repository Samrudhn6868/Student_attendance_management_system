"""Attendance Routes with Role-Based Access Control (SAS-88).

This module provides attendance management endpoints with RBAC:
- /attendance/view - View attendance (all roles)
- /attendance/mark - Mark attendance (teacher, admin)
- /attendance/override - Override attendance (admin only)

These routes support both Flask-Login session auth and JWT token auth.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

# Import RBAC and auth components
from auth_middleware import jwt_role_required, jwt_required
from rbac import require_role, get_user_role
from models import db, Attendance


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
        HTML page with attendance data or JSON for API requests
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
                {'date': '2025-11-05', 'status': 'present', 'subject': 'Mathematics'},
                {'date': '2025-11-06', 'status': 'present', 'subject': 'Physics'},
                {'date': '2025-11-07', 'status': 'present', 'subject': 'Chemistry'},
                {'date': '2025-11-08', 'status': 'present', 'subject': 'English'},
            ],
            'summary': {
                'total_classes': 8,
                'present': 7,
                'absent': 1,
                'percentage': 87.5
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
                },
                {
                    'user_id': 4,
                    'username': 'PES1UG23CS004',
                    'name': 'Student Four',
                    'percentage': 55.0
                },
                {
                    'user_id': 5,
                    'username': 'PES1UG23CS005',
                    'name': 'Student Five',
                    'percentage': 92.0
                }
            ],
            'summary': {
                'total_students': 5,
                'average_attendance': 80.0
            }
        }

    # If request wants JSON (API call), return JSON
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'success': True,
            'message': 'Attendance records retrieved successfully',
            'role': user_role,
            'data': attendance_data
        }), 200
    
    # Otherwise render HTML template
    return render_template('view_attendance.html', 
                         role=user_role,
                         data=attendance_data,
                         current_user=current_user)


@attendance_bp.route('/mark', methods=['GET', 'POST'])
@login_required
@require_role('teacher', 'admin')
def mark_attendance():
    """Mark attendance for students.

    Accessible by: teacher, admin
    
    GET: Display the attendance marking form
    POST: Process attendance submission

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
    # If GET request, show the form
    if request.method == 'GET':
        # Sample students for demo - in production, fetch from database
        sample_students = [
            {'id': 1, 'name': 'Student User', 'srn': 'PES1UG21CS001'},
            {'id': 2, 'name': 'Sample Student 2', 'srn': 'PES1UG21CS002'},
            {'id': 3, 'name': 'Sample Student 3', 'srn': 'PES1UG21CS003'},
        ]
        return render_template('mark_attendance.html', 
                             today=datetime.now().strftime('%Y-%m-%d'),
                             students=sample_students)
    
    user_role = get_user_role()

    # Handle form submission (from web form)
    if request.form:
        absentees = request.form.getlist('absentees')
        # In production, save to database here
        flash(f'Attendance marked successfully! {len(absentees)} student(s) marked absent.', 'success')
        return redirect(url_for('attendance.mark_attendance'))
    
    # Handle JSON API requests
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

    # Fetch the attendance record from database
    attendance_record = db.session.get(Attendance, attendance_id)

    if not attendance_record:
        return jsonify({
            'success': False,
            'error': 'Attendance record not found',
            'message': f'No attendance record found with ID {attendance_id}'
        }), 404

    # Store the previous status for audit trail
    previous_status = 'present' if attendance_record.is_present else 'absent'

    # Check if trying to set the same status
    if previous_status == new_status:
        return jsonify({
            'success': False,
            'error': 'No change needed',
            'message': f'Attendance is already marked as {new_status}'
        }), 400

    # Update the attendance record
    attendance_record.is_present = new_status == 'present'
    attendance_record.is_overridden = True
    attendance_record.override_reason = reason
    attendance_record.overridden_by = current_user.id
    attendance_record.override_timestamp = datetime.utcnow().isoformat()

    try:
        db.session.commit()

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
                'student_id': attendance_record.student_id,
                'date': attendance_record.date.isoformat(),
                'previous_status': previous_status,
                'new_status': new_status,
                'reason': reason,
                'timestamp': attendance_record.override_timestamp
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': f'Failed to save override: {str(e)}'
        }), 500


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

    if new_status not in ['present', 'absent']:
        return jsonify({
            'success': False,
            'error': 'Invalid status',
            'message': 'Status must be either "present" or "absent"'
        }), 400

    # Fetch the attendance record from database
    attendance_record = db.session.get(Attendance, attendance_id)

    if not attendance_record:
        return jsonify({
            'success': False,
            'error': 'Attendance record not found'
        }), 404

    # Store previous status
    previous_status = 'present' if attendance_record.is_present else 'absent'

    if previous_status == new_status:
        return jsonify({
            'success': False,
            'error': 'No change needed'
        }), 400

    # Update the attendance record
    attendance_record.is_present = new_status == 'present'
    attendance_record.is_overridden = True
    attendance_record.override_reason = reason
    attendance_record.overridden_by = jwt_user.get('user_id')
    attendance_record.override_timestamp = datetime.utcnow().isoformat()

    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Attendance overridden via JWT',
            'auth_method': 'JWT',
            'overridden_by': jwt_user,
            'override': {
                'attendance_id': attendance_id,
                'student_id': attendance_record.student_id,
                'date': attendance_record.date.isoformat(),
                'previous_status': previous_status,
                'new_status': new_status,
                'reason': reason,
                'timestamp': attendance_record.override_timestamp
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500
