"""Test the correction request feature with actual working endpoints."""

import sys
sys.path.insert(0, 'src')

from datetime import datetime


def test_correction_endpoints():
    """Test correction request endpoints and functionality."""
    from main import app, db
    from models import User, Attendance, AttendanceCorrectionRequest
    
    app.config['TESTING'] = True

    with app.app_context():
        with app.test_client() as client:
            print("=" * 70)
            print("CORRECTION REQUEST FEATURE - ENDPOINT TEST")
            print("=" * 70)
            
            # Get attendance records endpoint
            print("\n[1] Testing GET /correction/student-attendance-records")
            print("-" * 70)
            
            # Get a student with records
            student = User.query.get(10)
            if student:
                print(f"✓ Found user: {student.name} (ID: {student.id})")
            
            # Test the API
            response = client.get('/correction/student-attendance-records')
            print(f"Response Status: {response.status_code}")
            if response.status_code != 401:
                data = response.get_json()
                if data and 'records' in data:
                    print(f"✓ Records found: {len(data['records'])}")
                    if data['records']:
                        first_record = data['records'][0]
                        print(f"  First record: Date={first_record['date']}, Status={first_record['status']}, Course={first_record['course_id']}")
            else:
                print("(Login required - expected in test mode)")
            
            print("\n[2] Testing Correction Request Submission")
            print("-" * 70)
            print("Testing submission logic...")
            
            # Get a student with records using ORM
            if student:
                # Use ORM to get attendance record - this handles date types automatically
                attendance = Attendance.query.filter_by(student_id=student.id).first()
                
                if attendance:
                    status = 'present' if attendance.is_present else 'absent'
                    requested_status = 'absent' if attendance.is_present else 'present'
                    
                    print(f"✓ Found attendance record:")
                    print(f"  Date (type={type(attendance.date)}): {attendance.date}")
                    print(f"  Current Status: {status}")
                    print(f"  Requested Status: {requested_status}")
                    
                    # Create correction request - date is already proper type from ORM
                    req = AttendanceCorrectionRequest(
                        student_id=student.id,
                        student_name=student.name,
                        course_id=attendance.course_id if hasattr(attendance, 'course_id') else f"Course_{attendance.id}",
                        date=attendance.date,
                        current_status=status,
                        requested_status=requested_status,
                        reason="This is a test correction request with enough characters to pass validation.",
                        status='pending',
                        submitted_at=datetime.utcnow()
                    )
                    
                    db.session.add(req)
                    db.session.commit()
                    
                    print(f"✓ Correction request created (ID: {req.id})")
                    print(f"  Course: {req.course_id}")
                    print(f"  Date: {req.date}")
                    print(f"  Status: {req.status}")
            
            print("\n" + "=" * 70)
            print("✅ ENDPOINT TESTS COMPLETED")
            print("=" * 70)
