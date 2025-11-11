"""Audit Trail API Routes for SAS-94.

Provides REST API endpoints for accessing audit logs.
All endpoints require admin authentication.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from functools import wraps

from audit_trail import (
    get_audit_logs,
    generate_audit_report,
    AuditLog
)
from models import db

audit_api = Blueprint('audit_api', __name__, url_prefix='/api/audit')


def admin_required(func):
    """Decorator to require admin role for audit access.
    
    Returns JSON responses for API compatibility.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if user has admin role
        user_role = getattr(current_user, 'role', None)
        if user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return func(*args, **kwargs)
    return wrapper


@audit_api.route('/logs', methods=['GET'])
@admin_required
def get_logs():
    """Get audit logs with optional filters.
    
    Query Parameters:
        start_date (str): Start date (ISO format)
        end_date (str): End date (ISO format)
        user_id (int): Filter by user ID
        student_srn (str): Filter by student SRN
        course_id (str): Filter by course ID
        action_type (str): Filter by action type (CREATE/UPDATE/DELETE)
        limit (int): Maximum records to return (default: 100)
        offset (int): Number of records to skip (default: 0)
    
    Returns:
        JSON response with audit logs and metadata
    """
    try:
        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id', type=int)
        student_srn = request.args.get('student_srn')
        course_id = request.args.get('course_id')
        action_type = request.args.get('action_type')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Convert date strings to datetime objects
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        
        # Get audit logs
        logs, total_count = get_audit_logs(
            start_date=start_dt,
            end_date=end_dt,
            user_id=user_id,
            student_srn=student_srn,
            course_id=course_id,
            action_type=action_type,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'logs': [log.to_dict() for log in logs]
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve audit logs: {str(e)}'}), 500


@audit_api.route('/logs/<int:log_id>', methods=['GET'])
@admin_required
def get_log_detail(log_id):
    """Get detailed information for a specific audit log entry.
    
    Args:
        log_id (int): ID of the audit log entry
    
    Returns:
        JSON response with audit log details
    """
    try:
        log = AuditLog.query.get(log_id)
        
        if not log:
            return jsonify({'error': 'Audit log entry not found'}), 404
        
        return jsonify({
            'success': True,
            'log': log.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve audit log: {str(e)}'}), 500


@audit_api.route('/report', methods=['GET'])
@admin_required
def get_report():
    """Generate an audit report.
    
    Query Parameters:
        start_date (str): Start date (ISO format)
        end_date (str): End date (ISO format)
        user_id (int): Filter by user ID
        student_srn (str): Filter by student SRN
        course_id (str): Filter by course ID
        format (str): Report format (json/summary/csv, default: json)
    
    Returns:
        Report in requested format
    """
    try:
        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id', type=int)
        student_srn = request.args.get('student_srn')
        course_id = request.args.get('course_id')
        report_format = request.args.get('format', 'json')
        
        # Convert date strings to datetime objects
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Generate report
        report = generate_audit_report(
            start_date=start_dt,
            end_date=end_dt,
            user_id=user_id,
            student_srn=student_srn,
            course_id=course_id,
            format=report_format
        )
        
        if report_format == 'csv':
            from flask import Response
            return Response(
                report,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=audit_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
        else:
            return jsonify({
                'success': True,
                'report': report
            }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to generate report: {str(e)}'}), 500


@audit_api.route('/stats', methods=['GET'])
@admin_required
def get_statistics():
    """Get audit log statistics.
    
    Query Parameters:
        start_date (str): Start date for statistics (ISO format)
        end_date (str): End date for statistics (ISO format)
    
    Returns:
        JSON response with statistics
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get summary report
        stats = generate_audit_report(
            start_date=start_dt,
            end_date=end_dt,
            format='summary'
        )
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500


@audit_api.route('/users', methods=['GET'])
@admin_required
def get_users_with_activity():
    """Get list of users who have performed audited actions.
    
    Returns:
        JSON response with list of users and their activity counts
    """
    try:
        from sqlalchemy import func
        
        # Query for users with audit log counts
        users = db.session.query(
            AuditLog.user_id,
            AuditLog.username,
            AuditLog.user_role,
            func.count(AuditLog.id).label('action_count')
        ).group_by(
            AuditLog.user_id,
            AuditLog.username,
            AuditLog.user_role
        ).order_by(
            func.count(AuditLog.id).desc()
        ).all()
        
        user_list = [
            {
                'user_id': user[0],
                'username': user[1],
                'role': user[2],
                'action_count': user[3]
            }
            for user in users
        ]
        
        return jsonify({
            'success': True,
            'users': user_list,
            'total_users': len(user_list)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get user list: {str(e)}'}), 500


@audit_api.route('/timeline', methods=['GET'])
@admin_required
def get_timeline():
    """Get audit activity timeline.
    
    Query Parameters:
        days (int): Number of days to look back (default: 7)
        student_srn (str): Filter by student SRN
        course_id (str): Filter by course ID
    
    Returns:
        JSON response with daily activity counts
    """
    try:
        from sqlalchemy import func
        from datetime import timedelta
        
        days = request.args.get('days', 7, type=int)
        student_srn = request.args.get('student_srn')
        course_id = request.args.get('course_id')
        
        # Calculate start date
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = db.session.query(
            func.date(AuditLog.timestamp).label('date'),
            AuditLog.action_type,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        )
        
        if student_srn:
            query = query.filter(AuditLog.student_srn == student_srn)
        
        if course_id:
            query = query.filter(AuditLog.course_id == course_id)
        
        results = query.group_by(
            func.date(AuditLog.timestamp),
            AuditLog.action_type
        ).order_by(
            func.date(AuditLog.timestamp).desc()
        ).all()
        
        # Organize data by date
        timeline = {}
        for row in results:
            date_str = str(row[0])
            action_type = row[1]
            count = row[2]
            
            if date_str not in timeline:
                timeline[date_str] = {
                    'CREATE': 0,
                    'UPDATE': 0,
                    'DELETE': 0
                }
            
            timeline[date_str][action_type] = count
        
        return jsonify({
            'success': True,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'timeline': timeline
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get timeline: {str(e)}'}), 500
