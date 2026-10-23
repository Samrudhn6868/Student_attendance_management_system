"""Database migration script to add role column for SAS-88 RBAC.

This script adds a 'role' column to the existing users table.
Role values: 'student', 'teacher', 'admin'
"""

import sqlite3
import os
import sys

# Get the path to the database
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'instance', 'attendance.db')


def add_role_column():
    """Add role column to users table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if role column already exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'role' in columns:
            print("✓ Role column already exists in users table")
            return
        
        # Add role column with default value
        print("Adding role column to users table...")
        cursor.execute("""
            ALTER TABLE user 
            ADD COLUMN role TEXT NOT NULL DEFAULT 'student'
            CHECK(role IN ('student', 'teacher', 'admin'))
        """)
        
        # Update existing users based on is_faculty field
        print("Migrating existing users...")
        cursor.execute("""
            UPDATE user 
            SET role = CASE 
                WHEN is_faculty = 1 THEN 'teacher'
                ELSE 'student'
            END
        """)
        
        conn.commit()
        print("✓ Successfully added role column and migrated existing users")
        print("  - Faculty users → 'teacher' role")
        print("  - Student users → 'student' role")
        
    except sqlite3.Error as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("SAS-88: Adding Role Column for RBAC")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"✗ Database not found at: {DB_PATH}")
        print("  Please run the application first to create the database.")
        sys.exit(1)
    
    add_role_column()
    print("\nMigration complete!")
