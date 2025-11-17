"""Test suite for admin attendance override functionality.

Tests cover:
- Override attendance records
- Undo overrides
- Retrieve student attendance records
- Access override history (audit trail)
- Search students
- Calculate override statistics
- RBAC enforcement (admin-only access)
"""

import pytest
from datetime import datetime, timedelta
from src.models import db, User, Attendance
from src.admin_override_api import admin_override_bp


@pytest.fixture
def app_with_override(app):
    """Setup app with admin override blueprint registered."""
    if admin_override_bp not in app.blueprints.values():
        app.register_blueprint(admin_override_bp)
    return app


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        admin = User(
            username='admin_test',
            email='admin@test.com',
            password='admin123',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        return admin


@pytest.fixture
def student_user(app):
    """Create a student user for testing."""
    with app.app_context():
        student = User(
            username='student_test',
            email='student@test.com',
            password='student123',
            role='student'
        )
        db.session.add(student)
        db.session.commit()
        return student


@pytest.fixture
def test_attendance_records(app, student_user):
    """Create multiple attendance records for testing."""
    with app.app_context():
        records = []
        base_date = datetime.now().date()
        
        for i in range(5):
            date = base_date - timedelta(days=i)
            record = Attendance(
                student_id=student_user.id,
                course_id='TEST101',
                date=date,
                is_present=bool(i % 2),  # Alternate present/absent
                marked_by='auto',
                updated_at=datetime.utcnow()
            )
            records.append(record)
            db.session.add(record)
        
        db.session.commit()
        return records


class TestAdminOverrideAPI:
    """Test suite for admin override API endpoints."""

    def test_override_attendance_success(self, client, admin_user, test_attendance_records):
        """Test successfully overriding an attendance record."""
        login_response = client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)
        assert login_response.status_code == 200

        record_id = test_attendance_records[0].id
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': 'System error corrected by admin'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Attendance overridden successfully'

    def test_override_attendance_invalid_reason(self, client, admin_user, test_attendance_records):
        """Test override with invalid reason length."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        record_id = test_attendance_records[0].id
        
        # Test reason too short
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': 'bad'
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_override_attendance_not_found(self, client, admin_user):
        """Test override on non-existent record."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        response = client.post(
            '/api/admin/override/attendance/99999',
            json={
                'new_status': 'present',
                'reason': 'This record does not exist'
            }
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False

    def test_undo_override_success(self, client, admin_user, test_attendance_records):
        """Test successfully undoing an override."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        record_id = test_attendance_records[0].id
        
        # First override the record
        client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': 'Test override'
            }
        )
        
        # Now undo it
        response = client.post(f'/api/admin/override/attendance/{record_id}/undo')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Override removed successfully'

    def test_get_student_records(self, client, admin_user, student_user, test_attendance_records):
        """Test retrieving a student's attendance records."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        response = client.get(f'/api/admin/override/student/{student_user.id}/records')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['records']) > 0
        assert data['total_records'] == len(test_attendance_records)

    def test_get_student_records_with_date_filter(self, client, admin_user, student_user, test_attendance_records):
        """Test retrieving student records with date range filter."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        base_date = datetime.now().date()
        from_date = base_date - timedelta(days=3)
        to_date = base_date - timedelta(days=1)

        response = client.get(
            f'/api/admin/override/student/{student_user.id}/records?'
            f'from_date={from_date}&to_date={to_date}'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Should have fewer records due to date filter
        assert data['total_records'] <= len(test_attendance_records)

    def test_get_override_history(self, client, admin_user, test_attendance_records):
        """Test retrieving override history (audit trail)."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        # Create an override first
        record_id = test_attendance_records[0].id
        client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': 'Test override for history'
            }
        )

        # Get history
        response = client.get('/api/admin/override/override-history')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['history']) > 0
        
        # Verify audit trail contains expected fields
        override = data['history'][0]
        assert 'student' in override
        assert 'date' in override
        assert 'override_reason' in override
        assert 'overridden_by' in override

    def test_search_students(self, client, admin_user, student_user):
        """Test searching for students."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        response = client.get('/api/admin/override/search-students?query=student')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['students']) > 0
        
        # Verify student in results
        student_found = any(s['username'] == 'student_test' for s in data['students'])
        assert student_found

    def test_search_students_empty_query(self, client, admin_user):
        """Test student search with insufficient query length."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        response = client.get('/api/admin/override/search-students?query=a')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_get_statistics(self, client, admin_user, test_attendance_records):
        """Test retrieving override statistics."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        # Create multiple overrides
        for i in range(3):
            record_id = test_attendance_records[i].id
            client.post(
                f'/api/admin/override/attendance/{record_id}',
                json={
                    'new_status': 'present',
                    'reason': f'Test override {i+1}'
                }
            )

        # Get statistics
        response = client.get('/api/admin/override/stats')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        stats = data['stats']
        assert 'total_overrides' in stats
        assert 'override_percentage' in stats
        assert 'overrides_by_admin' in stats
        assert stats['total_overrides'] >= 3

    def test_rbac_non_admin_cannot_override(self, client, student_user, test_attendance_records):
        """Test that non-admin users cannot override attendance."""
        client.post('/login', data={
            'username': 'student_test',
            'password': 'student123'
        }, follow_redirects=True)

        record_id = test_attendance_records[0].id
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': 'Student should not be able to override'
            }
        )
        
        # Should be denied (401 Unauthorized or 403 Forbidden)
        assert response.status_code in [401, 403]

    def test_rbac_non_admin_cannot_access_history(self, client, student_user):
        """Test that non-admin users cannot access override history."""
        client.post('/login', data={
            'username': 'student_test',
            'password': 'student123'
        }, follow_redirects=True)

        response = client.get('/api/admin/override/override-history')
        
        assert response.status_code in [401, 403]

    def test_rbac_non_admin_cannot_access_stats(self, client, student_user):
        """Test that non-admin users cannot access override statistics."""
        client.post('/login', data={
            'username': 'student_test',
            'password': 'student123'
        }, follow_redirects=True)

        response = client.get('/api/admin/override/stats')
        
        assert response.status_code in [401, 403]

    def test_override_audit_trail_fields(self, client, admin_user, test_attendance_records):
        """Test that override creates proper audit trail with all fields."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        record_id = test_attendance_records[0].id
        override_reason = 'System glitch corrected'
        
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': override_reason
            }
        )
        
        assert response.status_code == 200
        
        # Verify audit trail was created
        response = client.get('/api/admin/override/override-history')
        data = response.get_json()
        
        override = data['history'][0]
        assert override['override_reason'] == override_reason
        assert override['overridden_by']['username'] == 'admin_test'
        assert override['override_timestamp'] is not None

    def test_concurrent_overrides_different_records(self, client, admin_user, test_attendance_records):
        """Test overriding multiple different records."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        reasons = [
            'First student override',
            'Second student override',
            'Third student override'
        ]

        for i, record in enumerate(test_attendance_records[:3]):
            response = client.post(
                f'/api/admin/override/attendance/{record.id}',
                json={
                    'new_status': 'present',
                    'reason': reasons[i]
                }
            )
            assert response.status_code == 200

        # Verify all overrides were recorded
        response = client.get('/api/admin/override/stats')
        data = response.get_json()
        assert data['stats']['total_overrides'] >= 3

    def test_invalid_new_status(self, client, admin_user, test_attendance_records):
        """Test override with invalid status value."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        record_id = test_attendance_records[0].id
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'invalid_status',
                'reason': 'This status is invalid'
            }
        )
        
        assert response.status_code == 400

    def test_missing_required_fields(self, client, admin_user, test_attendance_records):
        """Test override with missing required fields."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        record_id = test_attendance_records[0].id
        
        # Missing new_status
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={'reason': 'Missing status'}
        )
        assert response.status_code == 400
        
        # Missing reason
        response = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={'new_status': 'present'}
        )
        assert response.status_code == 400


class TestAdminOverridePage:
    """Test the admin override page template rendering."""

    def test_admin_override_page_loads(self, client, admin_user):
        """Test that admin can access the override page."""
        client.post('/login', data={
            'username': 'admin_test',
            'password': 'admin123'
        }, follow_redirects=True)

        response = client.get('/admin/override-attendance')
        assert response.status_code == 200
        assert b'Attendance Override' in response.data

    def test_non_admin_cannot_access_override_page(self, client, student_user):
        """Test that non-admin users are denied access to override page."""
        client.post('/login', data={
            'username': 'student_test',
            'password': 'student123'
        }, follow_redirects=True)

        response = client.get('/admin/override-attendance')
        # Should be redirected or denied
        assert response.status_code in [302, 403]

    def test_unauthenticated_redirected_to_login(self, client):
        """Test that unauthenticated users are redirected to login."""
        response = client.get('/admin/override-attendance')
        assert response.status_code == 302  # Redirect to login
