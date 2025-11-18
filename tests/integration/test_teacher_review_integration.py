"""Integration tests for SAS-99: Teacher Review System.

This module provides comprehensive integration tests for the teacher review
functionality including all endpoints, workflows, and edge cases.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from sqlalchemy import text

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from flask import Flask
from flask_login import LoginManager
from models import db, AttendanceCorrectionRequest, User, Attendance
from teacher_review_api import teacher_review_bp


@pytest.fixture
def test_app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprint
    app.register_blueprint(teacher_review_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Cleanup
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def test_users(test_app):
    """Create test users."""
    with test_app.app_context():
        # Create student
        student = User(username='student1', name='Test Student', role='student')
        student.set_password('pass123')
        
        # Create teacher
        teacher = User(username='teacher1', name='Test Teacher', role='teacher', is_faculty=True)
        teacher.set_password('pass123')
        
        # Create admin
        admin = User(username='admin1', name='Test Admin', role='admin', is_faculty=True)
        admin.set_password('pass123')
        
        db.session.add_all([student, teacher, admin])
        db.session.commit()
        
        return {
            'student': student.id,
            'teacher': teacher.id,
            'admin': admin.id
        }


def login_user(client, user_id):
    """Helper to login a user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True


class TestTeacherReviewEndpoints:
    """Test all teacher review API endpoints."""
    
    def test_get_pending_requests_empty(self, client, test_app, test_users):
        """Test getting pending requests when none exist."""
        login_user(client, test_users['teacher'])
        response = client.get('/teacher-review/pending-requests')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total'] == 0
        assert len(data['requests']) == 0
    
    def test_get_pending_requests_with_data(self, client, test_app, test_users):
        """Test getting pending requests with actual data."""
        with test_app.app_context():
            # Create pending request
            req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='I was present',
                status='pending',
                submitted_at=datetime.utcnow()
            )
            db.session.add(req)
            db.session.commit()
        
        login_user(client, test_users['teacher'])
        response = client.get('/teacher-review/pending-requests')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total'] == 1
        assert len(data['requests']) == 1
        assert data['requests'][0]['student_name'] == 'Test Student'
    
    def test_approve_request_success(self, client, test_app, test_users):
        """Test successfully approving a correction request."""
        with test_app.app_context():
            # Create attendance record
            attendance = Attendance(
                student_id=test_users['student'],
                date=datetime.now().date(),
                is_present=False,
                updated_at=datetime.utcnow()
            )
            db.session.add(attendance)
            
            # Create correction request
            req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Valid reason',
                status='pending',
                submitted_at=datetime.utcnow()
            )
            db.session.add(req)
            db.session.commit()
            request_id = req.id
        
        login_user(client, test_users['teacher'])
        response = client.post(
            f'/teacher-review/approve/{request_id}',
            json={'notes': 'Approved after verification'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Verify request was approved
        with test_app.app_context():
            req = db.session.get(AttendanceCorrectionRequest, request_id)
            assert req.status == 'approved'
            assert req.admin_notes == 'Approved after verification'
    
    def test_approve_nonexistent_request(self, client, test_app, test_users):
        """Test approving a request that doesn't exist."""
        login_user(client, test_users['teacher'])
        response = client.post(
            '/teacher-review/approve/99999',
            json={'notes': 'Test'}
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
    
    def test_deny_request_success(self, client, test_app, test_users):
        """Test successfully denying a correction request."""
        with test_app.app_context():
            req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Reason',
                status='pending',
                submitted_at=datetime.utcnow()
            )
            db.session.add(req)
            db.session.commit()
            request_id = req.id
        
        login_user(client, test_users['teacher'])
        response = client.post(
            f'/teacher-review/deny/{request_id}',
            json={'notes': 'Insufficient evidence'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Verify request was denied
        with test_app.app_context():
            req = db.session.get(AttendanceCorrectionRequest, request_id)
            assert req.status == 'rejected'
            assert req.admin_notes == 'Insufficient evidence'
    
    def test_deny_request_missing_notes(self, client, test_app, test_users):
        """Test that denying requires notes."""
        with test_app.app_context():
            req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Reason',
                status='pending',
                submitted_at=datetime.utcnow()
            )
            db.session.add(req)
            db.session.commit()
            request_id = req.id
        
        login_user(client, test_users['teacher'])
        response = client.post(
            f'/teacher-review/deny/{request_id}',
            json={}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_get_review_history(self, client, test_app, test_users):
        """Test getting review history."""
        with test_app.app_context():
            # Create approved request
            approved_req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Reason 1',
                status='approved',
                submitted_at=datetime.utcnow() - timedelta(days=1),
                reviewed_at=datetime.utcnow(),
                reviewed_by=test_users['teacher']
            )
            
            # Create rejected request
            rejected_req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS102',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Reason 2',
                status='rejected',
                submitted_at=datetime.utcnow() - timedelta(days=2),
                reviewed_at=datetime.utcnow(),
                reviewed_by=test_users['teacher']
            )
            
            db.session.add_all([approved_req, rejected_req])
            db.session.commit()
        
        login_user(client, test_users['teacher'])
        response = client.get('/teacher-review/history')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total'] >= 2
    
    def test_get_review_history_with_filters(self, client, test_app, test_users):
        """Test getting review history with status filter."""
        with test_app.app_context():
            # Create multiple requests with different statuses
            for status in ['approved', 'rejected', 'expired']:
                req = AttendanceCorrectionRequest(
                    student_id=test_users['student'],
                    student_name='Test Student',
                    course_id='CS101',
                    date=datetime.now().date(),
                    current_status='absent',
                    requested_status='present',
                    reason=f'Reason for {status}',
                    status=status,
                    submitted_at=datetime.utcnow() - timedelta(days=1),
                    reviewed_at=datetime.utcnow() if status != 'expired' else None,
                    reviewed_by=test_users['teacher'] if status != 'expired' else None
                )
                db.session.add(req)
            db.session.commit()
        
        login_user(client, test_users['teacher'])
        
        # Test filtering by approved
        response = client.get('/teacher-review/history?status=approved')
        assert response.status_code == 200
        data = response.get_json()
        assert all(r['status'] == 'approved' for r in data['requests'])
        
        # Test filtering by rejected
        response = client.get('/teacher-review/history?status=rejected')
        assert response.status_code == 200
        data = response.get_json()
        assert all(r['status'] == 'rejected' for r in data['requests'])
    
    def test_get_review_stats(self, client, test_app, test_users):
        """Test getting review statistics."""
        with test_app.app_context():
            # Create various requests
            statuses = ['pending', 'approved', 'rejected', 'expired']
            for status in statuses:
                req = AttendanceCorrectionRequest(
                    student_id=test_users['student'],
                    student_name='Test Student',
                    course_id='CS101',
                    date=datetime.now().date(),
                    current_status='absent',
                    requested_status='present',
                    reason=f'Reason for {status}',
                    status=status,
                    submitted_at=datetime.utcnow() - (timedelta(hours=50) if status == 'expired' else timedelta(hours=1)),
                    reviewed_at=datetime.utcnow() if status in ['approved', 'rejected'] else None,
                    reviewed_by=test_users['teacher'] if status in ['approved', 'rejected'] else None
                )
                db.session.add(req)
            
            # Add urgent request (less than 6 hours remaining)
            urgent_req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS102',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Urgent',
                status='pending',
                submitted_at=datetime.utcnow() - timedelta(hours=43)  # 5 hours left
            )
            db.session.add(urgent_req)
            db.session.commit()
        
        login_user(client, test_users['teacher'])
        response = client.get('/teacher-review/stats')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'stats' in data
        assert data['stats']['pending'] >= 2
        assert data['stats']['urgent'] >= 1
        assert data['stats']['approved'] >= 1
        assert data['stats']['rejected'] >= 1
    
    def test_auto_expire_mechanism(self, client, test_app, test_users):
        """Test that old requests are automatically expired."""
        with test_app.app_context():
            # Create old request (50 hours ago)
            old_req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=(datetime.now() - timedelta(days=3)).date(),
                current_status='absent',
                requested_status='present',
                reason='Old request',
                status='pending',
                submitted_at=datetime.utcnow() - timedelta(hours=50)
            )
            db.session.add(old_req)
            db.session.commit()
            old_req_id = old_req.id
        
        login_user(client, test_users['teacher'])
        
        # Trigger auto-expire by fetching pending requests
        response = client.get('/teacher-review/pending-requests')
        assert response.status_code == 200
        
        # Verify request was expired
        with test_app.app_context():
            req = db.session.get(AttendanceCorrectionRequest, old_req_id)
            assert req.status == 'expired'
    
    def test_expired_request_not_approvable(self, client, test_app, test_users):
        """Test that expired requests cannot be approved."""
        with test_app.app_context():
            req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Reason',
                status='expired',
                submitted_at=datetime.utcnow() - timedelta(hours=50)
            )
            db.session.add(req)
            db.session.commit()
            request_id = req.id
        
        login_user(client, test_users['teacher'])
        response = client.post(
            f'/teacher-review/approve/{request_id}',
            json={'notes': 'Trying to approve'}
        )
        
        # Should fail because request is expired (409 Conflict or 400/404)
        assert response.status_code in [400, 404, 409]


class TestTeacherReviewPermissions:
    """Test role-based access control for teacher review."""
    
    def test_student_cannot_access_pending(self, client, test_app, test_users):
        """Test that students cannot access teacher review endpoints."""
        login_user(client, test_users['student'])
        response = client.get('/teacher-review/pending-requests')
        
        # Should be forbidden or redirect
        assert response.status_code in [403, 302]
    
    def test_admin_can_access_all_endpoints(self, client, test_app, test_users):
        """Test that admins have full access."""
        with test_app.app_context():
            req = AttendanceCorrectionRequest(
                student_id=test_users['student'],
                student_name='Test Student',
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='Reason',
                status='pending',
                submitted_at=datetime.utcnow()
            )
            db.session.add(req)
            db.session.commit()
        
        login_user(client, test_users['admin'])
        
        # Admin can view pending
        response = client.get('/teacher-review/pending-requests')
        assert response.status_code == 200
        
        # Admin can view history
        response = client.get('/teacher-review/history')
        assert response.status_code == 200
        
        # Admin can view stats
        response = client.get('/teacher-review/stats')
        assert response.status_code == 200
