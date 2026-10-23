"""Create test users with different roles for SAS-88 RBAC testing.

This script creates three test users:
1. Student user
2. Teacher user  
3. Admin user
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User


def create_test_users():
    """Create test users with different roles."""
    with app.app_context():
        # Check if users already exist
        existing_student = User.query.filter_by(username='student1').first()
        existing_teacher = User.query.filter_by(username='teacher1').first()
        existing_admin = User.query.filter_by(username='admin1').first()
        
        print("="*70)
        print("Creating Test Users for SAS-88 RBAC")
        print("="*70)
        
        # Create student user
        if not existing_student:
            student = User(
                username='student1',
                name='John Doe (Student)',
                is_faculty=False,
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
            print("\n✅ Created STUDENT user:")
            print(f"   Username: student1")
            print(f"   Password: student123")
            print(f"   Role: student")
        else:
            print("\n⚠️  Student user already exists")
            print(f"   Username: student1")
            print(f"   Password: student123")
        
        # Create teacher user
        if not existing_teacher:
            teacher = User(
                username='teacher1',
                name='Prof. Sarah Smith (Teacher)',
                is_faculty=True,
                role='teacher'
            )
            teacher.set_password('teacher123')
            db.session.add(teacher)
            print("\n✅ Created TEACHER user:")
            print(f"   Username: teacher1")
            print(f"   Password: teacher123")
            print(f"   Role: teacher")
        else:
            print("\n⚠️  Teacher user already exists")
            print(f"   Username: teacher1")
            print(f"   Password: teacher123")
        
        # Create admin user
        if not existing_admin:
            admin = User(
                username='admin1',
                name='Admin User (Administrator)',
                is_faculty=True,
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("\n✅ Created ADMIN user:")
            print(f"   Username: admin1")
            print(f"   Password: admin123")
            print(f"   Role: admin")
        else:
            print("\n⚠️  Admin user already exists")
            print(f"   Username: admin1")
            print(f"   Password: admin123")
        
        # Commit changes
        db.session.commit()
        
        print("\n" + "="*70)
        print("Test Users Ready!")
        print("="*70)
        print("\n🌐 To test on the website:")
        print(f"   1. Open browser: http://127.0.0.1:5000/login")
        print(f"   2. Login with one of the credentials above")
        print(f"   3. After login, visit:")
        print(f"      - http://127.0.0.1:5000/attendance/view")
        print(f"      - http://127.0.0.1:5000/attendance/mark (teacher/admin only)")
        print(f"      - http://127.0.0.1:5000/attendance/override (admin only)")
        print(f"\n📝 You should see:")
        print(f"   - Students: Can only access /attendance/view")
        print(f"   - Teachers: Can access /view and /mark")
        print(f"   - Admins: Can access all three endpoints")
        print()


if __name__ == '__main__':
    create_test_users()
