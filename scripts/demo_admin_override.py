"""Demo script for testing admin override attendance functionality.

This script demonstrates how to:
1. Create test data (students and attendance records)
2. Perform admin overrides with reason notes
3. Verify the override was successful
4. View the audit trail

Usage:
    python scripts/demo_admin_override.py
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app, db, User
from src.models import Attendance


def create_test_data():
    """Create test users and attendance records."""
    print("\n" + "="*60)
    print("Creating Test Data")
    print("="*60)
    
    with app.app_context():
        # Create admin user
        admin = User.query.filter_by(username='ADMIN001').first()
        if not admin:
            admin = User()
            admin.username = 'ADMIN001'
            admin.name = 'Admin User'
            admin.is_faculty = True
            admin.role = 'admin'
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ Created admin user: ADMIN001")
        else:
            print("✓ Admin user already exists: ADMIN001")
        
        # Create student users
        students = []
        for i in range(1, 4):
            srn = f'PES1UG23CS00{i}'
            student = User.query.filter_by(username=srn).first()
            if not student:
                student = User()
                student.username = srn
                student.name = f'Student {i}'
                student.is_faculty = False
                student.role = 'student'
                student.set_password('student123')
                db.session.add(student)
                print(f"✓ Created student: {srn}")
            else:
                print(f"✓ Student already exists: {srn}")
            students.append(student)
        
        db.session.commit()
        
        # Create attendance records (some marked as absent)
        print("\nCreating attendance records...")
        today = date.today()
        
        for i, student in enumerate(students):
            for day_offset in range(5):
                attendance_date = today - timedelta(days=day_offset)
                
                # Check if record already exists
                existing = Attendance.query.filter_by(
                    student_id=student.id,
                    date=attendance_date
                ).first()
                
                if not existing:
                    # Mark some students as absent on certain days
                    is_present = not (i == 0 and day_offset in [1, 3])
                    
                    attendance = Attendance(
                        student_id=student.id,
                        date=attendance_date,
                        is_present=is_present
                    )
                    db.session.add(attendance)
        
        db.session.commit()
        print("✓ Attendance records created")
        
        return admin, students


def display_attendance_summary():
    """Display current attendance status."""
    print("\n" + "="*60)
    print("Current Attendance Status")
    print("="*60)
    
    with app.app_context():
        students = User.query.filter_by(is_faculty=False).all()
        
        for student in students:
            records = Attendance.query.filter_by(student_id=student.id).all()
            present_count = sum(1 for r in records if r.is_present)
            total_count = len(records)
            percentage = (present_count / total_count * 100) if total_count > 0 else 0
            
            print(f"\n{student.name} ({student.username})")
            print(f"  Total Classes: {total_count}")
            print(f"  Present: {present_count}")
            print(f"  Absent: {total_count - present_count}")
            print(f"  Attendance: {percentage:.1f}%")
            
            # Show records with override status
            for record in records:
                status = "Present" if record.is_present else "Absent"
                override_marker = " [OVERRIDDEN]" if record.is_overridden else ""
                print(f"    {record.date}: {status}{override_marker}")
                if record.is_overridden:
                    print(f"      Reason: {record.override_reason}")


def demo_override_attendance():
    """Demonstrate admin override functionality."""
    print("\n" + "="*60)
    print("Demonstrating Admin Override")
    print("="*60)
    
    with app.app_context():
        # Find an absent attendance record to override
        admin = User.query.filter_by(username='ADMIN001').first()
        absent_record = Attendance.query.filter_by(is_present=False, is_overridden=False).first()
        
        if not absent_record:
            print("✗ No absent records found to override")
            return
        
        student = User.query.get(absent_record.student_id)
        
        print(f"\nFound absent record:")
        print(f"  Student: {student.name} ({student.username})")
        print(f"  Date: {absent_record.date}")
        print(f"  Current Status: Absent")
        
        # Perform override
        print(f"\nPerforming override...")
        from datetime import datetime
        
        absent_record.is_present = True
        absent_record.is_overridden = True
        absent_record.override_reason = "Student provided medical certificate after class"
        absent_record.overridden_by = admin.id
        absent_record.override_timestamp = datetime.utcnow().isoformat()
        
        db.session.commit()
        
        print("✓ Override completed successfully!")
        print(f"\nOverride Details:")
        print(f"  Overridden by: {admin.name}")
        print(f"  New Status: Present")
        print(f"  Reason: {absent_record.override_reason}")
        print(f"  Timestamp: {absent_record.override_timestamp}")


def demo_multiple_overrides():
    """Demonstrate multiple overrides on the same record."""
    print("\n" + "="*60)
    print("Demonstrating Multiple Overrides")
    print("="*60)
    
    with app.app_context():
        # Find a present record to override multiple times
        admin = User.query.filter_by(username='ADMIN001').first()
        present_record = Attendance.query.filter_by(is_present=True, is_overridden=False).first()
        
        if not present_record:
            print("✗ No present records found")
            return
        
        student = User.query.get(present_record.student_id)
        
        print(f"\nOriginal record:")
        print(f"  Student: {student.name}")
        print(f"  Date: {present_record.date}")
        print(f"  Status: Present")
        
        # First override: present -> absent
        print(f"\nFirst override: Present -> Absent")
        from datetime import datetime
        
        present_record.is_present = False
        present_record.is_overridden = True
        present_record.override_reason = "System error, student was actually absent"
        present_record.overridden_by = admin.id
        present_record.override_timestamp = datetime.utcnow().isoformat()
        db.session.commit()
        print("✓ First override completed")
        
        # Second override: absent -> present
        print(f"\nSecond override: Absent -> Present")
        present_record.is_present = True
        present_record.override_reason = "Correction: Student provided late arrival proof"
        present_record.override_timestamp = datetime.utcnow().isoformat()
        db.session.commit()
        print("✓ Second override completed")
        
        print(f"\nFinal status:")
        print(f"  Status: Present")
        print(f"  Overridden: Yes")
        print(f"  Final Reason: {present_record.override_reason}")


def display_override_statistics():
    """Display statistics about overrides."""
    print("\n" + "="*60)
    print("Override Statistics")
    print("="*60)
    
    with app.app_context():
        total_records = Attendance.query.count()
        overridden_records = Attendance.query.filter_by(is_overridden=True).count()
        
        print(f"\nTotal Attendance Records: {total_records}")
        print(f"Overridden Records: {overridden_records}")
        
        if overridden_records > 0:
            percentage = (overridden_records / total_records * 100)
            print(f"Override Rate: {percentage:.1f}%")
            
            print(f"\nOverridden Records Details:")
            overridden = Attendance.query.filter_by(is_overridden=True).all()
            for record in overridden:
                student = User.query.get(record.student_id)
                admin = User.query.get(record.overridden_by)
                status = "Present" if record.is_present else "Absent"
                
                print(f"\n  Record ID: {record.id}")
                print(f"  Student: {student.name if student else 'Unknown'}")
                print(f"  Date: {record.date}")
                print(f"  Current Status: {status}")
                print(f"  Reason: {record.override_reason}")
                print(f"  Overridden By: {admin.name if admin else 'Unknown'}")
                print(f"  Timestamp: {record.override_timestamp}")


def main():
    """Run the demo."""
    print("\n" + "="*60)
    print("Admin Override Attendance - Demo Script")
    print("="*60)
    
    try:
        # Step 1: Create test data
        admin, students = create_test_data()
        
        # Step 2: Display initial attendance
        display_attendance_summary()
        
        # Step 3: Demonstrate single override
        demo_override_attendance()
        
        # Step 4: Demonstrate multiple overrides
        demo_multiple_overrides()
        
        # Step 5: Display updated attendance
        display_attendance_summary()
        
        # Step 6: Show override statistics
        display_override_statistics()
        
        print("\n" + "="*60)
        print("Demo Completed Successfully!")
        print("="*60)
        print("\nYou can now test the API endpoints:")
        print("  - PUT /attendance/override")
        print("  - PUT /attendance/api/override")
        print("\nLogin as ADMIN001 (password: admin123) to test the web interface.")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
