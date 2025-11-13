"""SAS-96: Bunk Allowance REST API.

This module provides REST API endpoints for viewing bunk allowances
and remaining classes for students. All endpoints support both session-based
(Flask-Login) and token-based (JWT) authentication.

API Endpoints:
    Student Endpoints:
        - GET /api/bunk-allowance/student/<srn> 
          Get bunk allowance for all courses of a student
        - GET /api/bunk-allowance/student/<srn>/course/<course_id>
          Get bunk allowance for specific course
        - GET /api/bunk-allowance/breakdown/<srn>/<course_id>
          Get detailed breakdown with projections
    
    Faculty/Admin Endpoints:
        - GET /api/bunk-allowance/course/<course_id>/students
          Get all students' bunk status in a course
        - GET /api/bunk-allowance/critical
          Get students with critical attendance (below threshold)
        - POST /api/bunk-allowance/course/config
          Create or update course configuration
        - GET /api/bunk-allowance/course/<course_id>/config
          Get course configuration
        - PUT /api/bunk-allowance/course/<course_id>/refresh
          Refresh bunk calculations for all students in course

Authorization:
    - Students: Can only view their own data
    - Faculty: Can view all students in their courses
    - Admin: Full access to all endpoints

Authentication:
    Supports dual authentication:
    - Session-based: Flask-Login (cookie-based)
    - Token-based: JWT (Authorization: Bearer <token>)
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from auth_middleware import jwt_required, get_token_from_header, verify_jwt_token
from rbac import get_user_role
from bunk_allowance_service import BunkAllowanceService
from bunk_allowance_models import CourseConfig, StudentBunkAllowance, db


# Create Blueprint
bunk_allowance_bp = Blueprint('bunk_allowance', __name__, url_prefix='/api/bunk-allowance')


def get_current_user_info():
    """Get current user info from session or JWT token.
    
    Returns:
        dict: User information or None
    """
    # Try JWT token first
    token = get_token_from_header()
    if token:
        payload = verify_jwt_token(token)
        if payload:
            return {
                'username': payload.get('username'),
                'role': payload.get('role'),
                'srn': payload.get('username')  # Assuming username is SRN for students
            }
    
    # Fall back to Flask-Login session
    if current_user.is_authenticated:
        return {
            'username': getattr(current_user, 'username', 'unknown'),
            'role': get_user_role(),
            'srn': getattr(current_user, 'username', None)
        }
    
    return None


def require_authentication(f):
    """Decorator to require either JWT or session authentication."""
    def wrapper(*args, **kwargs):
        user_info = get_current_user_info()
        if not user_info:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@bunk_allowance_bp.route('/student/<string:srn>', methods=['GET'])
@require_authentication
def get_student_bunk_allowance(srn):
    """Get bunk allowance for a specific student across all courses.
    
    Args:
        srn (str): Student SRN
        
    Returns:
        JSON response with bunk allowance data
    """
    try:
        user_info = get_current_user_info()
        
        # Students can only view their own data, faculty/admin can view any
        if user_info['role'] == 'student' and user_info['srn'] != srn:
            return jsonify({'error': 'Unauthorized to view other student data'}), 403
        
        allowances = BunkAllowanceService.get_student_bunk_allowance(srn)
        
        return jsonify({
            'success': True,
            'student_srn': srn,
            'courses': allowances
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/student/<string:srn>/course/<string:course_id>', methods=['GET'])
@require_authentication
def get_student_course_bunk_allowance(srn, course_id):
    """Get bunk allowance for a specific student in a specific course.
    
    Args:
        srn (str): Student SRN
        course_id (str): Course ID
        
    Returns:
        JSON response with bunk allowance data
    """
    try:
        user_info = get_current_user_info()
        
        # Students can only view their own data
        if user_info['role'] == 'student' and user_info['srn'] != srn:
            return jsonify({'error': 'Unauthorized to view other student data'}), 403
        
        allowance = BunkAllowanceService.get_student_bunk_allowance(srn, course_id)
        
        return jsonify({
            'success': True,
            'data': allowance
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/breakdown/<string:srn>/<string:course_id>', methods=['GET'])
@require_authentication
def get_remaining_classes_breakdown(srn, course_id):
    """Get detailed breakdown of remaining classes and projections.
    
    Args:
        srn (str): Student SRN
        course_id (str): Course ID
        
    Returns:
        JSON response with detailed breakdown
    """
    try:
        user_info = get_current_user_info()
        
        # Students can only view their own data
        if user_info['role'] == 'student' and user_info['srn'] != srn:
            return jsonify({'error': 'Unauthorized to view other student data'}), 403
        
        breakdown = BunkAllowanceService.get_remaining_classes_breakdown(srn, course_id)
        
        return jsonify({
            'success': True,
            'data': breakdown
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/course/<string:course_id>/students', methods=['GET'])
@require_authentication
def get_course_students_bunk_status(course_id):
    """Get bunk allowance status for all students in a course.
    
    Faculty and admin only.
    
    Args:
        course_id (str): Course ID
        
    Returns:
        JSON response with all students' bunk allowance data
    """
    try:
        user_info = get_current_user_info()
        
        # Only faculty and admin can access
        if user_info['role'] not in ['teacher', 'admin']:
            return jsonify({'error': 'Faculty or admin access required'}), 403
        
        students = BunkAllowanceService.get_all_students_bunk_status(course_id)
        
        return jsonify({
            'success': True,
            'course_id': course_id,
            'total_students': len(students),
            'students': students
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/critical', methods=['GET'])
@require_authentication
def get_critical_students():
    """Get list of students with critical attendance.
    
    Faculty and admin only. Optional query parameter: course_id
    
    Returns:
        JSON response with critical students
    """
    try:
        user_info = get_current_user_info()
        
        # Only faculty and admin can access
        if user_info['role'] not in ['teacher', 'admin']:
            return jsonify({'error': 'Faculty or admin access required'}), 403
        
        course_id = request.args.get('course_id')
        
        critical_students = BunkAllowanceService.get_critical_students(course_id)
        
        return jsonify({
            'success': True,
            'course_id': course_id,
            'total_critical': len(critical_students),
            'students': critical_students
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/course', methods=['POST'])
@require_authentication
def create_or_update_course_config():
    """Create or update course configuration.
    
    Admin only.
    
    Request body:
        {
            "course_id": "CS101",
            "course_name": "Introduction to CS",
            "total_classes": 60,
            "bunk_allowance_percentage": 25.0,
            "min_attendance_percentage": 75.0
        }
        
    Returns:
        JSON response with created/updated course config
    """
    try:
        user_info = get_current_user_info()
        
        # Only admin can configure courses
        if user_info['role'] != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        
        if not data or 'course_id' not in data:
            return jsonify({'error': 'course_id is required'}), 400
        
        course_id = data['course_id']
        course_name = data.get('course_name', course_id)
        total_classes = data.get('total_classes', 60)
        bunk_allowance = data.get('bunk_allowance_percentage', 25.0)
        min_attendance = data.get('min_attendance_percentage', 75.0)
        
        # Validate percentages
        if not (0 <= bunk_allowance <= 100):
            return jsonify({'error': 'bunk_allowance_percentage must be between 0 and 100'}), 400
        if not (0 <= min_attendance <= 100):
            return jsonify({'error': 'min_attendance_percentage must be between 0 and 100'}), 400
        
        # Get or create config
        config = db.session.execute(
            db.select(CourseConfig).filter_by(course_id=course_id)
        ).scalar_one_or_none()
        
        if config:
            # Update existing
            config.course_name = course_name
            config.total_classes = total_classes
            config.bunk_allowance_percentage = bunk_allowance
            config.min_attendance_percentage = min_attendance
            config.updated_at = db.func.now()
        else:
            # Create new
            config = CourseConfig(
                course_id=course_id,
                course_name=course_name,
                total_classes=total_classes,
                bunk_allowance_percentage=bunk_allowance,
                min_attendance_percentage=min_attendance
            )
            db.session.add(config)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Course configuration saved successfully',
            'data': config.to_dict()
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/course/<string:course_id>', methods=['GET'])
@require_authentication
def get_course_config(course_id):
    """Get course configuration.
    
    Args:
        course_id (str): Course ID
        
    Returns:
        JSON response with course config
    """
    try:
        config = db.session.execute(
            db.select(CourseConfig).filter_by(course_id=course_id)
        ).scalar_one_or_none()
        
        if not config:
            return jsonify({
                'success': False,
                'error': 'Course configuration not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': config.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/course/<string:course_id>/refresh', methods=['POST'])
@require_authentication
def refresh_course_allowances(course_id):
    """Refresh bunk allowance calculations for all students in a course.
    
    Faculty and admin only.
    
    Args:
        course_id (str): Course ID
        
    Returns:
        JSON response with refresh summary
    """
    try:
        user_info = get_current_user_info()
        
        # Only faculty and admin can refresh
        if user_info['role'] not in ['teacher', 'admin']:
            return jsonify({'error': 'Faculty or admin access required'}), 403
        
        result = BunkAllowanceService.bulk_update_course_allowances(course_id)
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bunk_allowance_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for bunk allowance API.
    
    Returns:
        JSON response with health status
    """
    return jsonify({
        'success': True,
        'service': 'Bunk Allowance API',
        'version': '1.0.0',
        'status': 'healthy'
    }), 200
