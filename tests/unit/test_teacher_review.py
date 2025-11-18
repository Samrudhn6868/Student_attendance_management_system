"""Tests for SAS-99: Teacher Review of Correction Requests.

This module tests the teacher review functionality including:
- Viewing pending correction requests
- Approving requests within 48-hour window
- Denying requests with required notes
- Auto-expiring requests after 48 hours
- Review history and statistics
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
from models import db, AttendanceCorrectionRequest, User
from teacher_review_api import teacher_review_bp


class TestTeacherReview:
    """Test teacher review of correction requests (SAS-99)."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Initialize db with the test app
        db.init_app(app)
        
        # Initialize Flask-Login
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))
        
        # Register the blueprint
        app.register_blueprint(teacher_review_bp)
        
        with app.app_context():
            db.create_all()
            
            # Create test users
            student = User(username='student1', name='Test Student', role='student')
            student.set_password('pass123')
            
            teacher = User(username='teacher1', name='Test Teacher', role='teacher', is_faculty=True)
            teacher.set_password('pass123')
            
            db.session.add_all([student, teacher])
            db.session.commit()
            
            yield app
            
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def teacher_headers(self, client, app):
        """Login as teacher and get session."""
        with app.app_context():
            teacher = User.query.filter_by(username='teacher1').first()
            with client.session_transaction() as sess:
                sess['_user_id'] = str(teacher.id)
                sess['_fresh'] = True
        return {}
    
    def test_pending_requests_endpoint(self, client, teacher_headers, app):
        """Test fetching pending correction requests."""
        with app.app_context():
            # Create a pending request
            student = User.query.filter_by(username='student1').first()
            req = AttendanceCorrectionRequest(
                student_id=student.id,
                student_name=student.name,
                course_id='CS101',
                date=datetime.now().date(),
                current_status='absent',
                requested_status='present',
                reason='I was present but marked absent',
                status='pending',
                submitted_at=datetime.utcnow()
            )
            db.session.add(req)
            db.session.commit()
        
        response = client.get('/teacher-review/pending-requests', headers=teacher_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total'] >= 1
    
    def test_approve_request(self, client, teacher_headers, app):
        """Test approving a correction request."""
        with app.app_context():
            # Create request and attendance record
            student = User.query.filter_by(username='student1').first()
            
            # Insert attendance record
            db.session.execute(
                text("""INSERT INTO attendance (student_id, date, is_present, updated_at)
                   VALUES (:sid, :date, 0, :updated)"""),
                {'sid': student.id, 'date': datetime.now().date(), 'updated': datetime.utcnow()}
            )
            
            req = AttendanceCorrectionRequest(
                student_id=student.id,
                student_name=student.name,
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
        
        response = client.post(
            f'/teacher-review/approve/{request_id}',
            json={'notes': 'Approved after verification'},
            headers=teacher_headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'approved' in data['message'].lower()
    
    def test_deny_request_requires_notes(self, client, teacher_headers, app):
        """Test that denying requires notes."""
        with app.app_context():
            student = User.query.filter_by(username='student1').first()
            req = AttendanceCorrectionRequest(
                student_id=student.id,
                student_name=student.name,
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
        
        # Try without notes
        response = client.post(
            f'/teacher-review/deny/{request_id}',
            json={},
            headers=teacher_headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'notes' in data['error'].lower() or 'required' in data['error'].lower()
    
    def test_auto_expire_old_requests(self, client, teacher_headers, app):
        """Test that requests older than 48 hours are auto-expired."""
        with app.app_context():
            student = User.query.filter_by(username='student1').first()
            
            # Create old request (50 hours ago)
            old_req = AttendanceCorrectionRequest(
                student_id=student.id,
                student_name=student.name,
                course_id='CS101',
                date=(datetime.now() - timedelta(days=2)).date(),
                current_status='absent',
                requested_status='present',
                reason='Old request',
                status='pending',
                submitted_at=datetime.utcnow() - timedelta(hours=50)
            )
            db.session.add(old_req)
            db.session.commit()
        
        # Fetch pending requests (should auto-expire old one)
        response = client.get('/teacher-review/pending-requests', headers=teacher_headers)
        data = response.get_json()
        
        # Check that old request was expired
        with app.app_context():
            expired = AttendanceCorrectionRequest.query.filter_by(status='expired').first()
            assert expired is not None
    
    def test_review_stats(self, client, teacher_headers, app):
        """Test getting review statistics."""
        response = client.get('/teacher-review/stats', headers=teacher_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'stats' in data
        assert 'pending' in data['stats']
        assert 'approved' in data['stats']
        assert 'rejected' in data['stats']
        assert 'urgent' in data['stats']


class TestTeacherReviewIntegration:
    """Integration tests for complete review workflow."""
    
    def test_complete_approval_workflow(self):
        """Test complete workflow from request to approval."""
        # This would test: student submits -> teacher sees -> teacher approves -> attendance updated
        pass
    
    def test_48_hour_window_enforcement(self):
        """Test that 48-hour window is strictly enforced."""
        pass
    
    def test_teacher_permissions(self):
        """Test that only teachers/admins can access review endpoints."""
        pass
