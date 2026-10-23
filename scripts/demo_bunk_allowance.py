"""Quick demo script for SAS-96: Bunk Allowance Feature.

This script demonstrates the bunk allowance feature functionality.
Run this after setting up the database.

Usage:
    python scripts/demo_bunk_allowance.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
from src.main import app, db
from src.models import User, Attendance
from src.bunk_allowance_models import CourseConfig, StudentBunkAllowance
from src.bunk_allowance_service import BunkAllowanceService


def setup_demo_data():
    """Set up demo data for bunk allowance demonstration."""
    with app.app_context():
        print("Setting up demo data...")
        
        # Create demo users
        demo_users = [
            {
                'username': 'PES1UG23CS001',
                'name': 'Alice Johnson',
                'password': 'demo123',
                'is_faculty': False,
                'role': 'student'
            },
            {
                'username': 'PES1UG23CS002',
                'name': 'Bob Smith',
                'password': 'demo123',
                'is_faculty': False,
                'role': 'student'
            },
            {
                'username': 'FAC001',
                'name': 'Prof. Davis',
                'password': 'demo123',
                'is_faculty': True,
                'role': 'teacher'
            },
        ]
        
        for user_data in demo_users:
            existing = User.query.filter_by(username=user_data['username']).first()
            if not existing:
                user = User(
                    username=user_data['username'],
                    name=user_data['name'],
                    is_faculty=user_data['is_faculty'],
                    role=user_data['role']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                print(f"  Created user: {user_data['username']}")
        
        db.session.commit()
        
        # Create demo courses
        demo_courses = [
            {
                'course_id': 'CS101',
                'course_name': 'Introduction to Programming',
                'total_classes': 60,
                'bunk_allowance_percentage': 25.0,
                'min_attendance_percentage': 75.0
            },
            {
                'course_id': 'MATH101',
                'course_name': 'Calculus',
                'total_classes': 50,
                'bunk_allowance_percentage': 20.0,
                'min_attendance_percentage': 80.0
            },
        ]
        
        for course_data in demo_courses:
            config = BunkAllowanceService.get_or_create_course_config(**course_data)
            print(f"  Created/Updated course: {course_data['course_id']}")
        
        # Create demo attendance records
        print("\nCreating attendance records...")
        
        # Alice - Good attendance (85%)
        for i in range(40):
            status = 'present' if i % 7 != 0 else 'absent'
            record = Attendance(
                student_srn='PES1UG23CS001',
                course_id='CS101',
                date=datetime.now().date() - timedelta(days=40-i),
                status=status,
                marked_by='FAC001'
            )
            db.session.add(record)
        
        # Bob - Critical attendance (70%)
        for i in range(40):
            status = 'present' if i < 28 else 'absent'
            record = Attendance(
                student_srn='PES1UG23CS002',
                course_id='CS101',
                date=datetime.now().date() - timedelta(days=40-i),
                status=status,
                marked_by='FAC001'
            )
            db.session.add(record)
        
        db.session.commit()
        print("  Created 80 attendance records")


def demonstrate_student_view():
    """Demonstrate student viewing their bunk allowance."""
    with app.app_context():
        print("\n" + "="*60)
        print("STUDENT VIEW - Alice (Good Attendance)")
        print("="*60)
        
        # Get Alice's data
        data = BunkAllowanceService.get_student_bunk_allowance('PES1UG23CS001', 'CS101')
        
        print(f"\nStudent: PES1UG23CS001")
        print(f"Course: {data['course_id']}")
        print(f"\nCurrent Statistics:")
        print(f"  Total Classes Held: {data['total_classes_held']}")
        print(f"  Classes Attended: {data['classes_attended']}")
        print(f"  Classes Missed: {data['classes_missed']}")
        print(f"  Attendance Percentage: {data['current_attendance_percentage']}%")
        print(f"\nBunk Allowance:")
        print(f"  Remaining Bunks: {data['remaining_bunk_allowance']}")
        print(f"  Status: {'⚠️ CRITICAL' if data['is_attendance_critical'] else '✓ Good'}")
        
        # Get detailed breakdown
        breakdown = BunkAllowanceService.get_remaining_classes_breakdown('PES1UG23CS001', 'CS101')
        
        print(f"\nRemaining Classes:")
        print(f"  Classes Left: {breakdown['remaining_classes']['classes_remaining']}")
        print(f"  Safe Bunks Remaining: {breakdown['remaining_classes']['safe_bunks_remaining']}")
        
        print(f"\nProjections:")
        print(f"  If attend all remaining: {breakdown['projections']['if_attend_all_remaining']}%")
        print(f"  If use all bunks: {breakdown['projections']['if_use_all_bunks']}%")
        
        print("\n" + "="*60)
        print("STUDENT VIEW - Bob (Critical Attendance)")
        print("="*60)
        
        # Get Bob's data
        data = BunkAllowanceService.get_student_bunk_allowance('PES1UG23CS002', 'CS101')
        
        print(f"\nStudent: PES1UG23CS002")
        print(f"Course: {data['course_id']}")
        print(f"\nCurrent Statistics:")
        print(f"  Total Classes Held: {data['total_classes_held']}")
        print(f"  Classes Attended: {data['classes_attended']}")
        print(f"  Classes Missed: {data['classes_missed']}")
        print(f"  Attendance Percentage: {data['current_attendance_percentage']}%")
        print(f"\nBunk Allowance:")
        print(f"  Remaining Bunks: {data['remaining_bunk_allowance']}")
        print(f"  Status: {'⚠️ CRITICAL' if data['is_attendance_critical'] else '✓ Good'}")
        
        breakdown = BunkAllowanceService.get_remaining_classes_breakdown('PES1UG23CS002', 'CS101')
        print(f"\nProjections:")
        print(f"  If attend all remaining: {breakdown['projections']['if_attend_all_remaining']}%")
        print(f"  If use all bunks: {breakdown['projections']['if_use_all_bunks']}%")


def demonstrate_faculty_view():
    """Demonstrate faculty monitoring students."""
    with app.app_context():
        print("\n" + "="*60)
        print("FACULTY VIEW - Course Overview")
        print("="*60)
        
        # Get all students in course
        students = BunkAllowanceService.get_all_students_bunk_status('CS101')
        
        print(f"\nCourse: CS101")
        print(f"Total Students: {len(students)}")
        
        print("\nStudent Attendance Summary:")
        print("-" * 80)
        print(f"{'SRN':<20} {'Attended':<10} {'Missed':<10} {'Attendance':<12} {'Status':<10}")
        print("-" * 80)
        
        for student in students:
            status = '⚠️ CRITICAL' if student['is_attendance_critical'] else '✓ Good'
            print(f"{student['student_srn']:<20} "
                  f"{student['classes_attended']:<10} "
                  f"{student['classes_missed']:<10} "
                  f"{student['current_attendance_percentage']:<12.2f}% "
                  f"{status:<10}")
        
        # Get critical students
        critical = BunkAllowanceService.get_critical_students('CS101')
        
        print(f"\n⚠️  Critical Students Requiring Attention: {len(critical)}")
        if critical:
            for student in critical:
                print(f"  - {student['student_srn']}: {student['current_attendance_percentage']:.2f}%")


def demonstrate_api_usage():
    """Demonstrate API endpoint usage."""
    print("\n" + "="*60)
    print("API ENDPOINT EXAMPLES")
    print("="*60)
    
    print("\nStudent Endpoints:")
    print("  GET /api/bunk-allowance/student/PES1UG23CS001")
    print("  GET /api/bunk-allowance/student/PES1UG23CS001/course/CS101")
    print("  GET /api/bunk-allowance/breakdown/PES1UG23CS001/CS101")
    
    print("\nFaculty Endpoints:")
    print("  GET /api/bunk-allowance/course/CS101/students")
    print("  GET /api/bunk-allowance/critical?course_id=CS101")
    print("  POST /api/bunk-allowance/course/CS101/refresh")
    
    print("\nAdmin Endpoints:")
    print("  POST /api/bunk-allowance/course")
    print("  GET /api/bunk-allowance/course/CS101")
    
    print("\nHealth Check:")
    print("  GET /api/bunk-allowance/health")


def main():
    """Run the demonstration."""
    print("="*60)
    print("SAS-96: Bunk Allowance Feature Demonstration")
    print("="*60)
    
    try:
        # Setup demo data
        setup_demo_data()
        
        # Demonstrate different views
        demonstrate_student_view()
        demonstrate_faculty_view()
        demonstrate_api_usage()
        
        print("\n" + "="*60)
        print("✓ Demonstration completed successfully!")
        print("="*60)
        print("\nNext Steps:")
        print("1. Start the Flask app: python src/main.py")
        print("2. Login with demo credentials:")
        print("   - Student: PES1UG23CS001 / demo123")
        print("   - Faculty: FAC001 / demo123")
        print("3. Access API endpoints or use the web interface")
        print("\nFor more information, see docs/SAS-96-BUNK-ALLOWANCE.md")
        
    except Exception as e:
        print(f"\n✗ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
