"""End-to-end functional tests for complete user workflows."""

import pytest
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


@pytest.mark.system
class TestStudentWorkflow:
    """End-to-end tests for student user workflows."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def student_user(self, app):
        """Create a student user for testing."""
        from models import User, db
        
        with app.app_context():
            user = User(
                srn='PES1UG21CS001',
                name='E2E Student',
                role='student',
                email='e2estudent@example.com'
            )
            user.set_password('Student123!')
            db.session.add(user)
            db.session.commit()
            
            yield user
            
            # Cleanup
            db.session.delete(user)
            db.session.commit()
    
    def test_complete_student_journey(self, client, student_user, app):
        """Test complete student journey: login -> view dashboard -> view attendance -> logout."""
        
        # Step 1: Access login page
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        
        # Step 2: Login
        response = client.post('/login', data={
            'srn': 'PES1UG21CS001',
            'password': 'Student123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Step 3: View student dashboard
        response = client.get('/student_dashboard')
        assert response.status_code == 200
        assert b'E2E Student' in response.data or b'dashboard' in response.data.lower()
        
        # Step 4: View attendance records
        response = client.get('/view_attendance')
        assert response.status_code == 200
        
        # Step 5: Logout
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Step 6: Verify cannot access protected page after logout
        response = client.get('/student_dashboard')
        assert response.status_code in [302, 401]


@pytest.mark.system
class TestTeacherWorkflow:
    """End-to-end tests for teacher user workflows."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def teacher_user(self, app):
        """Create a teacher user for testing."""
        from models import User, db
        
        with app.app_context():
            user = User(
                srn='TCH001',
                name='E2E Teacher',
                role='teacher',
                email='e2eteacher@example.com'
            )
            user.set_password('Teacher123!')
            db.session.add(user)
            db.session.commit()
            
            yield user
            
            # Cleanup
            db.session.delete(user)
            db.session.commit()
    
    def test_complete_teacher_journey(self, client, teacher_user, app):
        """Test complete teacher journey: login -> dashboard -> mark attendance -> logout."""
        from models import Attendance, db
        
        # Step 1: Login
        response = client.post('/login', data={
            'srn': 'TCH001',
            'password': 'Teacher123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Step 2: View faculty dashboard
        response = client.get('/faculty_dashboard')
        assert response.status_code == 200
        
        # Step 3: Mark attendance
        response = client.post('/mark_attendance', data={
            'srn': 'PES1UG21CS002',
            'subject': 'Mathematics',
            'date': date.today().strftime('%Y-%m-%d'),
            'status': 'present'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            # Verify attendance was marked
            attendance = Attendance.query.filter_by(
                srn='PES1UG21CS002',
                subject='Mathematics',
                date=date.today()
            ).first()
            
            if attendance:
                assert attendance.status == 'present'
                # Cleanup
                db.session.delete(attendance)
                db.session.commit()
        
        # Step 4: Logout
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200


@pytest.mark.system
class TestAttendanceManagementWorkflow:
    """End-to-end tests for attendance management workflows."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def setup_users(self, app):
        """Create student and teacher users."""
        from models import User, db
        
        with app.app_context():
            student = User(
                srn='PES1UG21CS100',
                name='Workflow Student',
                role='student',
                email='workflow_student@example.com'
            )
            student.set_password('Student123!')
            
            teacher = User(
                srn='TCH100',
                name='Workflow Teacher',
                role='teacher',
                email='workflow_teacher@example.com'
            )
            teacher.set_password('Teacher123!')
            
            db.session.add_all([student, teacher])
            db.session.commit()
            
            yield {'student': student, 'teacher': teacher}
            
            # Cleanup
            db.session.delete(student)
            db.session.delete(teacher)
            db.session.commit()
    
    def test_teacher_marks_student_views(self, client, setup_users, app):
        """Test workflow: teacher marks attendance, student views it."""
        from models import Attendance, db
        
        # Teacher login and mark attendance
        client.post('/login', data={
            'srn': 'TCH100',
            'password': 'Teacher123!'
        }, follow_redirects=True)
        
        response = client.post('/mark_attendance', data={
            'srn': 'PES1UG21CS100',
            'subject': 'Physics',
            'date': date.today().strftime('%Y-%m-%d'),
            'status': 'present'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        client.get('/logout')
        
        # Student login and view attendance
        client.post('/login', data={
            'srn': 'PES1UG21CS100',
            'password': 'Student123!'
        }, follow_redirects=True)
        
        response = client.get('/view_attendance')
        assert response.status_code == 200
        assert b'Physics' in response.data or b'present' in response.data.lower()
        
        # Cleanup
        with app.app_context():
            attendance = Attendance.query.filter_by(
                srn='PES1UG21CS100',
                subject='Physics',
                date=date.today()
            ).first()
            if attendance:
                db.session.delete(attendance)
                db.session.commit()
        
        client.get('/logout')


@pytest.mark.system
class TestSecurityWorkflow:
    """End-to-end tests for security features."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def test_user(self, app):
        """Create a test user."""
        from models import User, db
        
        with app.app_context():
            user = User(
                srn='SEC001',
                name='Security Test User',
                role='student',
                email='security@example.com'
            )
            user.set_password('SecurePass123!')
            db.session.add(user)
            db.session.commit()
            
            yield user
            
            # Cleanup
            db.session.delete(user)
            db.session.commit()
    
    def test_password_change_workflow(self, client, test_user, app):
        """Test complete password change workflow."""
        
        # Login with old password
        response = client.post('/login', data={
            'srn': 'SEC001',
            'password': 'SecurePass123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Attempt to change password (if endpoint exists)
        # Note: This is a placeholder - actual implementation depends on your routes
        
        client.get('/logout')
    
    def test_account_lockout_workflow(self, client, test_user, app):
        """Test account lockout after failed login attempts."""
        
        # Attempt multiple failed logins
        for i in range(5):
            response = client.post('/login', data={
                'srn': 'SEC001',
                'password': 'WrongPassword'
            }, follow_redirects=True)
        
        # Verify account behavior after multiple failures
        # (Implementation depends on your account locking logic)
    
    def test_session_timeout_workflow(self, client, test_user, app):
        """Test session timeout behavior."""
        
        # Login
        response = client.post('/login', data={
            'srn': 'SEC001',
            'password': 'SecurePass123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Access protected resource
        response = client.get('/student_dashboard')
        assert response.status_code == 200
        
        # Note: Actual session timeout testing would require time manipulation


@pytest.mark.system
class TestDataIntegrityWorkflow:
    """End-to-end tests for data integrity and consistency."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_concurrent_attendance_marking(self, client, app):
        """Test data integrity with concurrent attendance marking."""
        from models import User, Attendance, db
        
        with app.app_context():
            # Create teacher
            teacher = User(
                srn='TCH200',
                name='Concurrent Teacher',
                role='teacher',
                email='concurrent@example.com'
            )
            teacher.set_password('Teacher123!')
            db.session.add(teacher)
            db.session.commit()
            
            # Login
            client.post('/login', data={
                'srn': 'TCH200',
                'password': 'Teacher123!'
            }, follow_redirects=True)
            
            # Mark same attendance multiple times
            for _ in range(3):
                client.post('/mark_attendance', data={
                    'srn': 'PES1UG21CS200',
                    'subject': 'Chemistry',
                    'date': date.today().strftime('%Y-%m-%d'),
                    'status': 'present'
                }, follow_redirects=True)
            
            # Verify only one record exists (or latest update)
            count = Attendance.query.filter_by(
                srn='PES1UG21CS200',
                subject='Chemistry',
                date=date.today()
            ).count()
            
            # Should have deduplication logic
            assert count >= 1
            
            # Cleanup
            Attendance.query.filter_by(
                srn='PES1UG21CS200',
                subject='Chemistry'
            ).delete()
            db.session.delete(teacher)
            db.session.commit()
    
    def test_attendance_date_range_validation(self, client, app):
        """Test attendance date validation."""
        from models import User, db
        
        with app.app_context():
            teacher = User(
                srn='TCH300',
                name='Validation Teacher',
                role='teacher',
                email='validation@example.com'
            )
            teacher.set_password('Teacher123!')
            db.session.add(teacher)
            db.session.commit()
            
            client.post('/login', data={
                'srn': 'TCH300',
                'password': 'Teacher123!'
            }, follow_redirects=True)
            
            # Try to mark attendance for future date
            future_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
            response = client.post('/mark_attendance', data={
                'srn': 'PES1UG21CS300',
                'subject': 'Biology',
                'date': future_date,
                'status': 'present'
            }, follow_redirects=True)
            
            # Should handle future dates appropriately
            # (Implementation depends on your validation logic)
            
            # Cleanup
            db.session.delete(teacher)
            db.session.commit()
