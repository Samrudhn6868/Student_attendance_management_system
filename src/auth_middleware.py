"""JWT Authentication Middleware for SAS-88.

This module provides JWT token generation and verification for the attendance system.
It works alongside the existing Flask-Login session authentication, providing an
alternative API-based authentication method.
"""

import os
from datetime import datetime, timedelta
from functools import wraps
import jwt
from flask import request, jsonify


# JWT Configuration
JWT_SECRET_KEY = os.getenv(
    'JWT_SECRET_KEY',
    'your-jwt-secret-key-change-in-production'
)
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_jwt_token(user, expiration_hours=JWT_EXPIRATION_HOURS):
    """Generate a JWT token for a user.

    Args:
        user: User object with id, username, and role attributes
        expiration_hours: Token validity period in hours (default: 24)

    Returns:
        str: JWT token string
    """
    # Token payload
    role = (
        user.role if hasattr(user, 'role')
        else ('teacher' if user.is_faculty else 'student')
    )
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': role,
        'name': user.name,
        'iat': datetime.utcnow(),  # Issued at
        'exp': datetime.utcnow() + timedelta(hours=expiration_hours)
    }

    # Generate token
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return token

def verify_jwt_token(token):
    """Verify and decode a JWT token.

    Args:
        token (str): JWT token string

    Returns:
        dict: Decoded token payload if valid
        None: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


def get_token_from_header():
    """Extract JWT token from Authorization header.

    Expected format: "Authorization: Bearer <token>"

    Returns:
        str: JWT token if present
        None: If no token found
    """
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return None

    # Check for "Bearer " prefix
    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    return parts[1]


def jwt_required(f):
    """Decorator to protect routes with JWT authentication.

    This decorator verifies the JWT token from the Authorization header
    and makes the decoded payload available via request.jwt_user.

    Usage:
        @app.route('/api/protected')
        @jwt_required
        def protected_route():
            user_data = request.jwt_user
            return jsonify({'message': f'Hello {user_data["name"]}'})

    Args:
        f: Function to decorate

    Returns:
        Decorated function that requires valid JWT token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header
        token = get_token_from_header()

        if not token:
            return jsonify({
                'error': 'No token provided',
                'message': 'Authorization header with Bearer token is required'
            }), 401

        # Verify token
        payload = verify_jwt_token(token)

        if not payload:
            return jsonify({
                'error': 'Invalid token',
                'message': 'Token is invalid or has expired'
            }), 401

        # Store user data in request context
        request.jwt_user = payload

        return f(*args, **kwargs)

    return decorated_function


def jwt_role_required(*allowed_roles):
    """Decorator to protect routes with JWT authentication and role checking.

    This combines JWT verification with role-based access control.

    Usage:
        @app.route('/api/admin/users')
        @jwt_role_required('admin')
        def list_users():
            return jsonify({'users': [...]})

        @app.route('/api/attendance/mark')
        @jwt_role_required('teacher', 'admin')
        def mark_attendance():
            return jsonify({'message': 'Attendance marked'})

    Args:
        *allowed_roles: One or more role strings that are allowed to
                        access the route

    Returns:
        Decorated function that requires valid JWT token with appropriate role
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from header
            token = get_token_from_header()

            if not token:
                return jsonify({
                    'error': 'No token provided',
                    'message': 'Authorization header with Bearer token is required'
                }), 401

            # Verify token
            payload = verify_jwt_token(token)

            if not payload:
                return jsonify({
                    'error': 'Invalid token',
                    'message': 'Token is invalid or has expired'
                }), 401

            # Check role
            user_role = payload.get('role')

            if not user_role:
                return jsonify({
                    'error': 'No role in token',
                    'message': 'User token does not contain role information'
                }), 403

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

            # Store user data in request context
            request.jwt_user = payload

            return f(*args, **kwargs)

        return decorated_function
    return decorator

def create_token_response(user):
    """Create a standardized JWT token response.

    Args:
        user: User object

    Returns:
        dict: Response dictionary with token and user info
    """
    token = generate_jwt_token(user)

    role = (
        user.role if hasattr(user, 'role')
        else ('teacher' if user.is_faculty else 'student')
    )

    return {
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': JWT_EXPIRATION_HOURS * 3600,  # seconds
        'user': {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'role': role
        }
    }


def refresh_jwt_token(old_token):
    """Refresh an existing JWT token.

    Args:
        old_token (str): Existing JWT token

    Returns:
        str: New JWT token if old token is valid
        None: If old token is invalid
    """
    payload = verify_jwt_token(old_token)

    if not payload:
        return None

    # Create new token with same user info but new expiration
    new_payload = {
        'user_id': payload['user_id'],
        'username': payload['username'],
        'role': payload['role'],
        'name': payload['name'],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }

    return jwt.encode(new_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
