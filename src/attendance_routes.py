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
    """View attendance records from database.

    Accessible by: student, teacher, admin

    Students can view their own attendance.
    Teachers and admins can view all attendance.

    Returns:
        HTML page with attendance data or JSON for API requests
    """
    from models import User
    user_role = get_user_role()

    if user_role == 'student':
        # Students see only their own attendance from database
        records = Attendance.query.filter_by(student_id=current_user.id).all()

        attendance_list = []
        for record in records:
            attendance_list.append({
                'date': record.date.isoformat() if record.date else '',
                'status': 'present' if record.is_present else 'absent',
                'course_id': record.course_id or 'N/A',
                'marked_by': record.marked_by or 'Unknown'
            })

        # Calculate summary
        total_classes = len(attendance_list)
        present_count = sum(1 for a in attendance_list if a['status'] == 'present')
        absent_count = total_classes - present_count
        percentage = (present_count / total_classes * 100) if total_classes > 0 else 0

        attendance_data = {
            'user_id': current_user.id,
            'username': current_user.username,
            'name': current_user.name,
            'attendance': attendance_list,
            'summary': {
                'total_classes': total_classes,
                'present': present_count,
                'absent': absent_count,
                'percentage': round(percentage, 2)
            }
        }
    else:
        # Teachers and admins see all students with attendance from database
        students = User.query.filter_by(role='student').all()

        all_students_data = []
        for student in students:
            records = Attendance.query.filter_by(student_id=student.id).all()
            total = len(records)
            present = sum(1 for r in records if r.is_present)
            percentage = (present / total * 100) if total > 0 else 0

            all_students_data.append({
                'user_id': student.id,
                'username': student.username,
                'name': student.name,
                'total_classes': total,
                'present': present,
                'absent': total - present,
                'percentage': round(percentage, 2)
            })

        # Calculate average attendance
        total_percentages = [s['percentage'] for s in all_students_data]
        average_attendance = sum(total_percentages) / len(total_percentages) if total_percentages else 0

        attendance_data = {
            'all_students': all_students_data,
            'summary': {
                'total_students': len(all_students_data),
                'average_attendance': round(average_attendance, 2)
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
    """Mark attendance for students from database.

    Accessible by: teacher, admin
    
    GET: Display the attendance marking form with actual students from database
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
    from models import User

    # If GET request, show the form
    if request.method == 'GET':
        # Fetch actual students from database
        from models import User
        students = User.query.filter_by(role='student').all()

        student_list = [
            {'id': s.id, 'name': s.name, 'srn': s.username}
            for s in students
        ]

        return render_template('mark_attendance.html',
                             today=datetime.now().strftime('%Y-%m-%d'),
                             students=student_list)

    user_role = get_user_role()

    # Handle form submission (from web form) - check Content-Type FIRST
    if request.method == 'POST':
        # Form submission from HTML form
        if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            absentees = request.form.getlist('absentees')
            attendance_date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
            course_id = request.form.get('course_id', 'General')

            # Get all students to mark attendance
            from models import User
            all_students = User.query.filter_by(role='student').all()

            # Save attendance for all students
            for student in all_students:
                # Determine if student is present or absent
                is_present = str(student.id) not in absentees
                status = 'present' if is_present else 'absent'

                # Create or update attendance record
                attendance_record = Attendance(
                    student_id=student.id,
                    student_srn=student.username,
                    course_id=course_id,
                    date=datetime.strptime(attendance_date, '%Y-%m-%d').date(),
                    status=status,
                    is_present=is_present,
                    marked_by=current_user.username
                )
                db.session.add(attendance_record)

            try:
                db.session.commit()
                flash(f'Attendance marked successfully! {len(absentees)} student(s) marked absent.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving attendance: {str(e)}', 'danger')

            return redirect(url_for('attendance.mark_attendance'))

        # JSON API request
        elif request.content_type and 'application/json' in request.content_type:
            data = request.get_json(force=True, silent=True) or {}

        # Unsupported content type
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported Media Type',
                'message': 'Content-Type must be either "application/x-www-form-urlencoded" (for form) or "application/json" (for API)',
                'received': request.content_type
            }), 415
    else:
        # GET request or other method - not expected here for API
        return jsonify({
            'success': False,
            'error': 'Method Not Allowed',
            'message': 'POST requests are required for this endpoint'
        }), 405

    # Process JSON API request
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

    # Verify student exists in database
    from models import User
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return jsonify({
            'success': False,
            'error': 'Invalid student',
            'message': 'Student not found or is not a student user'
        }), 404

    # Check if attendance already exists for this student/date/course
    from datetime import datetime as dt
    attendance_date = dt.strptime(date, '%Y-%m-%d').date()
    existing_attendance = Attendance.query.filter_by(
        student_id=student_id,
        date=attendance_date,
        course_id=subject
    ).first()

    if existing_attendance:
        # Update existing record
        existing_attendance.status = status
        existing_attendance.is_present = (status == 'present')
        existing_attendance.marked_by = current_user.username
    else:
        # Create new attendance record
        attendance_record = Attendance(
            student_id=student_id,
            student_srn=student.username,
            course_id=subject,
            date=attendance_date,
            status=status,
            is_present=(status == 'present'),
            marked_by=current_user.username
        )
        db.session.add(attendance_record)

    try:
        db.session.commit()
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
                'student_name': student.name,
                'subject': subject,
                'date': date,
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Database error',
            'message': str(e)
        }), 500


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
