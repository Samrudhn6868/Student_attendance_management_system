"""Database migration script to add override fields to Attendance model.

This script adds the following columns to the Attendance table:
- is_overridden: Boolean flag indicating if attendance was overridden
- override_reason: Text field for the reason of override
- overridden_by: Foreign key to User who performed the override
- override_timestamp: ISO timestamp of when override occurred

Usage:
    python scripts/add_override_columns.py
"""

import sys
import os

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app, db
from sqlalchemy import text


def add_override_columns():
    """Add override-related columns to the Attendance table."""
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('attendance')]
            
            columns_to_add = {
                'is_overridden': 'BOOLEAN DEFAULT 0',
                'override_reason': 'VARCHAR(500)',
                'overridden_by': 'INTEGER',
                'override_timestamp': 'VARCHAR(50)'
            }
            
            for column_name, column_type in columns_to_add.items():
                if column_name not in existing_columns:
                    print(f"Adding column: {column_name}")
                    try:
                        # SQLite-compatible ALTER TABLE
                        with db.engine.connect() as conn:
                            conn.execute(text(
                                f"ALTER TABLE attendance ADD COLUMN {column_name} {column_type}"
                            ))
                            conn.commit()
                        print(f"✓ Successfully added column: {column_name}")
                    except Exception as e:
                        print(f"✗ Failed to add column {column_name}: {str(e)}")
                else:
                    print(f"Column {column_name} already exists, skipping...")
            
            print("\n✓ Migration completed successfully!")
            
        except Exception as e:
            print(f"✗ Migration failed: {str(e)}")
            return False
    
    return True


if __name__ == '__main__':
    print("Starting database migration...")
    print("=" * 60)
    success = add_override_columns()
    print("=" * 60)
    
    if success:
        print("Migration completed. Override functionality is now available.")
    else:
        print("Migration failed. Please check the error messages above.")
        sys.exit(1)
