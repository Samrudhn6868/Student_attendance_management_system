"""Integration tests for SAS-94 Audit Trail API.

Tests admin-only access to audit logs and report generation.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from flask import Flask
from flask_login import LoginManager, login_user as flask_login_user
from models import db, User, Attendance
from audit_trail import AuditLog, create_audit_entry
from audit_api import audit_api
from attendance_api import attendance_api_bp


@pytest.fixture
def test_app():
    """Create test application with in-memory database."""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    app.register_blueprint(audit_api)
    app.register_blueprint(attendance_api_bp)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def app_context(test_app):
    """Provide application context."""
    with test_app.app_context():
        yield test_app


@pytest.fixture
def admin_user(app_context):
    """Create admin user for testing."""
    admin = User(
        username='admin_user',
        name='Admin User',
        is_faculty=True,
        role='admin'
    )
    admin.set_password('AdminPass123!')
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def teacher_user(app_context):
    """Create teacher user for testing."""
    teacher = User(
        username='teacher_user',
        name='Teacher User',
        is_faculty=True,
        role='teacher'
    )
    teacher.set_password('TeacherPass123!')
    db.session.add(teacher)
    db.session.commit()
    return teacher


@pytest.fixture
def student_user(app_context):
    """Create student user for testing."""
    student = User(
        username='student_user',
        name='Student User',
        is_faculty=False,
        role='student'
    )
    student.set_password('StudentPass123!')
    db.session.add(student)
    db.session.commit()
    return student


class TestAuditAPIAccess:
    """Test access control for audit API."""
    
    def test_audit_api_requires_authentication(self, client, app_context):
        """Test that audit API requires authentication."""
        response = client.get('/api/audit/logs')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Authentication required'
    
    def test_audit_api_requires_admin_role(self, test_app, client, teacher_user):
        """Test that non-admin users cannot access audit API."""
        with test_app.test_request_context():
            with client:
                # Login as teacher
                flask_login_user(teacher_user)
                
                response = client.get('/api/audit/logs')
                
                assert response.status_code == 403
                data = json.loads(response.data)
                assert data['error'] == 'Admin access required'
    
    def test_student_cannot_access_audit_api(self, test_app, client, student_user):
        """Test that students cannot access audit API."""
        with test_app.test_request_context():
            with client:
                # Login as student
                flask_login_user(student_user)
                
                response = client.get('/api/audit/logs')
                
                assert response.status_code == 403
    
    def test_admin_can_access_audit_api(self, test_app, client, admin_user):
        """Test that admin users can access audit API."""
        with test_app.test_request_context():
            with client:
                # Login as admin
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True


class TestAuditLogsAPI:
    """Test audit logs retrieval API."""
    
    def setup_audit_data(self):
        """Create test audit data."""
        for i in range(10):
            audit = AuditLog(
                user_id=1,
                username=f'user{i % 3}',
                user_role='teacher',
                action_type='CREATE' if i < 5 else 'UPDATE',
                record_type='attendance',
                record_id=i,
                student_srn=f'PES1UG21CS{i:03d}',
                course_id='CS101' if i < 7 else 'CS102',
                attendance_date='2025-01-15',
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
            db.session.add(audit)
        db.session.commit()
    
    def test_get_all_audit_logs(self, test_app, client, admin_user):
        """Test retrieving all audit logs."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert data['total_count'] == 10
                assert len(data['logs']) == 10
    
    def test_get_logs_with_pagination(self, test_app, client, admin_user):
        """Test pagination parameters."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs?limit=5&offset=0')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert len(data['logs']) == 5
                assert data['limit'] == 5
                assert data['offset'] == 0
    
    def test_filter_by_action_type(self, test_app, client, admin_user):
        """Test filtering logs by action type."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs?action_type=CREATE')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert all(log['action_type'] == 'CREATE' for log in data['logs'])
    
    def test_filter_by_student_srn(self, test_app, client, admin_user):
        """Test filtering logs by student SRN."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs?student_srn=PES1UG21CS003')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert all(log['student_srn'] == 'PES1UG21CS003' for log in data['logs'])
    
    def test_filter_by_course_id(self, test_app, client, admin_user):
        """Test filtering logs by course ID."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs?course_id=CS101')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert all(log['course_id'] == 'CS101' for log in data['logs'])
    
    def test_filter_by_date_range(self, test_app, client, admin_user):
        """Test filtering logs by date range."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                end_date = datetime.utcnow().isoformat()
                start_date = (datetime.utcnow() - timedelta(days=5)).isoformat()
                
                response = client.get(f'/api/audit/logs?start_date={start_date}&end_date={end_date}')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                # Days 0-4 inclusive gives us 5 entries
                assert data['total_count'] == 5


class TestAuditLogDetail:
    """Test individual audit log retrieval."""
    
    def test_get_specific_log(self, test_app, client, admin_user):
        """Test retrieving a specific audit log by ID."""
        # Create test audit entry directly
        with test_app.app_context():
            entry = AuditLog(
                user_id=1,
                username='test_user',
                user_role='teacher',
                action_type='CREATE',
                record_id=123,
                student_srn='PES1UG21CS001'
            )
            db.session.add(entry)
            db.session.commit()
            log_id = entry.id
        
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get(f'/api/audit/logs/{log_id}')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert data['log']['id'] == log_id
                assert data['log']['student_srn'] == 'PES1UG21CS001'
    
    def test_get_nonexistent_log(self, test_app, client, admin_user):
        """Test retrieving a non-existent audit log."""
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/logs/99999')
                
                assert response.status_code == 404
                data = json.loads(response.data)
                assert 'error' in data


class TestAuditReports:
    """Test audit report generation."""
    
    def setup_audit_data(self):
        """Create test audit data."""
        for i in range(5):
            audit = AuditLog(
                user_id=i % 2 + 1,
                username=f'user{i % 2 + 1}',
                user_role='teacher',
                action_type='CREATE' if i < 3 else 'UPDATE',
                student_srn=f'PES1UG21CS{i:03d}',
                course_id='CS101'
            )
            db.session.add(audit)
        db.session.commit()
    
    def test_generate_json_report(self, test_app, client, admin_user):
        """Test generating JSON report."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/report?format=json')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'report' in data
                assert data['report']['total_records'] == 5
    
    def test_generate_summary_report(self, test_app, client, admin_user):
        """Test generating summary report."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/report?format=summary')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'report' in data
                assert 'action_breakdown' in data['report']
                assert data['report']['action_breakdown']['CREATE'] == 3
    
    def test_generate_csv_report(self, test_app, client, admin_user):
        """Test generating CSV report."""
        self.setup_audit_data()
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/report?format=csv')
                
                assert response.status_code == 200
                assert response.content_type == 'text/csv; charset=utf-8'
                assert b'ID,Timestamp,Username' in response.data


class TestAuditStatistics:
    """Test audit statistics API."""
    
    def test_get_statistics(self, test_app, client, admin_user):
        """Test retrieving audit statistics."""
        # Create test data
        for i in range(3):
            audit = AuditLog(
                user_id=1,
                username='test_user',
                user_role='teacher',
                action_type='CREATE'
            )
            db.session.add(audit)
        db.session.commit()
        
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/stats')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'statistics' in data


class TestAuditTimeline:
    """Test audit timeline API."""
    
    def test_get_timeline(self, test_app, client, admin_user):
        """Test retrieving audit activity timeline."""
        # Create test data
        for i in range(5):
            audit = AuditLog(
                user_id=1,
                username='test_user',
                user_role='teacher',
                action_type='CREATE' if i < 3 else 'UPDATE',
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
            db.session.add(audit)
        db.session.commit()
        
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                response = client.get('/api/audit/timeline?days=7')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'timeline' in data


class TestAttendanceAuditIntegration:
    """Test integration of audit logging with attendance operations."""
    
    def test_attendance_creation_logs_audit(self, test_app, client, admin_user):
        """Test that creating attendance creates an audit entry."""
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                # Submit attendance
                response = client.post('/api/attendance/submit', json={
                    'student_srn': 'PES1UG21CS001',
                    'course_id': 'CS101',
                    'date': '2025-01-15',
                    'status': 'present',
                    'reason': 'Regular marking'
                })
                
                # Attendance creation returns 201 Created
                assert response.status_code in [200, 201]
                
                # Check audit log
                audit_response = client.get('/api/audit/logs?student_srn=PES1UG21CS001')
                assert audit_response.status_code == 200
                
                audit_data = json.loads(audit_response.data)
                assert audit_data['total_count'] > 0
                assert audit_data['logs'][0]['action_type'] == 'CREATE'
    
    def test_attendance_update_logs_audit(self, test_app, client, admin_user):
        """Test that updating attendance creates an audit entry."""
        # First create an attendance record
        attendance = Attendance(
            student_srn='PES1UG21CS002',
            course_id='CS102',
            date=datetime(2025, 1, 16).date(),
            status='absent',
            marked_by='admin_user'
        )
        db.session.add(attendance)
        db.session.commit()
        attendance_id = attendance.id
        
        with test_app.test_request_context():
            with client:
                flask_login_user(admin_user)
                
                # Update attendance
                response = client.put('/api/attendance/update', json={
                    'attendance_id': attendance_id,
                    'status': 'present',
                    'reason': 'Correcting error'
                })
                
                assert response.status_code == 200
                
                # Check audit log
                audit_response = client.get('/api/audit/logs?action_type=UPDATE')
                assert audit_response.status_code == 200
                
                audit_data = json.loads(audit_response.data)
                assert audit_data['total_count'] > 0
                update_logs = [log for log in audit_data['logs'] if log['record_id'] == attendance_id]
                assert len(update_logs) > 0
                assert update_logs[0]['reason'] == 'Correcting error'
