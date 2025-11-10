"""Integration tests for admin override attendance functionality.

These tests verify the integration between different components:
- Database operations with models
- RBAC and authentication integration
- API endpoint integration with database
"""

import pytest
import os
import sys
import json
from datetime import date, datetime
from flask import Flask
from flask_login import LoginManager

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.attendance_routes import attendance_bp
from src.models import Attendance, User, db


@pytest.fixture
def test_app():
    """Create Flask application for integration testing."""
    template_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'src', 'templates'))
    
    app = Flask(__name__, template_folder=template_path)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SECRET_KEY='test-secret-key-integration',
        WTF_CSRF_ENABLED=False
    )
    
    db.init_app(app)
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    app.register_blueprint(attendance_bp)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create test client for integration testing."""
    return test_app.test_client()


class TestDatabaseIntegration:
    """Test database integration with override functionality."""
    
    def test_attendance_model_has_override_fields(self, test_app):
        """Test that Attendance model has all required override fields."""
        with test_app.app_context():
            # Create attendance record
            attendance = Attendance(
                student_id=1,
                date=date.today(),
                is_present=False
            )
            db.session.add(attendance)
            db.session.commit()
            
            # Verify override fields exist and are accessible
            assert hasattr(attendance, 'is_overridden')
            assert hasattr(attendance, 'override_reason')
            assert hasattr(attendance, 'overridden_by')
            assert hasattr(attendance, 'override_timestamp')
            
            # Verify default values
            assert attendance.is_overridden is False
            assert attendance.override_reason is None
            assert attendance.overridden_by is None
            assert attendance.override_timestamp is None
    
    def test_override_persists_in_database(self, test_app):
        """Test that override changes are properly persisted."""
        with test_app.app_context():
            # Create and save attendance
            attendance = Attendance(
                student_id=2,
                date=date.today(),
                is_present=False
            )
            db.session.add(attendance)
            db.session.commit()
            attendance_id = attendance.id
            
            # Override the attendance
            attendance.is_present = True
            attendance.is_overridden = True
            attendance.override_reason = "Integration test override"
            attendance.overridden_by = 1
            attendance.override_timestamp = datetime.utcnow().isoformat()
            db.session.commit()
            
            # Clear session and reload from database
            db.session.expire_all()
            reloaded = db.session.get(Attendance, attendance_id)
            
            # Verify all fields persisted
            assert reloaded.is_present is True
            assert reloaded.is_overridden is True
            assert reloaded.override_reason == "Integration test override"
            assert reloaded.overridden_by == 1
            assert reloaded.override_timestamp is not None
    
    def test_query_overridden_records(self, test_app):
        """Test querying for overridden attendance records."""
        with test_app.app_context():
            # Create mix of normal and overridden records
            normal = Attendance(student_id=3, date=date.today(), is_present=True)
            overridden = Attendance(
                student_id=4,
                date=date.today(),
                is_present=False,
                is_overridden=True,
                override_reason="Test"
            )
            
            db.session.add_all([normal, overridden])
            db.session.commit()
            
            # Query for overridden records only
            overridden_records = Attendance.query.filter_by(is_overridden=True).all()
            
            assert len(overridden_records) == 1
            assert overridden_records[0].override_reason == "Test"


class TestRBACIntegration:
    """Test RBAC integration with override functionality."""
    
    def test_admin_role_check(self, test_app):
        """Test that admin role is properly checked."""
        with test_app.app_context():
            # Create users with different roles
            admin = User(user_id=10, name='Admin', is_faculty=True)
            admin.role = 'admin'
            
            teacher = User(user_id=11, name='Teacher', is_faculty=True)
            teacher.role = 'teacher'
            
            student = User(user_id=12, name='Student', is_faculty=False)
            student.role = 'student'
            
            db.session.add_all([admin, teacher, student])
            db.session.commit()
            
            # Verify roles
            assert admin.role == 'admin'
            assert teacher.role == 'teacher'
            assert student.role == 'student'
    
    def test_endpoint_requires_admin_role(self, client, test_app):
        """Test that override endpoint requires admin role."""
        with test_app.app_context():
            # Create student
            student = User(user_id=20, name='Student', is_faculty=False)
            student.role = 'student'
            db.session.add(student)
            
            # Create attendance
            attendance = Attendance(student_id=20, date=date.today(), is_present=False)
            db.session.add(attendance)
            db.session.commit()
            attendance_id = attendance.id
            
            # Try to override as non-admin (should fail)
            with client.session_transaction() as sess:
                sess['_user_id'] = str(student.user_id)
            
            response = client.put(
                '/attendance/override',
                data=json.dumps({
                    'attendance_id': attendance_id,
                    'new_status': 'present',
                    'reason': 'Unauthorized attempt'
                }),
                content_type='application/json'
            )
            
            # Should be unauthorized or forbidden
            assert response.status_code in [401, 403]


class TestEndToEndOverride:
    """End-to-end integration tests for override flow."""
    
    def test_complete_override_workflow(self, test_app):
        """Test complete workflow from attendance creation to override."""
        with test_app.app_context():
            # Step 1: Create admin user
            admin = User(user_id=30, name='Admin', is_faculty=True)
            admin.role = 'admin'
            db.session.add(admin)
            
            # Step 2: Create student
            student = User(user_id=31, name='Student', is_faculty=False)
            student.role = 'student'
            db.session.add(student)
            
            # Step 3: Create attendance (marked absent)
            attendance = Attendance(
                student_id=student.user_id,
                date=date.today(),
                is_present=False
            )
            db.session.add(attendance)
            db.session.commit()
            
            attendance_id = attendance.id
            
            # Step 4: Verify initial state
            assert attendance.is_present is False
            assert attendance.is_overridden is False
            
            # Step 5: Perform override (simulate admin action)
            attendance.is_present = True
            attendance.is_overridden = True
            attendance.override_reason = "Student provided medical certificate"
            attendance.overridden_by = admin.user_id
            attendance.override_timestamp = datetime.utcnow().isoformat()
            db.session.commit()
            
            # Step 6: Verify final state
            db.session.expire_all()
            final_attendance = db.session.get(Attendance, attendance_id)
            
            assert final_attendance.is_present is True
            assert final_attendance.is_overridden is True
            assert final_attendance.override_reason == "Student provided medical certificate"
            assert final_attendance.overridden_by == admin.user_id
            assert final_attendance.override_timestamp is not None
    
    def test_override_updates_attendance_percentage(self, test_app):
        """Test that overriding affects attendance percentage calculation."""
        with test_app.app_context():
            student_id = 40
            
            # Create 5 attendance records: 2 present, 3 absent
            for i in range(5):
                attendance = Attendance(
                    student_id=student_id,
                    date=date.today(),
                    is_present=(i < 2)
                )
                db.session.add(attendance)
            db.session.commit()
            
            # Calculate initial percentage
            records = Attendance.query.filter_by(student_id=student_id).all()
            initial_present = sum(1 for r in records if r.is_present)
            initial_percentage = (initial_present / len(records)) * 100
            
            assert initial_percentage == 40.0  # 2 out of 5
            
            # Override one absent to present
            absent_record = Attendance.query.filter_by(
                student_id=student_id,
                is_present=False
            ).first()
            
            absent_record.is_present = True
            absent_record.is_overridden = True
            absent_record.override_reason = "Override for percentage test"
            db.session.commit()
            
            # Recalculate percentage
            updated_records = Attendance.query.filter_by(student_id=student_id).all()
            updated_present = sum(1 for r in updated_records if r.is_present)
            updated_percentage = (updated_present / len(updated_records)) * 100
            
            assert updated_percentage == 60.0  # 3 out of 5


class TestConcurrentOverrides:
    """Test handling of concurrent override operations."""
    
    def test_multiple_admins_can_override(self, test_app):
        """Test that different admins can override records."""
        with test_app.app_context():
            # Create two admin users
            admin1 = User(user_id=50, name='Admin One', is_faculty=True)
            admin1.role = 'admin'
            
            admin2 = User(user_id=51, name='Admin Two', is_faculty=True)
            admin2.role = 'admin'
            
            db.session.add_all([admin1, admin2])
            
            # Create two attendance records
            att1 = Attendance(student_id=100, date=date.today(), is_present=False)
            att2 = Attendance(student_id=101, date=date.today(), is_present=False)
            
            db.session.add_all([att1, att2])
            db.session.commit()
            
            # Admin 1 overrides first record
            att1.is_present = True
            att1.is_overridden = True
            att1.override_reason = "Overridden by Admin 1"
            att1.overridden_by = admin1.user_id
            att1.override_timestamp = datetime.utcnow().isoformat()
            
            # Admin 2 overrides second record
            att2.is_present = True
            att2.is_overridden = True
            att2.override_reason = "Overridden by Admin 2"
            att2.overridden_by = admin2.user_id
            att2.override_timestamp = datetime.utcnow().isoformat()
            
            db.session.commit()
            
            # Verify both overrides
            assert att1.overridden_by == admin1.user_id
            assert att2.overridden_by == admin2.user_id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
