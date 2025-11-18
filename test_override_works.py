"""Simple test to verify admin override attendance works end-to-end."""

import os
import sys
from datetime import datetime, timedelta

# Ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

import main
from models import db, User, Attendance


def test_admin_override_attendance_works():
    """Test that admin can override a student's attendance and it updates correctly."""
    app = main.app
    client = app.test_client()
    
    with app.app_context():
        # Clean up any existing test users from previous runs
        existing_admin = User.query.filter_by(username='admin_override_test').first()
        if existing_admin:
            db.session.delete(existing_admin)
            db.session.commit()
        existing_student = User.query.filter_by(username='student_override_test').first()
        if existing_student:
            # Remove any existing attendance records for this student for a clean slate
            Attendance.query.filter_by(student_id=existing_student.id).delete()
            db.session.delete(existing_student)
            db.session.commit()

        # Create test users
        admin = User(
            username='admin_override_test',
            email='admin@test.com',
            name='Admin Test User',
            role='admin',
            is_faculty=True
        )
        admin.set_password('admin123')  # Properly hash the password
        db.session.add(admin)
        
        student = User(
            username='student_override_test',
            email='student@test.com',
            name='Student Test User',
            role='student'
        )
        student.set_password('student123')  # Properly hash the password
        db.session.add(student)
        db.session.flush()
        
        # Create an attendance record (marked absent)
        today = datetime.now().date()
        attendance = Attendance(
            student_id=student.id,
            date=today,
            is_present=False,  # Initially absent
            course_id='TEST101',
            marked_by='faculty'
        )
        db.session.add(attendance)
        db.session.commit()
        
        record_id = attendance.id
        student_id = student.id
        
        # Verify the record is initially absent
        record = Attendance.query.get(record_id)
        assert record.is_present == False, "Record should be marked absent initially"
        print(f"✓ Initial state: Record {record_id} is absent (is_present=False)")
        
        # Admin logs in
        login_resp = client.post('/login', data={
            'username': 'admin_override_test',
            'password': 'admin123'
        }, follow_redirects=True)
        assert login_resp.status_code == 200
        print("✓ Admin logged in successfully")
        
        # Admin overrides the attendance to present
        override_resp = client.post(
            f'/api/admin/override/attendance/{record_id}',
            json={
                'new_status': 'present',
                'reason': 'System error - student was actually present'
            }
        )
        
        assert override_resp.status_code == 200, f"Override failed: {override_resp.data}"
        data = override_resp.get_json()
        assert data['success'] == True
        print(f"✓ Admin override successful: {data['message']}")
        
        # Verify the record is now marked present in the database
        record = Attendance.query.get(record_id)
        assert record.is_present == True, "Record should be marked present after override"
        assert record.is_overridden == True, "Override flag should be set"
        assert record.override_reason == 'System error - student was actually present'
        assert record.overridden_by == admin.id
        print(f"✓ Database updated: Record is now present (is_present=True)")
        print(f"  - is_overridden: {record.is_overridden}")
        print(f"  - override_reason: {record.override_reason}")
        print(f"  - overridden_by: {record.overridden_by}")
        
        # Verify it appears correctly in the get_student_records API
        records_resp = client.get(f'/api/admin/override/student/{student_id}/records')
        assert records_resp.status_code == 200
        records_data = records_resp.get_json()
        assert records_data['success'] == True
        
        # Find our record in the response
        found_record = None
        for rec in records_data['records']:
            if rec['id'] == record_id:
                found_record = rec
                break
        
        assert found_record is not None, "Record not found in student records"
        assert found_record['status'] == 'present', f"API should show status as present, got {found_record['status']}"
        assert found_record['is_overridden'] == True
        print(f"✓ API shows correct status: {found_record['status']} (is_overridden={found_record['is_overridden']})")
        
        # Test undo override
        undo_resp = client.post(f'/api/admin/override/attendance/{record_id}/undo')
        assert undo_resp.status_code == 200
        undo_data = undo_resp.get_json()
        assert undo_data['success'] == True
        print(f"✓ Undo successful: {undo_data['message']}")
        
        # Verify override flags are cleared
        record = Attendance.query.get(record_id)
        assert record.is_overridden == False
        assert record.override_reason == None
        print(f"✓ Override flags cleared after undo")
        print(f"  - Note: is_present remains {record.is_present} (undo doesn't revert status)")
        
        print("\n✅ ALL TESTS PASSED - Admin override attendance works correctly!")


if __name__ == '__main__':
    test_admin_override_attendance_works()
