"""
Database Setup Script for Student Attendance System
Run this script after pulling the repository to set up test users.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User

def setup_database():
    """Initialize database with test users."""
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        print("\n" + "="*70)
        print("STUDENT ATTENDANCE SYSTEM - DATABASE SETUP")
        print("="*70)
        print()
        
        # Define test users
        test_users = [
            {
                'username': 'admin_user',
                'password': 'AdminPass123!',
                'name': 'Admin User',
                'role': 'admin',
                'is_faculty': True
            },
            {
                'username': 'teacher_user',
                'password': 'TeacherPass123!',
                'name': 'Teacher User',
                'role': 'teacher',
                'is_faculty': True
            },
            {
                'username': 'student_user',
                'password': 'StudentPass123!',
                'name': 'Student User',
                'role': 'student',
                'is_faculty': False
            }
        ]
        
        created = 0
        updated = 0
        
        for user_data in test_users:
            existing_user = User.query.filter_by(username=user_data['username']).first()
            
            if existing_user:
                # Update existing user
                existing_user.role = user_data['role']
                existing_user.name = user_data['name']
                existing_user.is_faculty = user_data['is_faculty']
                existing_user.set_password(user_data['password'])
                # Reset account lock status
                existing_user.failed_login_attempts = 0
                existing_user.account_locked = False
                existing_user.locked_at = None
                print(f"✅ Updated: {user_data['username']} ({user_data['role']})")
                updated += 1
            else:
                # Create new user
                new_user = User(
                    username=user_data['username'],
                    name=user_data['name'],
                    role=user_data['role'],
                    is_faculty=user_data['is_faculty']
                )
                new_user.set_password(user_data['password'])
                db.session.add(new_user)
                print(f"✅ Created: {user_data['username']} ({user_data['role']})")
                created += 1
        
        db.session.commit()
        
        print()
        print("="*70)
        print(f"SETUP COMPLETE: {created} created, {updated} updated")
        print("="*70)
        print()
        print("📋 TEST CREDENTIALS:")
        print("─"*70)
        print("| Username      | Password         | Role    | Capabilities    |")
        print("─"*70)
        print("| admin_user    | AdminPass123!    | admin   | Full access     |")
        print("| teacher_user  | TeacherPass123!  | teacher | View + Mark     |")
        print("| student_user  | StudentPass123!  | student | View only       |")
        print("─"*70)
        print()
        print("🌐 To start the application:")
        print("   python src/main.py")
        print()
        print("🔗 Then visit:")
        print("   http://127.0.0.1:5000/login")
        print()
        print("⚠️  Security Features:")
        print("   - Accounts lock after 3 failed login attempts")
        print("   - Auto-unlock after 30 minutes")
        print("   - Passwords encrypted with bcrypt")
        print()
        print("="*70)
        print()


if __name__ == '__main__':
    try:
        setup_database()
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        print("\nMake sure you have:")
        print("1. Installed requirements: pip install -r requirements.txt")
        print("2. Created instance directory: mkdir -p src/instance")
        sys.exit(1)
