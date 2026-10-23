"""Unit tests for RBAC (Role-Based Access Control) module."""

import pytest
from unittest.mock import Mock, patch
from flask import Flask, jsonify
from flask_login import LoginManager, login_user, logout_user
from src.rbac import (
    ROLE_HIERARCHY,
    get_user_role,
    has_role,
    require_role,
    require_any_role,
    require_exact_role,
    is_admin,
    is_teacher_or_admin,
    is_student
)


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test_secret_key'
    app.config['TESTING'] = True
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    # Mock user loader
    @login_manager.user_loader
    def load_user(user_id):
        return None
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class MockUser:
    """Mock user object for testing."""
    
    def __init__(self, role=None, is_faculty=None, authenticated=True):
        self.role = role
        self.is_faculty = is_faculty
        self.is_authenticated = authenticated
        self.id = 1


class TestRoleHierarchy:
    """Test role hierarchy constants."""
    
    def test_role_hierarchy_defined(self):
        """Test role hierarchy dictionary exists."""
        assert ROLE_HIERARCHY is not None
        assert isinstance(ROLE_HIERARCHY, dict)
    
    def test_student_role_lowest(self):
        """Test student has lowest privilege level."""
        assert ROLE_HIERARCHY['student'] == 1
    
    def test_teacher_role_middle(self):
        """Test teacher has middle privilege level."""
        assert ROLE_HIERARCHY['teacher'] == 2
    
    def test_admin_role_highest(self):
        """Test admin has highest privilege level."""
        assert ROLE_HIERARCHY['admin'] == 3
    
    def test_hierarchy_order(self):
        """Test role hierarchy is correctly ordered."""
        assert ROLE_HIERARCHY['student'] < ROLE_HIERARCHY['teacher']
        assert ROLE_HIERARCHY['teacher'] < ROLE_HIERARCHY['admin']


class TestGetUserRole:
    """Test get_user_role function."""
    
    @patch('src.rbac.current_user')
    def test_authenticated_user_with_role(self, mock_current_user):
        """Test getting role from authenticated user."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'student'
        
        role = get_user_role()
        assert role == 'student'
    
    @patch('src.rbac.current_user')
    def test_authenticated_user_teacher_role(self, mock_current_user):
        """Test getting teacher role."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'teacher'
        
        role = get_user_role()
        assert role == 'teacher'
    
    @patch('src.rbac.current_user')
    def test_authenticated_user_admin_role(self, mock_current_user):
        """Test getting admin role."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'admin'
        
        role = get_user_role()
        assert role == 'admin'
    
    @patch('src.rbac.current_user')
    def test_unauthenticated_user(self, mock_current_user):
        """Test unauthenticated user returns None."""
        mock_current_user.is_authenticated = False
        
        role = get_user_role()
        assert role is None
    
    @patch('src.rbac.current_user')
    def test_fallback_to_is_faculty_true(self, mock_current_user):
        """Test fallback to is_faculty attribute (teacher)."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = None
        mock_current_user.is_faculty = True
        
        # Mock hasattr to return False for 'role' but True for 'is_faculty'
        with patch('builtins.hasattr') as mock_hasattr:
            def hasattr_side_effect(obj, attr):
                if attr == 'role':
                    return False
                elif attr == 'is_faculty':
                    return True
                return False
            mock_hasattr.side_effect = hasattr_side_effect
            
            role = get_user_role()
            assert role == 'teacher'
    
    @patch('src.rbac.current_user')
    def test_fallback_to_is_faculty_false(self, mock_current_user):
        """Test fallback to is_faculty attribute (student)."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = None
        mock_current_user.is_faculty = False
        
        with patch('builtins.hasattr') as mock_hasattr:
            def hasattr_side_effect(obj, attr):
                if attr == 'role':
                    return False
                elif attr == 'is_faculty':
                    return True
                return False
            mock_hasattr.side_effect = hasattr_side_effect
            
            role = get_user_role()
            assert role == 'student'


class TestHasRole:
    """Test has_role function."""
    
    def test_user_has_exact_role(self):
        """Test user has exact required role."""
        user = MockUser(role='teacher')
        assert has_role(user, 'teacher') is True
    
    def test_user_has_higher_role(self):
        """Test user has higher privilege role."""
        user = MockUser(role='admin')
        assert has_role(user, 'teacher') is True
        assert has_role(user, 'student') is True
    
    def test_user_has_lower_role(self):
        """Test user has lower privilege role."""
        user = MockUser(role='student')
        assert has_role(user, 'teacher') is False
        assert has_role(user, 'admin') is False
    
    def test_none_user(self):
        """Test None user returns False."""
        assert has_role(None, 'student') is False
    
    def test_user_without_role_attribute(self):
        """Test user without role attribute returns False."""
        user = Mock()
        del user.role
        assert has_role(user, 'student') is False
    
    def test_invalid_required_role(self):
        """Test invalid required role."""
        user = MockUser(role='student')
        assert has_role(user, 'invalid_role') is False


class TestRequireRoleDecorator:
    """Test require_role decorator."""
    
    @patch('src.rbac.current_user')
    def test_authenticated_user_with_correct_role(self, mock_current_user, app):
        """Test authenticated user with correct role can access route."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'teacher'
        
        @app.route('/test')
        @require_role('teacher')
        def test_route():
            return jsonify({'message': 'success'})
        
        with app.test_client() as client:
            with app.test_request_context():
                response = test_route()
                assert response.json['message'] == 'success'
    
    @patch('src.rbac.current_user')
    def test_unauthenticated_user(self, mock_current_user, app):
        """Test unauthenticated user gets 401."""
        mock_current_user.is_authenticated = False
        
        @app.route('/test')
        @require_role('teacher')
        def test_route():
            return jsonify({'message': 'success'})
        
        with app.test_client() as client:
            with app.test_request_context():
                response = test_route()
                assert response[1] == 401
    
    @patch('src.rbac.current_user')
    def test_user_with_wrong_role(self, mock_current_user, app):
        """Test user with wrong role gets 403."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'student'
        
        @app.route('/test')
        @require_role('teacher')
        def test_route():
            return jsonify({'message': 'success'})
        
        with app.test_request_context():
            response = test_route()
            assert response[1] == 403
    
    @patch('src.rbac.current_user')
    def test_user_with_no_role_assigned(self, mock_current_user, app):
        """Test user with no role gets 403."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = None
        
        with patch('src.rbac.get_user_role', return_value=None):
            @app.route('/test')
            @require_role('teacher')
            def test_route():
                return jsonify({'message': 'success'})
            
            with app.test_request_context():
                response = test_route()
                assert response[1] == 403
    
    @patch('src.rbac.current_user')
    def test_multiple_allowed_roles(self, mock_current_user, app):
        """Test decorator with multiple allowed roles."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'admin'
        
        @app.route('/test')
        @require_role('teacher', 'admin')
        def test_route():
            return jsonify({'message': 'success'})
        
        with app.test_request_context():
            response = test_route()
            assert response.json['message'] == 'success'


class TestRequireAnyRole:
    """Test require_any_role alias."""
    
    @patch('src.rbac.current_user')
    def test_works_like_require_role(self, mock_current_user, app):
        """Test require_any_role works like require_role."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'admin'
        
        @app.route('/test')
        @require_any_role('teacher', 'admin')
        def test_route():
            return jsonify({'message': 'success'})
        
        with app.test_request_context():
            response = test_route()
            assert response.json['message'] == 'success'


class TestRequireExactRole:
    """Test require_exact_role decorator."""
    
    @patch('src.rbac.current_user')
    def test_exact_role_match(self, mock_current_user, app):
        """Test user with exact role can access."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'student'
        
        with patch('src.rbac.get_user_role', return_value='student'):
            @app.route('/test')
            @require_exact_role('student')
            def test_route():
                return jsonify({'message': 'success'})
            
            with app.test_request_context():
                response = test_route()
                assert response.json['message'] == 'success'
    
    @patch('src.rbac.current_user')
    def test_higher_role_denied(self, mock_current_user, app):
        """Test user with higher role is denied (no hierarchy)."""
        mock_current_user.is_authenticated = True
        mock_current_user.role = 'admin'
        
        with patch('src.rbac.get_user_role', return_value='admin'):
            @app.route('/test')
            @require_exact_role('student')
            def test_route():
                return jsonify({'message': 'success'})
            
            with app.test_request_context():
                response = test_route()
                assert response[1] == 403
    
    @patch('src.rbac.current_user')
    def test_unauthenticated_user(self, mock_current_user, app):
        """Test unauthenticated user gets 401."""
        mock_current_user.is_authenticated = False
        
        @app.route('/test')
        @require_exact_role('student')
        def test_route():
            return jsonify({'message': 'success'})
        
        with app.test_request_context():
            response = test_route()
            assert response[1] == 401


class TestIsAdmin:
    """Test is_admin helper function."""
    
    def test_admin_user(self):
        """Test admin user returns True."""
        user = MockUser(role='admin')
        assert is_admin(user) is True
    
    def test_teacher_user(self):
        """Test teacher user returns False."""
        user = MockUser(role='teacher')
        assert is_admin(user) is False
    
    def test_student_user(self):
        """Test student user returns False."""
        user = MockUser(role='student')
        assert is_admin(user) is False
    
    @patch('src.rbac.current_user')
    def test_current_user_default(self, mock_current_user):
        """Test uses current_user by default."""
        mock_current_user.role = 'admin'
        assert is_admin() is True


class TestIsTeacherOrAdmin:
    """Test is_teacher_or_admin helper function."""
    
    def test_admin_user(self):
        """Test admin user returns True."""
        user = MockUser(role='admin')
        assert is_teacher_or_admin(user) is True
    
    def test_teacher_user(self):
        """Test teacher user returns True."""
        user = MockUser(role='teacher')
        assert is_teacher_or_admin(user) is True
    
    def test_student_user(self):
        """Test student user returns False."""
        user = MockUser(role='student')
        assert is_teacher_or_admin(user) is False
    
    @patch('src.rbac.current_user')
    def test_current_user_default(self, mock_current_user):
        """Test uses current_user by default."""
        mock_current_user.role = 'teacher'
        assert is_teacher_or_admin() is True


class TestIsStudent:
    """Test is_student helper function."""
    
    def test_student_user(self):
        """Test student user returns True."""
        user = MockUser(role='student')
        assert is_student(user) is True
    
    def test_teacher_user(self):
        """Test teacher user returns False."""
        user = MockUser(role='teacher')
        assert is_student(user) is False
    
    def test_admin_user(self):
        """Test admin user returns False."""
        user = MockUser(role='admin')
        assert is_student(user) is False
    
    def test_none_user(self):
        """Test None user returns False."""
        assert is_student(None) is False
    
    def test_user_without_role(self):
        """Test user without role returns False."""
        user = Mock()
        del user.role
        assert is_student(user) is False
    
    @patch('src.rbac.current_user')
    def test_current_user_default(self, mock_current_user):
        """Test uses current_user by default."""
        mock_current_user.role = 'student'
        assert is_student() is True
