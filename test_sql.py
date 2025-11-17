import sys
sys.path.insert(0, 'src')

from main import app, db
from models import User, Attendance
from sqlalchemy import text

with app.app_context():
    # Test the SQL query
    student_id = 10  # Test Student
    
    records = db.session.execute(
        text("""
            SELECT id, student_id, date, is_present, updated_at
            FROM attendance
            WHERE student_id = :student_id
            ORDER BY date DESC
        """),
        {'student_id': student_id}
    ).fetchall()
    
    print(f"Found {len(records)} records for student {student_id}")
    
    for i, record in enumerate(records[:5]):
        record_id, sid, date, is_present, updated_at = record
        status = 'present' if is_present else 'absent'
        course_id = f"Course_{record_id}"
        
        print(f"{i+1}. Date: {date}, Status: {status}, Course: {course_id}, ID: {record_id}")
