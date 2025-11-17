"""Migration script to add attendance correction request table.

This script adds the AttendanceCorrectionRequest table to the database.
If the table already exists, it will drop and recreate it with the new schema.
"""

import os
import sys
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db
from models import AttendanceCorrectionRequest

def migrate_correction_request_table():
    """Create or update the attendance correction request table."""
    
    print("\n" + "="*70)
    print("ATTENDANCE CORRECTION REQUEST TABLE MIGRATION")
    print("="*70)
    
    with app.app_context():
        # Get database path
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        print(f"\nDatabase: {db_path}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='attendance_correction_request'"
        )
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("✓ Table 'attendance_correction_request' already exists")
            
            # Check if columns exist
            cursor.execute("PRAGMA table_info(attendance_correction_request)")
            columns = {col[1] for col in cursor.fetchall()}
            
            print("\nExisting columns:")
            for col in sorted(columns):
                print(f"  • {col}")
            
            # Check for missing columns
            required_columns = {
                'id', 'student_id', 'student_name', 'course_id', 'date',
                'current_status', 'requested_status', 'reason', 'status',
                'submitted_at', 'reviewed_at', 'reviewed_by', 'admin_notes'
            }
            
            missing_columns = required_columns - columns
            
            if missing_columns:
                print(f"\n⚠ Missing columns: {missing_columns}")
                print("\nDropping and recreating table with correct schema...")
                
                cursor.execute("DROP TABLE attendance_correction_request")
                conn.commit()
                
                print("✓ Table dropped")
        else:
            print("✓ Table does not exist, will be created")
        
        conn.close()
        
        # Create table using SQLAlchemy
        print("\nCreating table with SQLAlchemy...")
        db.create_all()
        
        # Verify creation
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(attendance_correction_request)")
        columns = cursor.fetchall()
        
        print("✓ Table created successfully")
        print("\nTable schema:")
        for col in columns:
            col_id, col_name, col_type, col_notnull, col_default, col_pk = col
            print(f"  • {col_name}: {col_type} (PK: {bool(col_pk)}, NOT NULL: {bool(col_notnull)})")
        
        conn.close()
        
        print("\n" + "="*70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")

if __name__ == '__main__':
    migrate_correction_request_table()
