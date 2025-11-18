"""Seed realistic demo data for testing and demonstration.

Creates a comprehensive dataset that looks like a real college attendance system:
- 40 students with realistic names
- 8 teachers across different departments
- 2 admin users
- 5 courses with proper course codes
- 50 days of attendance history
- Mix of attendance patterns (good, average, at-risk students)

Usage:
    python tools/seed_demo_data.py [--reset] [--students N] [--days N]
"""

import os
import sys
import argparse
from datetime import datetime, timedelta, date
import random

# Add src to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
sys.path.insert(0, SRC_DIR)

os.environ['FLASK_ENV'] = 'development'
os.environ['DISABLE_DEMO_SEED'] = '1'

from main import app, db
from models import User, Attendance


# Realistic student names
STUDENT_NAMES = [
    "Aarav Sharma", "Vivaan Patel", "Aditya Kumar", "Vihaan Singh",
    "Arjun Reddy", "Sai Krishna", "Reyansh Gupta", "Ayaan Khan",
    "Krishna Iyer", "Ishaan Nair", "Shaurya Rao", "Atharv Desai",
    "Pranav Mehta", "Dhruv Joshi", "Kabir Verma", "Arnav Shah",
    "Veer Malhotra", "Anaya Shetty", "Diya Kapoor", "Aadhya Pillai",
    "Saanvi Agarwal", "Anvi Menon", "Navya Bhat", "Pari Kulkarni",
    "Myra Bhatt", "Aanya Rao", "Sara Nambiar", "Kiara Hegde",
    "Ira Srinivas", "Riya Patil", "Avni Reddy", "Shanaya Kumar",
    "Aaradhya Singh", "Zara Iyer", "Aditi Sharma", "Prisha Naik",
    "Ananya Menon", "Kavya Reddy", "Mishka Patel", "Tara Gupta"
]

# Teacher names and departments
TEACHERS = [
    ("Dr. Rajesh Kumar", "Computer Science"),
    ("Prof. Priya Sharma", "Computer Science"),
    ("Dr. Amit Patel", "Mathematics"),
    ("Prof. Sunita Reddy", "Physics"),
    ("Dr. Vikram Singh", "Electronics"),
    ("Prof. Anjali Nair", "Computer Science"),
    ("Dr. Suresh Iyer", "Mathematics"),
    ("Prof. Kavita Desai", "Physics")
]

# Courses with realistic codes and names
COURSES = [
    ("UE20CS101", "Data Structures"),
    ("UE20CS201", "Algorithms"),
    ("UE20CS301", "Database Systems"),
    ("UE20MA101", "Linear Algebra"),
    ("UE20PH101", "Physics Lab")
]

# Admin users
ADMINS = [
    ("admin", "System Administrator"),
    ("hod_cs", "Dr. Head Of Department")
]


class DemoDataSeeder:
    """Seed comprehensive demo data for the application."""
    
    def __init__(self, num_students=40, num_days=50, reset=False):
        """Initialize seeder with parameters.
        
        Args:
            num_students: Number of students to create (default: 40)
            num_days: Number of days of attendance history (default: 50)
            reset: Whether to reset database before seeding
        """
        self.num_students = min(num_students, len(STUDENT_NAMES))
        self.num_days = num_days
        self.reset = reset
        self.app = app
        
        self.students = []
        self.teachers = []
        self.admins = []
        
    def reset_database(self):
        """Drop and recreate all tables."""
        print("🗑️  Resetting database...")
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            print("✓ Database reset complete")
    
    def create_users(self):
        """Create all users (students, teachers, admins)."""
        print(f"\n👥 Creating users...")
        
        with self.app.app_context():
            # Create students
            print(f"   Creating {self.num_students} students...")
            for i in range(self.num_students):
                srn = f"PES1UG20CS{i+1:03d}"
                student = User(
                    username=srn,
                    name=STUDENT_NAMES[i],
                    is_faculty=False,
                    role='student'
                )
                student.set_password('student123')
                db.session.add(student)
                self.students.append(student)
            
            # Create teachers
            print(f"   Creating {len(TEACHERS)} teachers...")
            for i, (name, dept) in enumerate(TEACHERS):
                username = f"teacher{i+1}"
                teacher = User(
                    username=username,
                    name=name,
                    is_faculty=True,
                    role='teacher'
                )
                teacher.set_password('teacher123')
                db.session.add(teacher)
                self.teachers.append(teacher)
            
            # Create admins
            print(f"   Creating {len(ADMINS)} admins...")
            for username, name in ADMINS:
                admin = User(
                    username=username,
                    name=name,
                    is_faculty=True,
                    role='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                self.admins.append(admin)
            
            db.session.commit()
            
            # Refresh to get IDs
            self.students = User.query.filter_by(role='student').all()
            self.teachers = User.query.filter_by(role='teacher').all()
            self.admins = User.query.filter_by(role='admin').all()
            
            print(f"✓ Created {len(self.students)} students, {len(self.teachers)} teachers, {len(self.admins)} admins")
    
    def create_attendance_records(self):
        """Create realistic attendance records."""
        print(f"\n📅 Creating attendance records for {self.num_days} days...")
        
        with self.app.app_context():
            start_date = date.today() - timedelta(days=self.num_days)
            
            # Define attendance patterns for realism
            # 70% students have good attendance (80-95%)
            # 20% students have average attendance (70-80%)
            # 10% students are at-risk (<70%)
            
            total_records = 0
            
            for student in self.students:
                # Determine student's attendance pattern
                pattern_roll = random.random()
                if pattern_roll < 0.70:
                    # Good student (80-95% attendance)
                    attendance_rate = random.uniform(0.80, 0.95)
                elif pattern_roll < 0.90:
                    # Average student (70-80% attendance)
                    attendance_rate = random.uniform(0.70, 0.80)
                else:
                    # At-risk student (<70% attendance)
                    attendance_rate = random.uniform(0.50, 0.70)
                
                # Create attendance for each day and course
                for day_offset in range(self.num_days):
                    current_date = start_date + timedelta(days=day_offset)
                    
                    # Skip weekends (Saturday=5, Sunday=6)
                    if current_date.weekday() >= 5:
                        continue
                    
                    # Each student has 1-2 classes per day
                    num_classes = random.choice([1, 1, 2])  # More 1-class days
                    selected_courses = random.sample(COURSES, num_classes)
                    
                    for course_code, course_name in selected_courses:
                        # Determine if student is present based on their pattern
                        is_present = random.random() < attendance_rate
                        
                        # Select random teacher
                        teacher = random.choice(self.teachers)
                        
                        attendance = Attendance(
                            student_id=student.id,
                            course_id=course_code,
                            date=current_date,
                            status='present' if is_present else 'absent',
                            marked_by=teacher.name
                        )
                        db.session.add(attendance)
                        total_records += 1
                
                # Commit every 100 records for performance
                if total_records % 100 == 0:
                    db.session.commit()
                    print(f"   Progress: {total_records} records created...", end='\r')
            
            db.session.commit()
            print(f"\n✓ Created {total_records:,} attendance records")
    
    def create_sample_requests(self):
        """Create sample correction requests for demo."""
        print(f"\n📝 Creating sample correction requests...")
        
        with self.app.app_context():
            from models import AttendanceCorrectionRequest
            
            # Create 5-10 sample requests with different statuses
            num_requests = random.randint(5, 10)
            created = 0
            
            for _ in range(num_requests):
                student = random.choice(self.students[:10])  # First 10 students
                
                # Find a recent absent record
                recent_absent = Attendance.query.filter_by(
                    student_id=student.id,
                    status='absent'
                ).order_by(Attendance.date.desc()).first()
                
                if recent_absent:
                    # Random submission time in last 2 days
                    submitted_at = datetime.now() - timedelta(
                        hours=random.randint(1, 48)
                    )
                    
                    # Random status
                    status = random.choice([
                        'pending', 'pending', 'pending',  # More pending
                        'approved', 'rejected', 'cancelled'
                    ])
                    
                    request = AttendanceCorrectionRequest(
                        student_id=student.id,
                        student_name=student.name,
                        course_id=recent_absent.course_id,
                        date=recent_absent.date,
                        current_status='absent',
                        requested_status='present',
                        reason=random.choice([
                            "I was present but not marked",
                            "Medical emergency, have certificate",
                            "Biometric system error",
                            "Was late but attended full class"
                        ]),
                        status=status,
                        submitted_at=submitted_at
                    )
                    
                    if status in ['approved', 'rejected']:
                        request.reviewed_at = submitted_at + timedelta(hours=random.randint(2, 24))
                    
                    db.session.add(request)
                    created += 1
            
            db.session.commit()
            print(f"✓ Created {created} sample correction requests")
    
    def print_summary(self):
        """Print summary of created data."""
        with self.app.app_context():
            total_students = User.query.filter_by(role='student').count()
            total_teachers = User.query.filter_by(role='teacher').count()
            total_admins = User.query.filter_by(role='admin').count()
            total_attendance = Attendance.query.count()
            
            print("\n" + "="*60)
            print("📊 DEMO DATA SUMMARY")
            print("="*60)
            print(f"👨‍🎓 Students:          {total_students}")
            print(f"👨‍🏫 Teachers:          {total_teachers}")
            print(f"👔 Admins:            {total_admins}")
            print(f"📚 Courses:           {len(COURSES)}")
            print(f"📅 Attendance Records: {total_attendance:,}")
            print(f"📆 Days of History:   {self.num_days}")
            print("="*60)
            print("\n🔑 LOGIN CREDENTIALS:")
            print("-" * 60)
            print("\nStudents (all use password: student123):")
            for i in range(min(5, total_students)):
                student = User.query.filter_by(role='student').offset(i).first()
                print(f"   {student.username:20s} - {student.name}")
            if total_students > 5:
                print(f"   ... and {total_students - 5} more students")
            
            print("\nTeachers (all use password: teacher123):")
            for teacher in User.query.filter_by(role='teacher').all():
                print(f"   {teacher.username:20s} - {teacher.name}")
            
            print("\nAdmins (all use password: admin123):")
            for admin in User.query.filter_by(role='admin').all():
                print(f"   {admin.username:20s} - {admin.name}")
            
            print("\n" + "="*60)
            print("✅ Demo data ready! Start the app:")
            print("   python src/main.py")
            print("="*60)
    
    def seed(self):
        """Run the complete seeding process."""
        print("🌱 Starting demo data seeding process...")
        print(f"   Students: {self.num_students}")
        print(f"   Days: {self.num_days}")
        print(f"   Reset DB: {self.reset}")
        
        if self.reset:
            self.reset_database()
        
        self.create_users()
        self.create_attendance_records()
        
        try:
            self.create_sample_requests()
        except Exception as e:
            print(f"⚠️  Could not create correction requests: {e}")
        
        self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Seed realistic demo data for PESU Attendance System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: 40 students, 50 days
  python tools/seed_demo_data.py
  
  # Reset database and create fresh data
  python tools/seed_demo_data.py --reset
  
  # Create 20 students with 30 days of history
  python tools/seed_demo_data.py --students 20 --days 30
  
  # Full reset with custom numbers
  python tools/seed_demo_data.py --reset --students 100 --days 60
        """
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database before seeding (WARNING: deletes all data)'
    )
    parser.add_argument(
        '--students',
        type=int,
        default=40,
        help='Number of students to create (default: 40, max: 40)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=50,
        help='Number of days of attendance history (default: 50)'
    )
    
    args = parser.parse_args()
    
    # Confirmation for reset
    if args.reset:
        print("⚠️  WARNING: This will delete ALL existing data!")
        response = input("Are you sure you want to reset the database? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
    
    seeder = DemoDataSeeder(
        num_students=args.students,
        num_days=args.days,
        reset=args.reset
    )
    
    seeder.seed()


if __name__ == '__main__':
    main()
