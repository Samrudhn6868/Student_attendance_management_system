import sqlite3
import sys

db_path = 'src/instance/attendance.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the schema
cursor.execute("PRAGMA table_info(attendance)")
columns = cursor.fetchall()
print('Attendance table columns:')
for col in columns:
    print(f'  {col[1]}: {col[2]}')

# Get sample data
print('\nSample attendance records (first 5):')
cursor.execute('SELECT id, student_id, date, course_id, status, is_present FROM attendance LIMIT 5')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, Student: {row[1]}, Date: {row[2]}, Course: {row[3]}, Status: {row[4]}, Present: {row[5]}')

conn.close()
