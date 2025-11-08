"""Quick Python commands to create test users.

Run this with: python -i scripts/quick_create_users.py
Or copy-paste into Python interactive shell.
"""

commands = """
# Run these commands in Python interactive mode:
import sys
sys.path.insert(0, 'src')
from main import app, db, User

with app.app_context():
    # Student user
    s = User(username='student1', name='John Doe', is_faculty=False, role='student')
    s.set_password('student123')
    db.session.add(s)
    
    # Teacher user
    t = User(username='teacher1', name='Prof. Smith', is_faculty=True, role='teacher')
    t.set_password('teacher123')
    db.session.add(t)
    
    # Admin user
    a = User(username='admin1', name='Admin User', is_faculty=True, role='admin')
    a.set_password('admin123')
    db.session.add(a)
    
    db.session.commit()
    print('✅ Users created successfully!')
"""

print(commands)
