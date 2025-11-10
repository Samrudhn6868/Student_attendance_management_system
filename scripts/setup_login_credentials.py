import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User

with app.app_context():
    users = User.query.all()
    print("\n" + "="*70)
    print("CURRENT USERS IN DATABASE")
    print("="*70)
    for u in users:
        role = getattr(u, 'role', 'student' if not u.is_faculty else 'teacher')
        print(f"\n{u.id}. Username: {u.username}")
        print(f"   Name: {u.name}")
        print(f"   Role: {role}")
        print(f"   Is Faculty: {u.is_faculty}")
    
    print("\n" + "="*70)
    print("UPDATING ROLES & CREATING TEST USERS")
    print("="*70)
    
    # Update existing users with roles
    for u in users:
        if not hasattr(u, 'role') or u.role is None:
            if u.is_faculty:
                u.role = 'teacher'
                print(f"✅ Updated {u.username} to role: teacher")
            else:
                u.role = 'student'
                print(f"✅ Updated {u.username} to role: student")
    
    # Try to create admin user
    admin = User.query.filter_by(username='admin1').first()
    if not admin:
        admin = User(username='admin1', name='Admin User', is_faculty=True, role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print("✅ Created admin1 user")
    else:
        admin.role = 'admin'
        print("✅ Updated admin1 to admin role")
    
    # Try to create easy test users
    student = User.query.filter_by(username='student').first()
    if not student:
        student = User(username='student', name='Test Student', is_faculty=False, role='student')
        student.set_password('student')
        db.session.add(student)
        print("✅ Created student user")
    
    teacher = User.query.filter_by(username='teacher').first()
    if not teacher:
        teacher = User(username='teacher', name='Test Teacher', is_faculty=True, role='teacher')
        teacher.set_password('teacher')
        db.session.add(teacher)
        print("✅ Created teacher user")
    
    admin2 = User.query.filter_by(username='admin').first()
    if not admin2:
        admin2 = User(username='admin', name='Test Admin', is_faculty=True, role='admin')
        admin2.set_password('admin')
        db.session.add(admin2)
        print("✅ Created admin user")
    
    db.session.commit()
    
    print("\n" + "="*70)
    print("LOGIN CREDENTIALS FOR TESTING")
    print("="*70)
    print("\n📝 STUDENT LOGIN (Can only view attendance):")
    print("   Username: PES1RR20CS001  OR  student")
    print("   Password: [check with admin]  OR  student")
    
    print("\n👨‍🏫 TEACHER LOGIN (Can view & mark attendance):")
    print("   Username: FAC001  OR  teacher")
    print("   Password: [check with admin]  OR  teacher")
    
    print("\n🔑 ADMIN LOGIN (Can view, mark & override attendance):")
    print("   Username: admin1  OR  admin")
    print("   Password: admin123  OR  admin")
    
    print("\n" + "="*70)
    print("HOW TO TEST ON WEBSITE")
    print("="*70)
    print("\n1. Open browser: http://127.0.0.1:5000/login")
    print("2. Login with credentials above")
    print("3. After login, test these URLs:")
    print("\n   ✅ ALL USERS can access:")
    print("      http://127.0.0.1:5000/attendance/view")
    print("\n   ✅ TEACHER & ADMIN can access:")
    print("      http://127.0.0.1:5000/attendance/mark")
    print("      (Students will get 403 Forbidden)")
    print("\n   ✅ ONLY ADMIN can access:")
    print("      http://127.0.0.1:5000/attendance/override")
    print("      (Students & Teachers will get 403 Forbidden)")
    print()
