"""
Test script to verify attendance marking and retrieval
"""

import sys
import os
from datetime import datetime, date

# Add src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from main import app
from models import User, Attendance

def test_attendance():
    """Test attendance marking and retrieval."""
    
    with app.app_context():
        # Get a teacher and a student
        teacher = User.query.filter_by(role='teacher').first()
        student = User.query.filter_by(role='student').first()
        
        if not teacher or not student:
            print("❌ Error: Could not find teacher or student in database")
            return
        
        print("\n" + "="*80)
        print("ATTENDANCE MARKING AND RETRIEVAL TEST")
        print("="*80)
        
        # Create a test attendance record
        test_date = date.today()
        test_course = "Mathematics"
        
        print(f"\n📝 Marking attendance:")
        print(f"   Student: {student.name} ({student.username})")
        print(f"   Course: {test_course}")
        print(f"   Date: {test_date}")
        print(f"   Status: present")
        print(f"   Marked by: {teacher.name} ({teacher.username})")
        
        # Create attendance record
        attendance = Attendance(
            student_id=student.id,
            student_srn=student.username,
            course_id=test_course,
            date=test_date,
            status='present',
            is_present=True,
            marked_by=teacher.username
        )
        
        try:
            from models import db
            db.session.add(attendance)
            db.session.commit()
            print("\n✅ Attendance record saved to database successfully!")
            print(f"   Record ID: {attendance.id}")
        except Exception as e:
            print(f"\n❌ Error saving attendance: {e}")
            return
        
        # Now retrieve the attendance record
        print(f"\n🔍 Retrieving attendance for student...")
        
        retrieved_records = Attendance.query.filter_by(
            student_id=student.id,
            date=test_date
        ).all()
        
        if retrieved_records:
            print(f"✅ Found {len(retrieved_records)} attendance record(s):")
            for record in retrieved_records:
                print(f"\n   Record Details:")
                print(f"   - ID: {record.id}")
                print(f"   - Student ID: {record.student_id}")
                print(f"   - Student SRN: {record.student_srn}")
                print(f"   - Course: {record.course_id}")
                print(f"   - Date: {record.date}")
                print(f"   - Status: {record.status}")
                print(f"   - Is Present: {record.is_present}")
                print(f"   - Marked By: {record.marked_by}")
                print(f"   - Updated At: {record.updated_at}")
        else:
            print(f"❌ No attendance records found for student!")
            return
        
        # Test view from student perspective (simulating view_attendance route)
        print(f"\n👁️  Simulating student dashboard view:")
        student_records = Attendance.query.filter_by(student_id=student.id).all()
        
        attendance_list = []
        for record in student_records:
            attendance_list.append({
                'date': record.date.isoformat() if record.date else '',
                'status': 'present' if record.is_present else 'absent',
                'course_id': record.course_id or 'N/A',
                'marked_by': record.marked_by or 'Unknown'
            })
        
        total_classes = len(attendance_list)
        present_count = sum(1 for a in attendance_list if a['status'] == 'present')
        absent_count = total_classes - present_count
        percentage = (present_count / total_classes * 100) if total_classes > 0 else 0
        
        print(f"\n   Attendance Summary:")
        print(f"   - Total Classes: {total_classes}")
        print(f"   - Present: {present_count}")
        print(f"   - Absent: {absent_count}")
        print(f"   - Percentage: {round(percentage, 2)}%")
        
        print(f"\n   Attendance Records:")
        for record in attendance_list:
            print(f"   - {record['date']}: {record['status']} (Course: {record['course_id']}, Marked by: {record['marked_by']})")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nAttendance is now properly saved and retrievable on the student dashboard.")

if __name__ == "__main__":
    test_attendance()
