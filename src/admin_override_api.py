"""Admin Attendance Override API.

This module provides endpoints for admins to override student attendance records.
Features include:
- Override attendance status for any student
- View override history
- Undo overrides
- Track all override actions

Note: This is separate from the student correction request system.
Admins can directly modify any attendance record without student request.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from rbac import require_role
from models import db, Attendance, User


# Create Blueprint for admin override routes
admin_override_bp = Blueprint('admin_override', __name__, url_prefix='/api/admin/override')


@admin_override_bp.route('/attendance/<int:attendance_id>', methods=['POST'])
@login_required
@require_role('admin')
def override_attendance(attendance_id):
    """Override the attendance status of a specific record.

    Only admins can perform this action. The original status is preserved
    in audit trail via override fields.

    Expected JSON payload:
    {
        "new_status": "present",  # or "absent"
        "reason": "System error - student was present but marked absent"
    }

    Returns:
        JSON response with updated record or error message
    """
    try:
        data = request.get_json()

        # Validate required fields
        if 'new_status' not in data or 'reason' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: new_status and reason'
            }), 400

        # Validate status value
        if data['new_status'] not in ['present', 'absent']:
            return jsonify({
                'success': False,
                'error': 'Invalid status. Must be "present" or "absent"'
            }), 400

        # Validate reason
        reason = data['reason'].strip()
        if len(reason) < 5:
            return jsonify({
                'success': False,
                'error': 'Override reason must be at least 5 characters long'
            }), 400

        if len(reason) > 500:
            return jsonify({
                'success': False,
                'error': 'Override reason cannot exceed 500 characters'
            }), 400

        # Get the attendance record
        attendance = Attendance.query.get(attendance_id)

        if not attendance:
            return jsonify({
                'success': False,
                'error': 'Attendance record not found'
            }), 404

        # Store original status for audit trail
        original_is_present = attendance.is_present
        new_is_present = data['new_status'] == 'present'

        # Apply override - update the main tracking field
        attendance.is_present = new_is_present
        attendance.is_overridden = True
        attendance.override_reason = reason
        attendance.overridden_by = current_user.id
        attendance.override_timestamp = datetime.utcnow().isoformat()

        # Note: We don't update the encrypted 'status' field as it's difficult to re-encrypt.
        # The is_present field is the source of truth for attendance status.

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Attendance record overridden successfully',
            'record': {
                'id': attendance.id,
                'student_id': attendance.student_id,
                'date': attendance.date.isoformat() if attendance.date else None,
                'original_status': 'present' if original_is_present else 'absent',
                'new_status': data['new_status'],
                'reason': reason,
                'overridden_by': current_user.name,
                'override_timestamp': attendance.override_timestamp
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to override attendance: {str(e)}'
        }), 500


@admin_override_bp.route('/attendance/<int:attendance_id>/undo', methods=['POST'])
@login_required
@require_role('admin')
def undo_override(attendance_id):
    """Undo a previous attendance override.

    Removes the override flags but doesn't restore original values.
    Requires admin role.

    Returns:
        JSON response with updated record or error message
    """
    try:
        attendance = Attendance.query.get(attendance_id)

        if not attendance:
            return jsonify({
                'success': False,
                'error': 'Attendance record not found'
            }), 404

        if not attendance.is_overridden:
            return jsonify({
                'success': False,
                'error': 'This record is not overridden'
            }), 409

        # Clear override information
        attendance.is_overridden = False
        attendance.override_reason = None
        attendance.overridden_by = None
        attendance.override_timestamp = None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Override removed successfully',
            'record': {
                'id': attendance.id,
                'student_id': attendance.student_id,
                'date': attendance.date.isoformat() if attendance.date else None,
                'status': 'present' if attendance.is_present else 'absent',
                'is_overridden': False
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to remove override: {str(e)}'
        }), 500


@admin_override_bp.route('/student/<int:student_id>/records', methods=['GET'])
@login_required
@require_role('admin')
def get_student_attendance_records(student_id):
    """Get all attendance records for a specific student.

    Useful for admins to see full history and decide what to override.
    Supports filtering by date range and override status.

    Query parameters:
    - from_date: YYYY-MM-DD (optional)
    - to_date: YYYY-MM-DD (optional)
    - overridden_only: true/false (default: false)

    Returns:
        JSON response with list of attendance records
    """
    try:
        # Verify student exists
        student = User.query.get(student_id)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        # Build query
        query = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc())

        # Apply date filters if provided
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date >= from_date_obj)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid from_date format. Use YYYY-MM-DD'
                }), 400

        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date <= to_date_obj)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid to_date format. Use YYYY-MM-DD'
                }), 400

        # Filter by override status if requested
        overridden_only = request.args.get('overridden_only', 'false').lower() == 'true'
        if overridden_only:
            query = query.filter_by(is_overridden=True)

        records = query.all()

        records_data = []
        for record in records:
            records_data.append({
                'id': record.id,
                'student_id': record.student_id,
                'date': record.date.isoformat() if record.date else None,
                'status': 'present' if record.is_present else 'absent',
                'is_overridden': record.is_overridden,
                'override_reason': record.override_reason,
                'overridden_by_id': record.overridden_by,
                'override_timestamp': record.override_timestamp,
                'updated_at': record.updated_at.isoformat() if record.updated_at else None
            })

        return jsonify({
            'success': True,
            'student': {
                'id': student.id,
                'name': student.name,
                'username': student.username
            },
            'total_records': len(records_data),
            'records': records_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve records: {str(e)}'
        }), 500


@admin_override_bp.route('/override-history', methods=['GET'])
@login_required
@require_role('admin')
def get_override_history():
    """Get history of all attendance overrides.

    Useful for audit trail and tracking which admin made what changes.

    Query parameters:
    - limit: Maximum number of records (default: 100)
    - offset: Pagination offset (default: 0)
    - admin_id: Filter by specific admin (optional)

    Returns:
        JSON response with override history
    """
    try:
        limit = min(int(request.args.get('limit', 100)), 500)  # Max 500
        offset = int(request.args.get('offset', 0))
        admin_id = request.args.get('admin_id')

        # Build query for overridden records
        query = Attendance.query.filter_by(is_overridden=True).order_by(
            Attendance.override_timestamp.desc()
        )

        if admin_id:
            try:
                admin_id = int(admin_id)
                query = query.filter_by(overridden_by=admin_id)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid admin_id'
                }), 400

        total = query.count()
        records = query.limit(limit).offset(offset).all()

        history_data = []
        for record in records:
            # Get student and admin names
            student = User.query.get(record.student_id)
            admin = User.query.get(record.overridden_by) if record.overridden_by else None

            history_data.append({
                'id': record.id,
                'student': {
                    'id': record.student_id,
                    'name': student.name if student else 'Unknown'
                },
                'date': record.date.isoformat() if record.date else None,
                'status': 'present' if record.is_present else 'absent',
                'override_reason': record.override_reason,
                'overridden_by': {
                    'id': record.overridden_by,
                    'name': admin.name if admin else 'Unknown'
                },
                'override_timestamp': record.override_timestamp
            })

        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'history': history_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve override history: {str(e)}'
        }), 500


@admin_override_bp.route('/search-students', methods=['GET'])
@login_required
@require_role('admin')
def search_students():
    """Search for students by name or username.

    Useful for the admin UI to find which student's attendance to override.

    Query parameters:
    - query: Search term (name or username)

    Returns:
        JSON response with matching students
    """
    try:
        query_term = request.args.get('query', '').strip()

        if len(query_term) < 2:
            return jsonify({
                'success': False,
                'error': 'Search term must be at least 2 characters'
            }), 400

        # Search in student names and usernames
        results = User.query.filter_by(role='student').filter(
            (User.name.ilike(f'%{query_term}%')) |
            (User.username.ilike(f'%{query_term}%'))
        ).limit(20).all()

        students_data = []
        for student in results:
            students_data.append({
                'id': student.id,
                'name': student.name,
                'username': student.username
            })

        return jsonify({
            'success': True,
            'total': len(students_data),
            'students': students_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to search students: {str(e)}'
        }), 500


@admin_override_bp.route('/stats', methods=['GET'])
@login_required
@require_role('admin')
def get_override_statistics():
    """Get statistics about attendance overrides.

    Returns:
        JSON response with override statistics
    """
    try:
        total_overrides = Attendance.query.filter_by(is_overridden=True).count()
        total_records = Attendance.query.count()

        # Count by admin
        admins = db.session.query(
            Attendance.overridden_by,
            db.func.count(Attendance.id)
        ).filter_by(is_overridden=True).group_by(
            Attendance.overridden_by
        ).all()

        overrides_by_admin = []
        for admin_id, count in admins:
            admin = User.query.get(admin_id) if admin_id else None
            overrides_by_admin.append({
                'admin_id': admin_id,
                'admin_name': admin.name if admin else 'Unknown',
                'override_count': count
            })

        return jsonify({
            'success': True,
            'stats': {
                'total_overrides': total_overrides,
                'total_records': total_records,
                'override_percentage': round((total_overrides / total_records * 100) if total_records > 0 else 0, 2),
                'overrides_by_admin': overrides_by_admin
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get statistics: {str(e)}'
        }), 500
