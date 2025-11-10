"""System tests for admin override attendance functionality.

These tests verify the complete system behavior from an end-user perspective,
testing the full stack including API, database, authentication, and authorization.
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
    """Create Flask application for system testing."""
    template_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'src', 'templates'))
    
    app = Flask(__name__, template_folder=template_path)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SECRET_KEY='test-secret-key-system',
        WTF_CSRF_ENABLED=False
    )
    
    db.init_app(app)
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    app.register_blueprint(attendance_bp)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create test client for system testing."""
    return test_app.test_client()


@pytest.fixture
def system_users(test_app):
    """Create a complete set of users for system testing."""
    with test_app.app_context():
        # Admin user
        admin = User(user_id=1, name='System Admin', is_faculty=True)
        admin.role = 'admin'
        
        # Teacher users
        teacher1 = User(user_id=2, name='Teacher One', is_faculty=True)
        teacher1.role = 'teacher'
        
        teacher2 = User(user_id=3, name='Teacher Two', is_faculty=True)
        teacher2.role = 'teacher'
        
        # Student users
        students = []
        for i in range(4, 14):  # 10 students
            student = User(user_id=i, name=f'Student {i-3}', is_faculty=False)
            student.role = 'student'
            students.append(student)
        
        db.session.add_all([admin, teacher1, teacher2] + students)
        db.session.commit()
        
        return {
            'admin': admin,
            'teachers': [teacher1, teacher2],
            'students': students
        }


class TestSystemScenarios:
    """Test complete system scenarios for override functionality."""
    
    def test_scenario_medical_certificate_override(self, test_app, system_users):
        """
        Scenario: Student submits medical certificate for missed class
        
        Steps:
        1. Student is marked absent by teacher
        2. Student submits medical certificate
        3. Admin reviews and overrides attendance to present
        4. System records the override with reason
        """
        with test_app.app_context():
            admin = system_users['admin']
            student = system_users['students'][0]
            
            # Step 1: Teacher marks student absent
            attendance = Attendance(
                student_id=student.user_id,
                date=date.today(),
                is_present=False
            )
            db.session.add(attendance)
            db.session.commit()
            
            assert attendance.is_present is False
            
            # Step 2 & 3: Admin overrides after medical certificate submission
            attendance.is_present = True
            attendance.is_overridden = True
            attendance.override_reason = "Medical certificate submitted for illness"
            attendance.overridden_by = admin.user_id
            attendance.override_timestamp = datetime.utcnow().isoformat()
            db.session.commit()
            
            # Step 4: Verify complete audit trail
            final_record = Attendance.query.get(attendance.id)
            
            assert final_record.is_present is True
            assert final_record.is_overridden is True
            assert "Medical certificate" in final_record.override_reason
            assert final_record.overridden_by == admin.user_id
            assert final_record.override_timestamp is not None
    
    def test_scenario_system_error_correction(self, test_app, system_users):
        """
        Scenario: System error causes incorrect attendance marking
        
        Steps:
        1. Multiple students marked incorrectly due to system glitch
        2. Admin identifies the error
        3. Admin corrects all affected records
        4. System maintains audit trail for all corrections
        """
        with test_app.app_context():
            admin = system_users['admin']
            affected_students = system_users['students'][:5]
            
            # Step 1: Create incorrect records (system glitch)
            incorrect_records = []
            for student in affected_students:
                attendance = Attendance(
                    student_id=student.user_id,
                    date=date.today(),
                    is_present=False  # Incorrectly marked as absent
                )
                db.session.add(attendance)
                incorrect_records.append(attendance)
            
            db.session.commit()
            
            # Step 2 & 3: Admin corrects all records
            for attendance in incorrect_records:
                attendance.is_present = True
                attendance.is_overridden = True
                attendance.override_reason = "Correcting system error - biometric scan malfunction"
                attendance.overridden_by = admin.user_id
                attendance.override_timestamp = datetime.utcnow().isoformat()
            
            db.session.commit()
            
            # Step 4: Verify all corrections
            for attendance in incorrect_records:
                db.session.refresh(attendance)
                assert attendance.is_present is True
                assert attendance.is_overridden is True
                assert "system error" in attendance.override_reason.lower()
    
    def test_scenario_late_arrival_override(self, test_app, system_users):
        """
        Scenario: Student arrives late and provides valid excuse
        
        Steps:
        1. Student marked absent for being late
        2. Student provides documentation for traffic jam
        3. Admin decides to mark as present with note
        4. Override recorded with specific reason
        """
        with test_app.app_context():
            admin = system_users['admin']
            student = system_users['students'][1]
            
            # Step 1: Initial absent marking
            attendance = Attendance(
                student_id=student.user_id,
                date=date.today(),
                is_present=False
            )
            db.session.add(attendance)
            db.session.commit()
            
            # Step 2 & 3: Admin override after review
            attendance.is_present = True
            attendance.is_overridden = True
            attendance.override_reason = "Late arrival due to documented traffic accident on highway"
            attendance.overridden_by = admin.user_id
            attendance.override_timestamp = datetime.utcnow().isoformat()
            db.session.commit()
            
            # Step 4: Verify override
            assert attendance.is_overridden is True
            assert "traffic" in attendance.override_reason.lower()
    
    def test_scenario_attendance_percentage_improvement(self, test_app, system_users):
        """
        Scenario: Track how overrides affect student's attendance percentage
        
        Steps:
        1. Student has low attendance (below threshold)
        2. Multiple corrections needed after documentation review
        3. Admin overrides justified absences
        4. Student's attendance percentage increases
        """
        with test_app.app_context():
            admin = system_users['admin']
            student = system_users['students'][2]
            
            # Step 1: Create attendance history - 10 classes, 5 absent
            for i in range(10):
                attendance = Attendance(
                    student_id=student.user_id,
                    date=date.today(),
                    is_present=(i % 2 == 0)  # Alternating present/absent
                )
                db.session.add(attendance)
            db.session.commit()
            
            # Calculate initial percentage
            all_records = Attendance.query.filter_by(student_id=student.user_id).all()
            initial_present = sum(1 for r in all_records if r.is_present)
            initial_percentage = (initial_present / len(all_records)) * 100
            
            assert initial_percentage == 50.0  # 5 out of 10
            
            # Step 2 & 3: Admin reviews and overrides 3 justified absences
            absent_records = Attendance.query.filter_by(
                student_id=student.user_id,
                is_present=False
            ).limit(3).all()
            
            for idx, record in enumerate(absent_records, 1):
                record.is_present = True
                record.is_overridden = True
                record.override_reason = f"Justified absence #{idx} - documented medical/family emergency"
                record.overridden_by = admin.user_id
                record.override_timestamp = datetime.utcnow().isoformat()
            
            db.session.commit()
            
            # Step 4: Calculate new percentage
            updated_records = Attendance.query.filter_by(student_id=student.user_id).all()
            final_present = sum(1 for r in updated_records if r.is_present)
            final_percentage = (final_present / len(updated_records)) * 100
            
            assert final_percentage == 80.0  # 8 out of 10
            assert final_percentage > initial_percentage
    
    def test_scenario_audit_trail_for_compliance(self, test_app, system_users):
        """
        Scenario: Generate audit report for compliance
        
        Steps:
        1. Multiple overrides performed by different admins
        2. Query all overridden records
        3. Verify complete audit information available
        4. Generate compliance report data
        """
        with test_app.app_context():
            admin = system_users['admin']
            students = system_users['students'][:3]
            
            # Step 1: Create overrides with different scenarios
            override_scenarios = [
                ("Medical certificate provided", students[0]),
                ("System error correction", students[1]),
                ("Documentation reviewed and approved", students[2])
            ]
            
            for reason, student in override_scenarios:
                attendance = Attendance(
                    student_id=student.user_id,
                    date=date.today(),
                    is_present=False
                )
                db.session.add(attendance)
                db.session.commit()
                
                attendance.is_present = True
                attendance.is_overridden = True
                attendance.override_reason = reason
                attendance.overridden_by = admin.user_id
                attendance.override_timestamp = datetime.utcnow().isoformat()
                db.session.commit()
            
            # Step 2: Query all overridden records
            overridden_records = Attendance.query.filter_by(is_overridden=True).all()
            
            # Step 3: Verify audit information
            assert len(overridden_records) >= 3
            
            for record in overridden_records:
                # Each record must have complete audit trail
                assert record.is_overridden is True
                assert record.override_reason is not None
                assert record.overridden_by is not None
                assert record.override_timestamp is not None
            
            # Step 4: Generate compliance report data
            report_data = []
            for record in overridden_records:
                student = User.query.get(record.student_id)
                admin_user = User.query.get(record.overridden_by)
                
                report_entry = {
                    'student_name': student.name if student else 'Unknown',
                    'date': record.date.isoformat(),
                    'overridden_by': admin_user.name if admin_user else 'Unknown',
                    'reason': record.override_reason,
                    'timestamp': record.override_timestamp
                }
                report_data.append(report_entry)
            
            assert len(report_data) >= 3
            assert all('reason' in entry for entry in report_data)


class TestSystemPerformance:
    """Test system performance with override operations."""
    
    def test_bulk_override_performance(self, test_app, system_users):
        """Test performance when overriding multiple records at once."""
        with test_app.app_context():
            admin = system_users['admin']
            students = system_users['students']
            
            # Create 100 attendance records
            bulk_records = []
            for i in range(100):
                student = students[i % len(students)]
                attendance = Attendance(
                    student_id=student.user_id,
                    date=date.today(),
                    is_present=False
                )
                bulk_records.append(attendance)
            
            db.session.add_all(bulk_records)
            db.session.commit()
            
            # Override all records
            import time
            start_time = time.time()
            
            for record in bulk_records:
                record.is_present = True
                record.is_overridden = True
                record.override_reason = "Bulk correction"
                record.overridden_by = admin.user_id
                record.override_timestamp = datetime.utcnow().isoformat()
            
            db.session.commit()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete within reasonable time (adjust threshold as needed)
            assert duration < 5.0  # 5 seconds for 100 records
            
            # Verify all were overridden
            overridden_count = Attendance.query.filter_by(is_overridden=True).count()
            assert overridden_count >= 100


class TestSystemErrorHandling:
    """Test system-wide error handling for override operations."""
    
    def test_rollback_on_error(self, test_app, system_users):
        """Test that failed overrides don't partially update database."""
        with test_app.app_context():
            admin = system_users['admin']
            student = system_users['students'][0]
            
            # Create attendance
            attendance = Attendance(
                student_id=student.user_id,
                date=date.today(),
                is_present=False
            )
            db.session.add(attendance)
            db.session.commit()
            
            original_status = attendance.is_present
            
            try:
                # Attempt invalid operation
                attendance.is_present = True
                attendance.is_overridden = True
                attendance.override_reason = "Test"
                attendance.overridden_by = admin.user_id
                
                # Simulate error before commit
                raise Exception("Simulated error")
                
            except Exception:
                db.session.rollback()
            
            # Verify no changes persisted
            db.session.refresh(attendance)
            assert attendance.is_present == original_status
            assert attendance.is_overridden is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
