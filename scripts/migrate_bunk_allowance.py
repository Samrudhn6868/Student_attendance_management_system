"""SAS-96: Migration script to add bunk allowance tables.

This script creates the necessary database tables for bunk allowance tracking.
Run this script after deploying the new code to set up the database schema.

Usage:
    python scripts/migrate_bunk_allowance.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app, db
from src.bunk_allowance_models import CourseConfig, StudentBunkAllowance
from src.bunk_allowance_service import BunkAllowanceService


def create_tables():
    """Create bunk allowance tables if they don't exist."""
    with app.app_context():
        print("Creating bunk allowance tables...")
        
        # Create tables
        db.create_all()
        
        print("✓ Tables created successfully")
        
        # Verify tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'course_config' in tables:
            print("✓ course_config table exists")
        else:
            print("✗ course_config table not found")
        
        if 'student_bunk_allowance' in tables:
            print("✓ student_bunk_allowance table exists")
        else:
            print("✗ student_bunk_allowance table not found")


def create_default_courses():
    """Create default course configurations."""
    with app.app_context():
        print("\nCreating default course configurations...")
        
        default_courses = [
            {
                'course_id': 'CS101',
                'course_name': 'Introduction to Computer Science',
                'total_classes': 60,
                'bunk_allowance_percentage': 25.0,
                'min_attendance_percentage': 75.0
            },
            {
                'course_id': 'CS201',
                'course_name': 'Data Structures and Algorithms',
                'total_classes': 60,
                'bunk_allowance_percentage': 20.0,
                'min_attendance_percentage': 80.0
            },
            {
                'course_id': 'MATH101',
                'course_name': 'Engineering Mathematics',
                'total_classes': 50,
                'bunk_allowance_percentage': 20.0,
                'min_attendance_percentage': 80.0
            },
        ]
        
        for course_data in default_courses:
            existing = CourseConfig.query.filter_by(
                course_id=course_data['course_id']
            ).first()
            
            if existing:
                print(f"  - {course_data['course_id']}: Already exists, skipping")
            else:
                config = CourseConfig(**course_data)
                db.session.add(config)
                print(f"  + {course_data['course_id']}: Created")
        
        db.session.commit()
        print("✓ Default courses created")


def sync_existing_attendance():
    """Sync existing attendance records to create bunk allowance entries."""
    with app.app_context():
        print("\nSyncing existing attendance records...")
        
        from src.models import Attendance
        
        # Get all unique student-course combinations
        combinations = db.session.query(
            Attendance.student_srn,
            Attendance.course_id
        ).distinct().all()
        
        print(f"Found {len(combinations)} student-course combinations")
        
        synced = 0
        errors = 0
        
        for student_srn, course_id in combinations:
            if not student_srn or not course_id:
                continue
            
            try:
                # Ensure course config exists
                BunkAllowanceService.get_or_create_course_config(course_id)
                
                # Update student bunk allowance
                BunkAllowanceService.update_student_bunk_allowance(
                    student_srn, course_id
                )
                synced += 1
                
                if synced % 10 == 0:
                    print(f"  Synced {synced} records...")
                
            except Exception as e:
                errors += 1
                print(f"  Error syncing {student_srn} - {course_id}: {e}")
        
        print(f"✓ Synced {synced} student-course records")
        if errors > 0:
            print(f"✗ {errors} errors occurred")


def display_summary():
    """Display summary of bunk allowance data."""
    with app.app_context():
        print("\n" + "="*60)
        print("BUNK ALLOWANCE SYSTEM SUMMARY")
        print("="*60)
        
        # Count courses
        course_count = CourseConfig.query.count()
        print(f"\nTotal Courses Configured: {course_count}")
        
        if course_count > 0:
            print("\nCourses:")
            for config in CourseConfig.query.all():
                print(f"  - {config.course_id}: {config.course_name}")
                print(f"    Total Classes: {config.total_classes}")
                print(f"    Bunk Allowance: {config.bunk_allowance_percentage}%")
                print(f"    Min Attendance: {config.min_attendance_percentage}%")
        
        # Count student records
        student_count = StudentBunkAllowance.query.count()
        print(f"\nTotal Student-Course Records: {student_count}")
        
        # Count critical students
        critical_count = StudentBunkAllowance.query.filter_by(
            is_attendance_critical=True
        ).count()
        print(f"Students with Critical Attendance: {critical_count}")
        
        print("\n" + "="*60)


def main():
    """Run the migration."""
    print("="*60)
    print("SAS-96: Bunk Allowance Migration")
    print("="*60)
    
    try:
        # Step 1: Create tables
        create_tables()
        
        # Step 2: Create default courses
        create_default_courses()
        
        # Step 3: Sync existing attendance (optional)
        print("\nDo you want to sync existing attendance records? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            sync_existing_attendance()
        else:
            print("Skipping attendance sync")
        
        # Step 4: Display summary
        display_summary()
        
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
