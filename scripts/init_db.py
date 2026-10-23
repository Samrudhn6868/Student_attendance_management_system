#!/usr/bin/env python
"""Initialize the database with test users."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import Flask and create app FIRST
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

# Create app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'src', 'instance')
os.makedirs(instance_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "attendance.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import db and User from models
from models import db, User

# Initialize db with app
db.init_app(app)

with app.app_context():
    # Create tables
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
        },
        {
            'username': 'PES1UG21CS001',
            'password': 'Student123!',
            'name': 'Aarav Patel',
            'role': 'student',
            'is_faculty': False
        },
        {
            'username': 'PES1UG21CS002',
            'password': 'Student123!',
            'name': 'Bhavna Sharma',
            'role': 'student',
            'is_faculty': False
        },
        {
            'username': 'PES1UG21CS003',
            'password': 'Student123!',
            'name': 'Chirag Verma',
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
    print("-"*70)
    print("Username          | Password        | Role    | Name")
    print("-"*70)
    
    all_users = User.query.all()
    for user in all_users:
        print(f"{user.username:<17} | {'*'*15} | {user.role:<7} | {user.name}")
    
    print("-"*70)
    print()
    print("🌐 To start the application:")
    print("   python src/main.py")
    print()
    print("🔗 Then visit:")
    print("   http://127.0.0.1:5000/login")
    print()
