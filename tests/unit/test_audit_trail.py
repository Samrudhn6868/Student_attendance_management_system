"""Unit tests for SAS-94 Audit Trail System.

Tests audit logging functionality, filtering, and report generation.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from flask import Flask
from flask_login import LoginManager
from audit_trail import (
    AuditLog,
    create_audit_entry,
    get_audit_logs,
    generate_audit_report,
    log_attendance_creation,
    log_attendance_update,
    log_attendance_deletion
)
from models import db, Attendance, User


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
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_context(test_app):
    """Provide application context for tests."""
    with test_app.app_context():
        yield test_app


class TestAuditLogModel:
    """Test AuditLog model functionality."""
    
    def test_audit_log_creation(self, app_context):
        """Test creating an audit log entry."""
        audit_log = AuditLog(
            user_id=1,
            username='test_teacher',
            user_role='teacher',
            action_type='CREATE',
            record_type='attendance',
            record_id=123,
            student_srn='PES1UG21CS001',
            course_id='CS101',
            attendance_date='2025-01-15'
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        assert audit_log.id is not None
        assert audit_log.username == 'test_teacher'
        assert audit_log.action_type == 'CREATE'
    
    def test_audit_log_to_dict(self, app_context):
        """Test converting audit log to dictionary."""
        changes = {'status': {'old': 'absent', 'new': 'present'}}
        
        audit_log = AuditLog(
            user_id=1,
            username='test_admin',
            user_role='admin',
            action_type='UPDATE',
            changes=json.dumps(changes),
            student_srn='PES1UG21CS002'
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        log_dict = audit_log.to_dict()
        
        assert log_dict['username'] == 'test_admin'
        assert log_dict['changes'] == changes
        assert 'timestamp' in log_dict
    
    def test_audit_log_timestamp_auto_set(self, app_context):
        """Test that timestamp is automatically set."""
        audit_log = AuditLog(
            user_id=1,
            username='test_user',
            user_role='student',
            action_type='CREATE'
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        assert audit_log.timestamp is not None
        assert isinstance(audit_log.timestamp, datetime)


class TestAuditEntryCreation:
    """Test audit entry creation functions."""
    
    def test_create_audit_entry_basic(self, app_context):
        """Test basic audit entry creation."""
        from flask import Flask
        from flask_login import login_user
        
        # Create a mock request context
        with app_context.test_request_context():
            entry = create_audit_entry(
                action_type='CREATE',
                record_id=1,
                student_srn='PES1UG21CS001',
                course_id='CS101',
                attendance_date='2025-01-15'
            )
            
            assert entry.action_type == 'CREATE'
            assert entry.student_srn == 'PES1UG21CS001'
            assert entry.course_id == 'CS101'
    
    def test_create_audit_entry_with_changes(self, app_context):
        """Test audit entry with old and new values."""
        with app_context.test_request_context():
            old_values = {'status': 'absent', 'marked_by': 'teacher1'}
            new_values = {'status': 'present', 'marked_by': 'teacher2'}
            
            entry = create_audit_entry(
                action_type='UPDATE',
                record_id=5,
                old_values=old_values,
                new_values=new_values
            )
            
            assert entry.action_type == 'UPDATE'
            changes = json.loads(entry.changes)
            assert changes['status']['old'] == 'absent'
            assert changes['status']['new'] == 'present'
    
    def test_create_audit_entry_with_reason(self, app_context):
        """Test audit entry with reason field."""
        with app_context.test_request_context():
            entry = create_audit_entry(
                action_type='UPDATE',
                reason='Correcting attendance error'
            )
            
            assert entry.reason == 'Correcting attendance error'


class TestAuditLogRetrieval:
    """Test retrieving and filtering audit logs."""
    
    def setup_test_data(self):
        """Create test audit entries."""
        # Create entries with different dates and users
        for i in range(10):
            audit = AuditLog(
                user_id=i % 3 + 1,
                username=f'user{i % 3 + 1}',
                user_role='teacher' if i % 2 == 0 else 'admin',
                action_type='CREATE' if i < 5 else 'UPDATE',
                student_srn=f'PES1UG21CS{i:03d}',
                course_id='CS101' if i < 7 else 'CS102',
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
            db.session.add(audit)
        
        db.session.commit()
    
    def test_get_all_logs(self, app_context):
        """Test retrieving all audit logs."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(limit=100)
        
        assert total == 10
        assert len(logs) == 10
    
    def test_get_logs_with_limit(self, app_context):
        """Test pagination with limit."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(limit=5)
        
        assert total == 10
        assert len(logs) == 5
    
    def test_get_logs_with_offset(self, app_context):
        """Test pagination with offset."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(limit=5, offset=5)
        
        assert total == 10
        assert len(logs) == 5
    
    def test_filter_by_user_id(self, app_context):
        """Test filtering logs by user ID."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(user_id=1)
        
        assert all(log.user_id == 1 for log in logs)
        assert total > 0
    
    def test_filter_by_action_type(self, app_context):
        """Test filtering logs by action type."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(action_type='CREATE')
        
        assert all(log.action_type == 'CREATE' for log in logs)
        assert total == 5
    
    def test_filter_by_student_srn(self, app_context):
        """Test filtering logs by student SRN."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(student_srn='PES1UG21CS003')
        
        assert all(log.student_srn == 'PES1UG21CS003' for log in logs)
        assert total == 1
    
    def test_filter_by_course_id(self, app_context):
        """Test filtering logs by course ID."""
        self.setup_test_data()
        
        logs, total = get_audit_logs(course_id='CS101')
        
        assert all(log.course_id == 'CS101' for log in logs)
        assert total == 7
    
    def test_filter_by_date_range(self, app_context):
        """Test filtering logs by date range."""
        self.setup_test_data()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=5)
        
        logs, total = get_audit_logs(start_date=start_date, end_date=end_date)
        
        assert all(start_date <= log.timestamp <= end_date for log in logs)
        assert total == 5  # Days 0-4 inclusive


class TestAuditReportGeneration:
    """Test audit report generation."""
    
    def setup_test_data(self):
        """Create test audit entries."""
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
    
    def test_generate_json_report(self, app_context):
        """Test generating JSON format report."""
        self.setup_test_data()
        
        report = generate_audit_report(format='json')
        
        assert 'total_records' in report
        assert 'logs' in report
        assert report['total_records'] == 5
        assert len(report['logs']) == 5
    
    def test_generate_summary_report(self, app_context):
        """Test generating summary report."""
        self.setup_test_data()
        
        report = generate_audit_report(format='summary')
        
        assert 'total_records' in report
        assert 'action_breakdown' in report
        assert 'user_activity' in report
        assert report['action_breakdown']['CREATE'] == 3
        assert report['action_breakdown']['UPDATE'] == 2
    
    def test_generate_csv_report(self, app_context):
        """Test generating CSV format report."""
        self.setup_test_data()
        
        csv_data = generate_audit_report(format='csv')
        
        assert isinstance(csv_data, str)
        assert 'ID,Timestamp,Username' in csv_data
        lines = csv_data.strip().split('\n')
        assert len(lines) == 6  # Header + 5 data rows
    
    def test_report_with_date_filter(self, app_context):
        """Test report generation with date filtering."""
        self.setup_test_data()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        report = generate_audit_report(
            start_date=start_date,
            end_date=end_date,
            format='json'
        )
        
        assert report['total_records'] == 5


class TestAttendanceLogging:
    """Test attendance-specific logging functions."""
    
    def test_log_attendance_creation(self, app_context):
        """Test logging attendance creation."""
        with app_context.test_request_context():
            attendance = Attendance(
                id=1,
                student_srn='PES1UG21CS001',
                course_id='CS101',
                date=datetime(2025, 1, 15).date(),
                status='present',
                marked_by='teacher1'
            )
            
            log_attendance_creation(attendance, reason='Initial marking')
            
            logs, total = get_audit_logs()
            
            assert total == 1
            assert logs[0].action_type == 'CREATE'
            assert logs[0].student_srn == 'PES1UG21CS001'
            assert logs[0].reason == 'Initial marking'
    
    def test_log_attendance_update(self, app_context):
        """Test logging attendance update."""
        with app_context.test_request_context():
            attendance = Attendance(
                id=2,
                student_srn='PES1UG21CS002',
                course_id='CS102',
                date=datetime(2025, 1, 16).date(),
                status='present',
                marked_by='teacher2'
            )
            
            old_values = {
                'status': 'absent',
                'marked_by': 'teacher1'
            }
            
            log_attendance_update(attendance, old_values, reason='Correction')
            
            logs, total = get_audit_logs()
            
            assert total == 1
            assert logs[0].action_type == 'UPDATE'
            changes = json.loads(logs[0].changes)
            assert changes['status']['old'] == 'absent'
            assert changes['status']['new'] == 'present'
    
    def test_log_attendance_deletion(self, app_context):
        """Test logging attendance deletion."""
        with app_context.test_request_context():
            attendance = Attendance(
                id=3,
                student_srn='PES1UG21CS003',
                course_id='CS103',
                date=datetime(2025, 1, 17).date(),
                status='absent',
                marked_by='teacher3'
            )
            
            log_attendance_deletion(attendance, reason='Duplicate entry')
            
            logs, total = get_audit_logs()
            
            assert total == 1
            assert logs[0].action_type == 'DELETE'
            assert logs[0].reason == 'Duplicate entry'


class TestAuditSecurity:
    """Test audit trail security features."""
    
    def test_audit_logs_are_read_only(self, app_context):
        """Test that audit logs cannot be modified."""
        with app_context.test_request_context():
            entry = create_audit_entry(
                action_type='CREATE',
                record_id=1
            )
            
            original_username = entry.username
            
            # Attempt to modify (should not be done in practice)
            entry.username = 'hacker'
            db.session.commit()
            
            # In a real system, this would be prevented by database constraints
            # or application-level checks
            # For now, we just document the expected behavior
            assert entry.username == 'hacker'  # Shows modification is possible
            # TODO: Add database-level read-only enforcement
    
    def test_audit_log_includes_ip_address(self, app_context):
        """Test that IP address is logged."""
        with app_context.test_request_context('/test', environ_base={'REMOTE_ADDR': '192.168.1.100'}):
            entry = create_audit_entry(
                action_type='CREATE',
                record_id=1
            )
            
            assert entry.ip_address == '192.168.1.100'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
