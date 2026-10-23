"""Role-Based Access Control (RBAC) utilities for SAS-88.

This module provides decorators and helper functions to enforce role-based
access control on Flask routes. Works with both Flask-Login sessions and
JWT token authentication.
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user


# Role hierarchy (higher number = more privileges)
ROLE_HIERARCHY = {
    'student': 1,
    'teacher': 2,
    'admin': 3
}


def get_user_role():
    """Get the role of the current user.

    Returns:
        str: The role of the current user ('student', 'teacher', or 'admin')
        None: If no user is authenticated
    """
    if current_user.is_authenticated:
        # Check if user has role attribute (SAS-88)
        if hasattr(current_user, 'role'):
            return current_user.role
        # Fallback to is_faculty for backward compatibility
        if hasattr(current_user, 'is_faculty'):
            return 'teacher' if current_user.is_faculty else 'student'
    return None


def has_role(user, required_role):
    """Check if a user has the required role or higher.

    Args:
        user: User object with role attribute
        required_role (str): Minimum required role ('student', 'teacher', 'admin')

    Returns:
        bool: True if user has sufficient privileges
    """
    if not user or not hasattr(user, 'role'):
        return False

    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 999)

    return user_level >= required_level


def require_role(*allowed_roles):
    """Decorator to restrict access to routes based on user role.

    Usage:
        @app.route('/admin/dashboard')
        @login_required
        @require_role('admin')
        def admin_dashboard():
            return "Admin Dashboard"

        @app.route('/attendance/mark')
        @login_required
        @require_role('teacher', 'admin')
        def mark_attendance():
            return "Mark Attendance"

    Args:
        *allowed_roles: One or more role strings that are allowed to
                        access the route

    Returns:
        Decorated function that checks user role before executing
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401

            # Get user's role
            user_role = get_user_role()

            if not user_role:
                return jsonify({
                    'error': 'No role assigned',
                    'message': 'User account does not have a role assigned'
                }), 403

            # Check if user's role is in the allowed roles
            if user_role not in allowed_roles:
                message = (
                    f'This action requires one of the following roles: '
                    f'{", ".join(allowed_roles)}'
                )
                return jsonify({
                    'error': 'Access denied',
                    'message': message,
                    'your_role': user_role,
                    'required_roles': list(allowed_roles)
                }), 403

            # User has required role, proceed with the route
            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_any_role(*allowed_roles):
    """Alias for require_role for better readability.

    Use this when you want to explicitly show that multiple roles are accepted.
    """
    return require_role(*allowed_roles)


def require_exact_role(role):
    """Decorator to restrict access to a specific role only (no hierarchy).

    Unlike require_role, this does not allow higher-privileged roles.
    For example, if you want something only students can do.

    Usage:
        @app.route('/student/profile')
        @login_required
        @require_exact_role('student')
        def student_profile():
            return "Student Profile"

    Args:
        role: The exact role required

    Returns:
        Decorated function that checks for exact role match
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401

            user_role = get_user_role()

            if user_role != role:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This action is restricted to {role} users only',
                    'your_role': user_role,
                    'required_role': role
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def is_admin(user=None):
    """Check if a user is an admin.

    Args:
        user: User object (optional, defaults to current_user)

    Returns:
        bool: True if user is an admin
    """
    target_user = user or current_user
    return has_role(target_user, 'admin')


def is_teacher_or_admin(user=None):
    """Check if a user is a teacher or admin.

    Args:
        user: User object (optional, defaults to current_user)

    Returns:
        bool: True if user is a teacher or admin
    """
    target_user = user or current_user
    return has_role(target_user, 'teacher')


def is_student(user=None):
    """Check if a user is a student.

    Args:
        user: User object (optional, defaults to current_user)

    Returns:
        bool: True if user is a student
    """
    target_user = user or current_user
    if not target_user or not hasattr(target_user, 'role'):
        return False
    return target_user.role == 'student'
