"""Teacher Review API for Attendance Correction Requests (SAS-99).

This module provides endpoints for teachers to review and approve/deny
correction requests submitted by students. Features include:
- View pending requests within 48-hour window
- Approve/deny requests with optional notes
- View request history
- Auto-expire requests after 48 hours
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from rbac import require_role
from models import db, AttendanceCorrectionRequest
from audit_trail import create_audit_entry
from sqlalchemy import text


# Create Blueprint for teacher review routes
teacher_review_bp = Blueprint('teacher_review', __name__, url_prefix='/teacher-review')


@teacher_review_bp.route('/pending-requests', methods=['GET'])
@login_required
@require_role('teacher', 'admin')
def get_pending_requests():
    """Get all pending correction requests for teacher review.

    Filters requests that are:
    - Still pending (not reviewed)
    - Submitted within last 48 hours (active window)
    
    Requests older than 48 hours are automatically marked as expired.

    Returns:
        JSON response with list of pending requests
    """
    try:
        # Calculate 48-hour cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=48)
        
        # Auto-expire old pending requests
        expired_requests = AttendanceCorrectionRequest.query.filter(
            AttendanceCorrectionRequest.status == 'pending',
            AttendanceCorrectionRequest.submitted_at < cutoff_time
        ).all()
        
        for req in expired_requests:
            req.status = 'expired'
            req.admin_notes = 'Request expired - not reviewed within 48 hours'
            create_audit_entry(
                action_type='UPDATE',
                record_type='correction_request',
                record_id=req.id,
                old_values={'status': 'pending'},
                new_values={'status': 'expired'},
                reason='auto_expired_48h'
            )
        
        if expired_requests:
            db.session.commit()

        # Get all pending requests (within 48-hour window)
        pending_requests = AttendanceCorrectionRequest.query.filter_by(
            status='pending'
        ).order_by(AttendanceCorrectionRequest.submitted_at.asc()).all()

        requests_data = []
        for req in pending_requests:
            # Calculate time remaining
            time_elapsed = datetime.utcnow() - req.submitted_at
            hours_remaining = 48 - (time_elapsed.total_seconds() / 3600)
            
            requests_data.append({
                'id': req.id,
                'student_id': req.student_id,
                'student_name': req.student_name,
                'course_id': req.course_id,
                'date': req.date.isoformat(),
                'current_status': req.current_status,
                'requested_status': req.requested_status,
                'reason': req.reason,
                'submitted_at': req.submitted_at.isoformat(),
                'hours_remaining': round(hours_remaining, 1),
                'is_urgent': hours_remaining < 6  # Flag urgent if less than 6 hours
            })

        return jsonify({
            'success': True,
            'total': len(requests_data),
            'requests': requests_data
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve pending requests: {str(e)}'
        }), 500


@teacher_review_bp.route('/approve/<int:request_id>', methods=['POST'])
@login_required
@require_role('teacher', 'admin')
def approve_request(request_id):
    """Approve an attendance correction request.

    Updates the attendance record to the requested status and marks
    the request as approved.

    Args:
        request_id: ID of the correction request

    Expected JSON payload (optional):
    {
        "notes": "Verified with student. Valid reason."
    }

    Returns:
        JSON response with updated request details
    """
    try:
        correction_request = AttendanceCorrectionRequest.query.get(request_id)

        if not correction_request:
            return jsonify({
                'success': False,
                'error': 'Correction request not found'
            }), 404

        if correction_request.status != 'pending':
            return jsonify({
                'success': False,
                'error': f'Cannot approve a {correction_request.status} request'
            }), 409

        # Check if still within 48-hour window
        time_elapsed = datetime.utcnow() - correction_request.submitted_at
        if time_elapsed > timedelta(hours=48):
            correction_request.status = 'expired'
            correction_request.admin_notes = 'Request expired - exceeded 48-hour window'
            db.session.commit()
            return jsonify({
                'success': False,
                'error': 'Request has expired (exceeded 48-hour review window)'
            }), 409

        # Get optional notes
        data = request.get_json() or {}
        admin_notes = data.get('notes', '').strip()

        # Update attendance record
        new_status = correction_request.requested_status
        is_present = (new_status == 'present')
        
        # Update the attendance record in database
        result = db.session.execute(
            text("""
                UPDATE attendance 
                SET is_present = :is_present, 
                    updated_at = :updated_at
                WHERE student_id = :student_id 
                  AND date = :date
            """),
            {
                'is_present': is_present,
                'updated_at': datetime.utcnow(),
                'student_id': correction_request.student_id,
                'date': correction_request.date
            }
        )

        if result.rowcount == 0:
            return jsonify({
                'success': False,
                'error': 'Attendance record not found or update failed'
            }), 404

        # Update correction request status
        correction_request.status = 'approved'
        correction_request.reviewed_at = datetime.utcnow()
        correction_request.reviewed_by = current_user.id
        correction_request.admin_notes = admin_notes or 'Approved by teacher'

        db.session.commit()

        # Log audit event
        create_audit_entry(
            action_type='UPDATE',
            record_type='correction_request',
            record_id=request_id,
            old_values={'status': 'pending'},
            new_values={'status': 'approved', 'attendance_status': new_status},
            reason=f"Approved by teacher: {admin_notes}"
        )

        return jsonify({
            'success': True,
            'message': 'Correction request approved successfully',
            'request': {
                'id': correction_request.id,
                'status': correction_request.status,
                'reviewed_at': correction_request.reviewed_at.isoformat(),
                'reviewed_by': current_user.name,
                'admin_notes': correction_request.admin_notes
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to approve request: {str(e)}'
        }), 500


@teacher_review_bp.route('/deny/<int:request_id>', methods=['POST'])
@login_required
@require_role('teacher', 'admin')
def deny_request(request_id):
    """Deny an attendance correction request.

    Marks the request as rejected without updating the attendance record.

    Args:
        request_id: ID of the correction request

    Expected JSON payload:
    {
        "notes": "Insufficient evidence provided."
    }

    Returns:
        JSON response with updated request details
    """
    try:
        correction_request = AttendanceCorrectionRequest.query.get(request_id)

        if not correction_request:
            return jsonify({
                'success': False,
                'error': 'Correction request not found'
            }), 404

        if correction_request.status != 'pending':
            return jsonify({
                'success': False,
                'error': f'Cannot deny a {correction_request.status} request'
            }), 409

        # Check if still within 48-hour window
        time_elapsed = datetime.utcnow() - correction_request.submitted_at
        if time_elapsed > timedelta(hours=48):
            correction_request.status = 'expired'
            correction_request.admin_notes = 'Request expired - exceeded 48-hour window'
            db.session.commit()
            return jsonify({
                'success': False,
                'error': 'Request has expired (exceeded 48-hour review window)'
            }), 409

        # Get required notes
        data = request.get_json() or {}
        admin_notes = data.get('notes', '').strip()

        if not admin_notes:
            return jsonify({
                'success': False,
                'error': 'Notes are required when denying a request'
            }), 400

        # Update correction request status
        correction_request.status = 'rejected'
        correction_request.reviewed_at = datetime.utcnow()
        correction_request.reviewed_by = current_user.id
        correction_request.admin_notes = admin_notes

        db.session.commit()

        # Log audit event
        create_audit_entry(
            action_type='UPDATE',
            record_type='correction_request',
            record_id=request_id,
            old_values={'status': 'pending'},
            new_values={'status': 'rejected'},
            reason=f"Denied by teacher: {admin_notes}"
        )

        return jsonify({
            'success': True,
            'message': 'Correction request denied',
            'request': {
                'id': correction_request.id,
                'status': correction_request.status,
                'reviewed_at': correction_request.reviewed_at.isoformat(),
                'reviewed_by': current_user.name,
                'admin_notes': correction_request.admin_notes
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to deny request: {str(e)}'
        }), 500


@teacher_review_bp.route('/history', methods=['GET'])
@login_required
@require_role('teacher', 'admin')
def get_review_history():
    """Get history of all reviewed correction requests.

    Supports filtering by:
    - status: approved, rejected, expired
    - reviewer: reviewed_by user_id
    - date range: start_date, end_date

    Returns:
        JSON response with list of reviewed requests
    """
    try:
        # Get filter parameters
        status_filter = request.args.get('status')
        reviewer_id = request.args.get('reviewer_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = AttendanceCorrectionRequest.query.filter(
            AttendanceCorrectionRequest.status.in_(['approved', 'rejected', 'expired'])
        ).order_by(AttendanceCorrectionRequest.reviewed_at.desc())

        # Apply filters
        if status_filter:
            if status_filter not in ['approved', 'rejected', 'expired']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid status filter'
                }), 400
            query = query.filter_by(status=status_filter)

        if reviewer_id:
            query = query.filter_by(reviewed_by=int(reviewer_id))

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(AttendanceCorrectionRequest.reviewed_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AttendanceCorrectionRequest.reviewed_at < end_dt)

        requests = query.all()

        requests_data = []
        for req in requests:
            requests_data.append({
                'id': req.id,
                'student_id': req.student_id,
                'student_name': req.student_name,
                'course_id': req.course_id,
                'date': req.date.isoformat(),
                'current_status': req.current_status,
                'requested_status': req.requested_status,
                'reason': req.reason,
                'status': req.status,
                'submitted_at': req.submitted_at.isoformat(),
                'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
                'reviewed_by': req.reviewed_by,
                'admin_notes': req.admin_notes
            })

        return jsonify({
            'success': True,
            'total': len(requests_data),
            'requests': requests_data
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve history: {str(e)}'
        }), 500


@teacher_review_bp.route('/stats', methods=['GET'])
@login_required
@require_role('teacher', 'admin')
def get_review_stats():
    """Get statistics about correction request reviews.

    Returns counts of requests by status and review metrics.

    Returns:
        JSON response with statistics
    """
    try:
        total_pending = AttendanceCorrectionRequest.query.filter_by(
            status='pending'
        ).count()

        total_approved = AttendanceCorrectionRequest.query.filter_by(
            status='approved'
        ).count()

        total_rejected = AttendanceCorrectionRequest.query.filter_by(
            status='rejected'
        ).count()

        total_expired = AttendanceCorrectionRequest.query.filter_by(
            status='expired'
        ).count()

        # Count urgent requests (less than 6 hours remaining)
        cutoff_urgent = datetime.utcnow() - timedelta(hours=42)  # 48-6=42
        urgent_count = AttendanceCorrectionRequest.query.filter(
            AttendanceCorrectionRequest.status == 'pending',
            AttendanceCorrectionRequest.submitted_at < cutoff_urgent
        ).count()

        return jsonify({
            'success': True,
            'stats': {
                'pending': total_pending,
                'approved': total_approved,
                'rejected': total_rejected,
                'expired': total_expired,
                'urgent': urgent_count,
                'total_reviewed': total_approved + total_rejected
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve statistics: {str(e)}'
        }), 500
