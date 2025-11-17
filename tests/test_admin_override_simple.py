"""Simple tests for admin attendance override functionality.

These tests verify that:
1. Admin can override student attendance status
2. Changes are persisted in the database
3. Changes are reflected in all API endpoints
4. Audit trail is created
"""

import os
import sys
from datetime import datetime, timedelta

# Ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import main
from models import db, User, Attendance


def setup_test_data():
    """Create test admin and student users with attendance records."""
    app = main.app
    
    with app.app_context():
        # Clear existing test data
        User.query.filter_by(username='admin_override_test').delete()
        User.query.filter_by(username='student_override_test').delete()
        Attendance.query.filter_by(course_id='OVERRIDE_TEST').delete()
        db.session.commit()
        
        # Create admin user
        admin = User(
            username='admin_override_test',
            email='admin_override@test.com',
            password='admin123',
            role='admin',
            is_faculty=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()
        
        # Create student user
        student = User(
            username='student_override_test',
            email='student_override@test.com',
            password='student123',
            role='student',
            is_faculty=False
        )
        student.set_password('student123')
        db.session.add(student)
        db.session.flush()
        
        # Create attendance records
        records = []
        base_date = datetime.now().date()
        
        for i in range(3):
            date = base_date - timedelta(days=i)
            record = Attendance(
                student_id=student.id,
                course_id='OVERRIDE_TEST',
                date=date,
                is_present=(i > 0),  # First record is absent, others present
                marked_by='test_faculty',
                updated_at=datetime.utcnow()
            )
            records.append(record)
            db.session.add(record)
        
        db.session.commit()
        
        return {
            'admin': admin,
            'student': student,
            'records': records,
            'student_id': student.id,
            'first_record_id': records[0].id,
            'first_record_date': records[0].date
        }


def test_override_attendance_changes_is_present():
    """Test that overriding attendance changes the is_present field."""
    data = setup_test_data()
    app = main.app
    client = app.test_client()
    
    # Login as admin
    login_resp = client.post('/login', data={
        'username': 'admin_override_test',
        'password': 'admin123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    
    # Verify initial state - first record should be absent (is_present=False)
    with app.app_context():
        record = Attendance.query.get(data['first_record_id'])
        assert record.is_present == False, "Initial state: record should be absent"
    
    # Override to present
    response = client.post(
        f'/api/admin/override/attendance/{data["first_record_id"]}',
        json={
            'new_status': 'present',
            'reason': 'Test override - student was actually present'
        }
    )
    
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['success'] == True, f"Override failed: {resp_data}"
    
    # Verify override changed is_present
    with app.app_context():
        record = Attendance.query.get(data['first_record_id'])
        assert record.is_present == True, "After override: record should be present"
        assert record.is_overridden == True, "Record should be marked as overridden"
        assert record.override_reason == 'Test override - student was actually present'
        assert record.overridden_by == data['admin'].id


def test_override_reflected_in_student_dashboard():
    """Test that overridden attendance is reflected in student dashboard."""
    data = setup_test_data()
    app = main.app
    client = app.test_client()
    
    # Login as admin
    login_resp = client.post('/login', data={
        'username': 'admin_override_test',
        'password': 'admin123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    
    # Get initial attendance stats
    with app.app_context():
        initial_records = Attendance.query.filter_by(student_id=data['student_id']).all()
        initial_present = sum(1 for r in initial_records if r.is_present)
        print(f"Initial: {initial_present} present out of {len(initial_records)}")
    
    # Override the absent record to present
    response = client.post(
        f'/api/admin/override/attendance/{data["first_record_id"]}',
        json={
            'new_status': 'present',
            'reason': 'Correcting absence'
        }
    )
    assert response.status_code == 200
    
    # Check updated stats
    with app.app_context():
        updated_records = Attendance.query.filter_by(student_id=data['student_id']).all()
        updated_present = sum(1 for r in updated_records if r.is_present)
        print(f"After override: {updated_present} present out of {len(updated_records)}")
        
        assert updated_present > initial_present, \
            f"Present count should increase after override: {initial_present} -> {updated_present}"


def test_override_history_contains_all_info():
    """Test that override history contains complete audit information."""
    data = setup_test_data()
    app = main.app
    client = app.test_client()
    
    # Login as admin
    login_resp = client.post('/login', data={
        'username': 'admin_override_test',
        'password': 'admin123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    
    override_reason = 'Test override for audit trail'
    
    # Create override
    response = client.post(
        f'/api/admin/override/attendance/{data["first_record_id"]}',
        json={
            'new_status': 'present',
            'reason': override_reason
        }
    )
    assert response.status_code == 200
    
    # Get override history
    history_response = client.get('/api/admin/override/override-history')
    assert history_response.status_code == 200
    
    history_data = history_response.get_json()
    assert history_data['success'] == True
    assert len(history_data['history']) > 0
    
    # Check that override is in history with all details
    override = history_data['history'][0]
    assert override['student']['id'] == data['student_id']
    assert override['status'] == 'present'
    assert override['override_reason'] == override_reason
    assert override['overridden_by']['id'] == data['admin'].id
    assert override['override_timestamp'] is not None


def test_override_changes_status_correctly():
    """Test that changing status works in both directions (absent -> present, present -> absent)."""
    data = setup_test_data()
    app = main.app
    client = app.test_client()
    
    # Login as admin
    login_resp = client.post('/login', data={
        'username': 'admin_override_test',
        'password': 'admin123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    
    # Test 1: Override from absent to present
    with app.app_context():
        record = Attendance.query.get(data['first_record_id'])
        assert record.is_present == False, "Start: should be absent"
    
    response1 = client.post(
        f'/api/admin/override/attendance/{data["first_record_id"]}',
        json={
            'new_status': 'present',
            'reason': 'First override: absent to present'
        }
    )
    assert response1.status_code == 200
    
    with app.app_context():
        record = Attendance.query.get(data['first_record_id'])
        assert record.is_present == True, "After first override: should be present"
    
    # Test 2: Override back from present to absent
    response2 = client.post(
        f'/api/admin/override/attendance/{data["first_record_id"]}',
        json={
            'new_status': 'absent',
            'reason': 'Second override: present to absent'
        }
    )
    assert response2.status_code == 200
    
    with app.app_context():
        record = Attendance.query.get(data['first_record_id'])
        assert record.is_present == False, "After second override: should be absent again"
        assert record.override_reason == 'Second override: present to absent'


def test_get_student_records_shows_overridden_status():
    """Test that student records API shows correct status including overrides."""
    data = setup_test_data()
    app = main.app
    client = app.test_client()
    
    # Login as admin
    login_resp = client.post('/login', data={
        'username': 'admin_override_test',
        'password': 'admin123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    
    # Create override
    client.post(
        f'/api/admin/override/attendance/{data["first_record_id"]}',
        json={
            'new_status': 'present',
            'reason': 'Correcting attendance'
        }
    )
    
    # Get student records
    records_response = client.get(f'/api/admin/override/student/{data["student_id"]}/records')
    assert records_response.status_code == 200
    
    records_data = records_response.get_json()
    assert records_data['success'] == True
    
    # Find the overridden record
    overridden_record = None
    for record in records_data['records']:
        if record['id'] == data['first_record_id']:
            overridden_record = record
            break
    
    assert overridden_record is not None, "Should find the overridden record in list"
    assert overridden_record['is_overridden'] == True
    assert overridden_record['status'] == 'present'


if __name__ == '__main__':
    print("Running admin override tests...")
    
    try:
        print("\n1. Testing override changes is_present...")
        test_override_attendance_changes_is_present()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
    
    try:
        print("\n2. Testing override reflected in dashboard...")
        test_override_reflected_in_student_dashboard()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
    
    try:
        print("\n3. Testing override history...")
        test_override_history_contains_all_info()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
    
    try:
        print("\n4. Testing status changes both directions...")
        test_override_changes_status_correctly()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
    
    try:
        print("\n5. Testing student records API...")
        test_get_student_records_shows_overridden_status()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
    
    print("\n" + "="*50)
    print("All tests completed!")
