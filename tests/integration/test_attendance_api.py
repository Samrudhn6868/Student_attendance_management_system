"""Tests for SAS-93: API for Attendance Submission and Updates.

This module contains comprehensive tests for the attendance API endpoints:
- Teacher/Admin can submit attendance
- Teacher/Admin can update attendance
- Student cannot modify attendance (403)
- Data persists correctly in SQLite
- Role checks and JWT validation work properly
- Both session and JWT authentication methods work
"""

import os
import sys
import pytest
from datetime import datetime, date

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flask import Flask
from flask_login import LoginManager, login_user
from werkzeug.security import generate_password_hash

# Import models and blueprints
from models import db, User as MainUser, Attendance
from attendance_api import attendance_api_bp
from auth_middleware import generate_jwt_token


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    })
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(MainUser, int(user_id))
    
    # Register blueprint
    app.register_blueprint(attendance_api_bp)
    
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
def app_context(test_app):
    """Create application context."""
    with test_app.app_context():
        yield test_app


@pytest.fixture
def test_users(app_context):
    """Create test users: student, teacher, admin."""
    users = {}
    
    # Create student
    student = MainUser(
        username='PES1UG23CS001',
        password_hash=generate_password_hash('student123'),
        is_faculty=False,
        name='Test Student',
        role='student'
    )
    db.session.add(student)
    
    # Create teacher
    teacher = MainUser(
        username='TEACHER001',
        password_hash=generate_password_hash('teacher123'),
        is_faculty=True,
        name='Test Teacher',
        role='teacher'
    )
    db.session.add(teacher)
    
    # Create admin
    admin = MainUser(
        username='ADMIN001',
        password_hash=generate_password_hash('admin123'),
        is_faculty=True,
        name='Test Admin',
        role='admin'
    )
    db.session.add(admin)
    
    db.session.commit()
    
    users['student'] = student
    users['teacher'] = teacher
    users['admin'] = admin
    
    return users


@pytest.fixture
def auth_headers(test_users):
    """Generate JWT tokens for each user role."""
    headers = {}
    
    for role, user in test_users.items():
        token = generate_jwt_token(user)
        headers[role] = {'Authorization': f'Bearer {token}'}
    
    return headers


# ============================================================================
# Test Session-Based Authentication (Flask-Login)
# ============================================================================

def test_submit_attendance_as_teacher_session(client, test_app, test_users):
    """Test teacher can submit attendance using session auth."""
    with test_app.test_request_context():
        with client:
            # Login as teacher
            teacher = test_users['teacher']
            login_user(teacher)
            
            # Submit attendance
            response = client.post('/api/attendance/submit', json={
                'student_srn': 'PES1UG23CS001',
                'course_id': 'CSE101',
                'date': '2025-11-09',
                'status': 'present'
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert data['attendance']['student_srn'] == 'PES1UG23CS001'
            assert data['attendance']['status'] == 'present'
            
            # Verify in database
            with test_app.app_context():
                attendance = Attendance.query.filter_by(student_srn='PES1UG23CS001').first()
                assert attendance is not None
                assert attendance.course_id == 'CSE101'
                assert attendance.status == 'present'
                assert attendance.marked_by == 'TEACHER001'


def test_submit_attendance_as_admin_session(client, test_app, test_users):
    """Test admin can submit attendance using session auth."""
    with test_app.test_request_context():
        with client:
            # Login as admin
            admin = test_users['admin']
            login_user(admin)
            
            # Submit attendance
            response = client.post('/api/attendance/submit', json={
                'student_srn': 'PES1UG23CS002',
                'course_id': 'CSE102',
                'date': '2025-11-09',
                'status': 'absent'
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['success'] is True
            assert data['attendance']['marked_by'] == 'ADMIN001'


def test_submit_attendance_as_student_denied_session(client, test_app, test_users):
    """Test student cannot submit attendance (403) using session auth."""
    with test_app.test_request_context():
        with client:
            # Login as student
            student = test_users['student']
            login_user(student)
            
            # Try to submit attendance
            response = client.post('/api/attendance/submit', json={
                'student_srn': 'PES1UG23CS003',
                'course_id': 'CSE103',
                'date': '2025-11-09',
                'status': 'present'
            })
            
            # Should get 403 status code
            assert response.status_code == 403
            
            # Verify response contains error message
            data = response.get_json()
            if data:
                # Check if it's an error response
                assert (data.get('success') is False or 
                        'error' in data or 
                        'Access denied' in str(data) or
                        'access denied' in str(data).lower())
            # If no JSON data, the 403 status code itself is sufficient verification


def test_update_attendance_as_teacher_session(client, test_app, test_users):
    """Test teacher can update attendance using session auth."""
    with test_app.app_context():
        # Create existing attendance record
        attendance = Attendance(
            student_srn='PES1UG23CS004',
            course_id='CSE104',
            date=date(2025, 11, 9),
            status='absent',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        db.session.add(attendance)
        db.session.commit()
        attendance_id = attendance.id
    
    with test_app.test_request_context():
        with client:
            # Login as teacher
            teacher = test_users['teacher']
            login_user(teacher)
            
            # Update attendance
            response = client.put('/api/attendance/update', json={
                'attendance_id': attendance_id,
                'status': 'present',
                'reason': 'Correction needed'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['attendance']['status'] == 'present'
            assert data['changes']['old_status'] == 'absent'
            assert data['changes']['new_status'] == 'present'
            
            # Verify in database
            with test_app.app_context():
                updated = db.session.get(Attendance, attendance_id)
                assert updated.status == 'present'


def test_update_nonexistent_attendance_404(client, test_app, test_users):
    """Test updating nonexistent attendance returns 404."""
    with test_app.test_request_context():
        with client:
            # Login as teacher
            teacher = test_users['teacher']
            login_user(teacher)
            
            # Try to update nonexistent record
            response = client.put('/api/attendance/update', json={
                'attendance_id': 99999,
                'status': 'present'
            })
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'Not found' in data['error']


def test_view_attendance_as_teacher_session(client, test_app, test_users):
    """Test teacher can view all attendance using session auth."""
    with test_app.app_context():
        # Create test data
        for i in range(3):
            attendance = Attendance(
                student_srn=f'PES1UG23CS{i:03d}',
                course_id='CSE101',
                date=date(2025, 11, 9),
                status='present' if i % 2 == 0 else 'absent',
                marked_by='TEACHER001',
                updated_at=datetime.utcnow()
            )
            db.session.add(attendance)
        db.session.commit()
    
    with test_app.test_request_context():
        with client:
            # Login as teacher
            teacher = test_users['teacher']
            login_user(teacher)
            
            # View all attendance
            response = client.get('/api/attendance/view')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['count'] >= 3
            assert len(data['attendance']) >= 3


def test_view_attendance_with_filters(client, test_app, test_users):
    """Test viewing attendance with query filters."""
    with test_app.app_context():
        # Create test data
        attendance = Attendance(
            student_srn='PES1UG23CS999',
            course_id='CSE999',
            date=date(2025, 11, 9),
            status='present',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        db.session.add(attendance)
        db.session.commit()
    
    with test_app.test_request_context():
        with client:
            # Login as teacher
            teacher = test_users['teacher']
            login_user(teacher)
            
            # Filter by student
            response = client.get('/api/attendance/view?student_srn=PES1UG23CS999')
            assert response.status_code == 200
            data = response.get_json()
            assert data['count'] >= 1
            assert all(a['student_srn'] == 'PES1UG23CS999' for a in data['attendance'])
            
            # Filter by course
            response = client.get('/api/attendance/view?course_id=CSE999')
            assert response.status_code == 200
            data = response.get_json()
            assert all(a['course_id'] == 'CSE999' for a in data['attendance'])
            
            # Filter by status
            response = client.get('/api/attendance/view?status=present')
            assert response.status_code == 200
            data = response.get_json()
            assert all(a['status'] == 'present' for a in data['attendance'])


# ============================================================================
# Test JWT-Based Authentication
# ============================================================================

def test_submit_attendance_jwt_teacher(client, test_app, auth_headers):
    """Test teacher can submit attendance using JWT."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS101',
                              'course_id': 'CSE201',
                              'date': '2025-11-09',
                              'status': 'present'
                          },
                          headers=auth_headers['teacher'])
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['auth_method'] == 'JWT'
    assert data['attendance']['student_srn'] == 'PES1UG23CS101'


def test_submit_attendance_jwt_admin(client, test_app, auth_headers):
    """Test admin can submit attendance using JWT."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS102',
                              'course_id': 'CSE202',
                              'date': '2025-11-09',
                              'status': 'absent'
                          },
                          headers=auth_headers['admin'])
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True


def test_submit_attendance_jwt_student_denied(client, test_app, auth_headers):
    """Test student cannot submit attendance via JWT (403)."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS103',
                              'course_id': 'CSE203',
                              'date': '2025-11-09',
                              'status': 'present'
                          },
                          headers=auth_headers['student'])
    
    assert response.status_code == 403
    data = response.get_json()
    assert 'Access denied' in data['error']


def test_submit_attendance_jwt_no_token(client):
    """Test submitting without JWT token returns 401."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS104',
                              'course_id': 'CSE204',
                              'date': '2025-11-09',
                              'status': 'present'
                          })
    
    assert response.status_code == 401
    data = response.get_json()
    assert 'No token provided' in data['error']


def test_update_attendance_jwt_teacher(client, test_app, auth_headers):
    """Test teacher can update attendance using JWT."""
    # Create attendance record
    with test_app.app_context():
        attendance = Attendance(
            student_srn='PES1UG23CS105',
            course_id='CSE205',
            date=date(2025, 11, 9),
            status='absent',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        db.session.add(attendance)
        db.session.commit()
        attendance_id = attendance.id
    
    # Update via JWT
    response = client.put('/api/attendance/jwt/update',
                         json={
                             'attendance_id': attendance_id,
                             'status': 'present',
                             'reason': 'Student was present but marked incorrectly'
                         },
                         headers=auth_headers['teacher'])
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['auth_method'] == 'JWT'
    assert data['changes']['new_status'] == 'present'


def test_view_attendance_jwt_student_restricted(client, test_app, auth_headers):
    """Test student via JWT can only see their own attendance."""
    # Create attendance for different students
    with test_app.app_context():
        # Student's own record
        attendance1 = Attendance(
            student_srn='PES1UG23CS001',  # Student's username
            course_id='CSE301',
            date=date(2025, 11, 9),
            status='present',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        # Another student's record
        attendance2 = Attendance(
            student_srn='PES1UG23CS999',
            course_id='CSE301',
            date=date(2025, 11, 9),
            status='present',
            marked_by='TEACHER001',
            updated_at=datetime.utcnow()
        )
        db.session.add(attendance1)
        db.session.add(attendance2)
        db.session.commit()
    
    # View as student
    response = client.get('/api/attendance/jwt/view',
                         headers=auth_headers['student'])
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    # Student should only see their own records
    assert all(a['student_srn'] == 'PES1UG23CS001' for a in data['attendance'])


def test_view_attendance_jwt_teacher_all(client, test_app, auth_headers):
    """Test teacher via JWT can view all attendance."""
    # Create multiple records
    with test_app.app_context():
        for i in range(5):
            attendance = Attendance(
                student_srn=f'PES1UG23CS{500+i}',
                course_id='CSE401',
                date=date(2025, 11, 9),
                status='present',
                marked_by='TEACHER001',
                updated_at=datetime.utcnow()
            )
            db.session.add(attendance)
        db.session.commit()
    
    # View as teacher
    response = client.get('/api/attendance/jwt/view',
                         headers=auth_headers['teacher'])
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['role'] == 'teacher'
    assert data['count'] >= 5


# ============================================================================
# Test Validation and Error Handling
# ============================================================================

def test_submit_attendance_missing_fields(client, test_app, auth_headers):
    """Test submitting attendance with missing required fields."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS200',
                              # Missing course_id, date, status
                          },
                          headers=auth_headers['teacher'])
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'Validation error' in data['error']


def test_submit_attendance_invalid_status(client, test_app, auth_headers):
    """Test submitting attendance with invalid status."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS201',
                              'course_id': 'CSE501',
                              'date': '2025-11-09',
                              'status': 'maybe'  # Invalid status
                          },
                          headers=auth_headers['teacher'])
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'present' in data['message'] or 'absent' in data['message']


def test_submit_attendance_invalid_date_format(client, test_app, auth_headers):
    """Test submitting attendance with invalid date format."""
    response = client.post('/api/attendance/jwt/submit',
                          json={
                              'student_srn': 'PES1UG23CS202',
                              'course_id': 'CSE502',
                              'date': '09-11-2025',  # Wrong format
                              'status': 'present'
                          },
                          headers=auth_headers['teacher'])
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'YYYY-MM-DD' in data['message']


def test_submit_duplicate_attendance(client, test_app, auth_headers):
    """Test submitting duplicate attendance returns error."""
    # Submit first time
    response1 = client.post('/api/attendance/jwt/submit',
                           json={
                               'student_srn': 'PES1UG23CS300',
                               'course_id': 'CSE600',
                               'date': '2025-11-09',
                               'status': 'present'
                           },
                           headers=auth_headers['teacher'])
    assert response1.status_code == 201
    
    # Try to submit again
    response2 = client.post('/api/attendance/jwt/submit',
                           json={
                               'student_srn': 'PES1UG23CS300',
                               'course_id': 'CSE600',
                               'date': '2025-11-09',
                               'status': 'absent'
                           },
                           headers=auth_headers['teacher'])
    
    assert response2.status_code == 400
    data = response2.get_json()
    assert 'Duplicate' in data['error'] or 'already exists' in data['message']


def test_view_attendance_invalid_date_filter(client, test_app, auth_headers):
    """Test viewing attendance with invalid date filter."""
    response = client.get('/api/attendance/jwt/view?date=invalid-date',
                         headers=auth_headers['teacher'])
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'date' in data['message'].lower()


def test_view_attendance_invalid_status_filter(client, test_app, auth_headers):
    """Test viewing attendance with invalid status filter."""
    response = client.get('/api/attendance/jwt/view?status=maybe',
                         headers=auth_headers['teacher'])
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'status' in data['message'].lower()


# ============================================================================
# Test Data Persistence
# ============================================================================

def test_attendance_persists_across_requests(client, test_app, auth_headers):
    """Test that attendance data persists correctly."""
    # Submit attendance
    submit_response = client.post('/api/attendance/jwt/submit',
                                  json={
                                      'student_srn': 'PES1UG23CS700',
                                      'course_id': 'CSE700',
                                      'date': '2025-11-09',
                                      'status': 'present'
                                  },
                                  headers=auth_headers['teacher'])
    assert submit_response.status_code == 201
    attendance_id = submit_response.get_json()['attendance']['id']
    
    # View attendance
    view_response = client.get('/api/attendance/jwt/view?student_srn=PES1UG23CS700',
                               headers=auth_headers['teacher'])
    assert view_response.status_code == 200
    data = view_response.get_json()
    assert data['count'] >= 1
    found = any(a['id'] == attendance_id for a in data['attendance'])
    assert found, "Submitted attendance not found in view"
    
    # Update attendance
    update_response = client.put('/api/attendance/jwt/update',
                                 json={
                                     'attendance_id': attendance_id,
                                     'status': 'absent',
                                     'reason': 'Correction'
                                 },
                                 headers=auth_headers['teacher'])
    assert update_response.status_code == 200
    
    # Verify update persisted
    verify_response = client.get('/api/attendance/jwt/view?student_srn=PES1UG23CS700',
                                 headers=auth_headers['teacher'])
    data = verify_response.get_json()
    updated_record = next((a for a in data['attendance'] if a['id'] == attendance_id), None)
    assert updated_record is not None
    assert updated_record['status'] == 'absent'


def test_updated_at_changes_on_update(client, test_app, auth_headers):
    """Test that updated_at timestamp changes when record is updated."""
    # Create initial record
    with test_app.app_context():
        attendance = Attendance(
            student_srn='PES1UG23CS800',
            course_id='CSE800',
            date=date(2025, 11, 9),
            status='present',
            marked_by='TEACHER001',
            updated_at=datetime(2025, 11, 9, 10, 0, 0)
        )
        db.session.add(attendance)
        db.session.commit()
        attendance_id = attendance.id
        original_updated_at = attendance.updated_at
    
    # Update the record
    import time
    time.sleep(0.1)  # Small delay to ensure timestamp difference
    
    response = client.put('/api/attendance/jwt/update',
                         json={
                             'attendance_id': attendance_id,
                             'status': 'absent',
                             'reason': 'Testing timestamp update'
                         },
                         headers=auth_headers['teacher'])
    assert response.status_code == 200
    
    # Check that updated_at changed
    with test_app.app_context():
        updated = db.session.get(Attendance, attendance_id)
        assert updated.updated_at > original_updated_at


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
