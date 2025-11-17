"""Attendance Correction Request API.

This module provides endpoints for students to submit correction requests
for their attendance status. Features include:
- Submit correction requests with reason
- View submitted requests and their status
- Cancel pending requests
- Retrieve request history

Note: This API focuses on student submission only. Review/approval logic
is handled separately by the admin/faculty system.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import text

from rbac import require_role
from models import db, AttendanceCorrectionRequest


# Create Blueprint for correction request routes
correction_bp = Blueprint('correction', __name__, url_prefix='/correction')


@correction_bp.route('/student-attendance-records', methods=['GET'])
@login_required
@require_role('student')
def get_student_attendance_records():
    """Get all attendance records for the current student.

    Used by the frontend to populate the correction request form with
    available records that can be corrected.

    Returns:
        JSON response with list of attendance records
    """
    try:
        # Query directly using SQL to get raw data
        records = db.session.execute(
            text("""
                SELECT id, student_id, date, is_present, updated_at
                FROM attendance
                WHERE student_id = :student_id
                ORDER BY date DESC
            """),
            {'student_id': current_user.id}
        ).fetchall()

        records_data = []
        for record in records:
            record_id, _, date, is_present, updated_at = record

            # Skip records with missing date
            if not date:
                continue

            # Convert is_present to status
            status = 'present' if is_present else 'absent'
            course_id = f"Course_{record_id}"  # Use generic course name

            records_data.append({
                'course_id': course_id,
                'date': str(date),
                'status': status,
                'marked_by': 'Unknown',
                'marked_date': str(updated_at) if updated_at else '',
                'record_id': record_id
            })

        return jsonify({
            'success': True,
            'records': records_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve attendance records: {str(e)}'
        }), 500


@correction_bp.route('/submit', methods=['POST'])
@login_required
@require_role('student')
def submit_correction_request():
    """Submit an attendance correction request.

    Students can request a change to their attendance status for any
    specific course on a specific date with a reason.

    Expected JSON payload:
    {
        "course_id": "CS101",
        "date": "2024-01-15",
        "current_status": "absent",
        "requested_status": "present",
        "reason": "I was sick but attended online classes"
    }

    Returns:
        JSON response with request details or error message
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['course_id', 'date', 'current_status', 'requested_status', 'reason']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Validate status values
        valid_statuses = ['present', 'absent']
        if data['current_status'] not in valid_statuses or data['requested_status'] not in valid_statuses:
            return jsonify({
                'success': False,
                'error': 'Status must be either "present" or "absent"'
            }), 400

        # Prevent duplicate requests for same attendance record
        date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()

        existing_pending = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id,
            course_id=data['course_id'],
            date=date_obj,
            status='pending'
        ).first()

        if existing_pending:
            return jsonify({
                'success': False,
                'error': 'A pending correction request already exists for this attendance record'
            }), 409

        # Validate that the attendance record exists (by date and student)
        record = db.session.execute(
            text("""
                SELECT id, is_present FROM attendance
                WHERE student_id = :student_id AND date = :date LIMIT 1
            """),
            {'student_id': current_user.id, 'date': date_obj}
        ).first()

        if not record:
            return jsonify({
                'success': False,
                'error': 'No attendance record found for this date'
            }), 404

        # Validate reason length
        reason = data['reason'].strip()
        if len(reason) < 10:
            return jsonify({
                'success': False,
                'error': 'Reason must be at least 10 characters long'
            }), 400

        if len(reason) > 500:
            return jsonify({
                'success': False,
                'error': 'Reason cannot exceed 500 characters'
            }), 400

        # Create new correction request
        correction_request = AttendanceCorrectionRequest(
            student_id=current_user.id,
            student_name=current_user.name,
            course_id=data['course_id'],
            date=date_obj,
            current_status=data['current_status'],
            requested_status=data['requested_status'],
            reason=reason,
            status='pending',
            submitted_at=datetime.utcnow()
        )

        db.session.add(correction_request)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Correction request submitted successfully',
            'request_id': correction_request.id,
            'request': {
                'id': correction_request.id,
                'course_id': correction_request.course_id,
                'date': correction_request.date.isoformat(),
                'current_status': correction_request.current_status,
                'requested_status': correction_request.requested_status,
                'reason': correction_request.reason,
                'status': correction_request.status,
                'submitted_at': correction_request.submitted_at.isoformat()
            }
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to submit correction request: {str(e)}'
        }), 500


@correction_bp.route('/list', methods=['GET'])
@login_required
@require_role('student')
def list_correction_requests():
    """Get all correction requests submitted by the current student.

    Supports filtering by status via query parameter:
    - /correction/list?status=pending
    - /correction/list?status=approved
    - /correction/list?status=rejected
    - /correction/list?status=cancelled
    - /correction/list (returns all requests)

    Returns:
        JSON response with list of correction requests
    """
    try:
        status_filter = request.args.get('status', None)

        query = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id
        ).order_by(AttendanceCorrectionRequest.submitted_at.desc())

        if status_filter:
            if status_filter not in ['pending', 'approved', 'rejected', 'cancelled']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid status filter'
                }), 400
            query = query.filter_by(status=status_filter)

        requests = query.all()

        requests_data = []
        for req in requests:
            requests_data.append({
                'id': req.id,
                'course_id': req.course_id,
                'date': req.date.isoformat(),
                'current_status': req.current_status,
                'requested_status': req.requested_status,
                'reason': req.reason,
                'status': req.status,
                'submitted_at': req.submitted_at.isoformat(),
                'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
                'admin_notes': req.admin_notes
            })

        return jsonify({
            'success': True,
            'total': len(requests_data),
            'requests': requests_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve correction requests: {str(e)}'
        }), 500


@correction_bp.route('/<int:request_id>', methods=['GET'])
@login_required
@require_role('student')
def get_correction_request(request_id):
    """Get details of a specific correction request.

    Students can only view their own requests.

    Args:
        request_id: ID of the correction request

    Returns:
        JSON response with request details or error message
    """
    try:
        correction_request = AttendanceCorrectionRequest.query.get(request_id)

        if not correction_request:
            return jsonify({
                'success': False,
                'error': 'Correction request not found'
            }), 404

        # Ensure student can only view their own requests
        if correction_request.student_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to view this request'
            }), 403

        request_data = {
            'id': correction_request.id,
            'course_id': correction_request.course_id,
            'date': correction_request.date.isoformat(),
            'current_status': correction_request.current_status,
            'requested_status': correction_request.requested_status,
            'reason': correction_request.reason,
            'status': correction_request.status,
            'submitted_at': correction_request.submitted_at.isoformat(),
            'reviewed_at': correction_request.reviewed_at.isoformat() if correction_request.reviewed_at else None,
            'admin_notes': correction_request.admin_notes
        }

        return jsonify({
            'success': True,
            'request': request_data
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve correction request: {str(e)}'
        }), 500


@correction_bp.route('/<int:request_id>/cancel', methods=['POST'])
@login_required
@require_role('student')
def cancel_correction_request(request_id):
    """Cancel a pending correction request.

    Students can only cancel their own pending requests. Once approved
    or rejected, requests cannot be cancelled.

    Args:
        request_id: ID of the correction request to cancel

    Returns:
        JSON response with updated request or error message
    """
    try:
        correction_request = AttendanceCorrectionRequest.query.get(request_id)

        if not correction_request:
            return jsonify({
                'success': False,
                'error': 'Correction request not found'
            }), 404

        # Ensure student can only cancel their own requests
        if correction_request.student_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'You do not have permission to cancel this request'
            }), 403

        # Only pending requests can be cancelled
        if correction_request.status != 'pending':
            return jsonify({
                'success': False,
                'error': f'Cannot cancel a {correction_request.status} request'
            }), 409

        # Update status to cancelled
        correction_request.status = 'cancelled'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Correction request cancelled successfully',
            'request': {
                'id': correction_request.id,
                'course_id': correction_request.course_id,
                'date': correction_request.date.isoformat(),
                'status': correction_request.status
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to cancel correction request: {str(e)}'
        }), 500


@correction_bp.route('/stats', methods=['GET'])
@login_required
@require_role('student')
def get_correction_stats():
    """Get summary statistics of correction requests for the current student.

    Returns counts of requests by status.

    Returns:
        JSON response with statistics
    """
    try:
        total = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id
        ).count()

        pending = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id,
            status='pending'
        ).count()

        approved = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id,
            status='approved'
        ).count()

        rejected = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id,
            status='rejected'
        ).count()

        cancelled = AttendanceCorrectionRequest.query.filter_by(
            student_id=current_user.id,
            status='cancelled'
        ).count()

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'cancelled': cancelled
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve statistics: {str(e)}'
        }), 500
