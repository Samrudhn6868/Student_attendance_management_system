"""Add role column to user table and populate it."""
import sqlite3

# Connect to database
conn = sqlite3.connect('instance/attendance.db')
cursor = conn.cursor()

# Check if role column exists
cursor.execute('PRAGMA table_info(user)')
cols = [row[1] for row in cursor.fetchall()]

if 'role' not in cols:
    print('Adding role column...')
    cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'student'")
    conn.commit()
    print('✓ Added role column')
    
    # Update roles based on is_faculty
    print('Updating role values...')
    cursor.execute("UPDATE user SET role = 'teacher' WHERE is_faculty = 1")
    cursor.execute("UPDATE user SET role = 'student' WHERE is_faculty = 0 OR is_faculty IS NULL")
    conn.commit()
    print('✓ Updated role values')
else:
    print('✓ Role column already exists')
    
# Verify
cursor.execute('SELECT username, role, is_faculty FROM user')
print('\nCurrent user roles:')
for row in cursor.fetchall():
    print(f'  {row[0]}: role={row[1]}, is_faculty={row[2]}')

conn.close()
print('\n✓ Migration complete!')
