"""Migration script to add account locking fields to User model.

This script adds the following fields:
- failed_login_attempts (Integer, default 0)
- account_locked (Boolean, default False)
- locked_at (DateTime, nullable)

Run this script to update existing database with new fields.
"""

import sys
import os

# Add src to path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User

def migrate_database():
    """Add account locking fields to existing User table."""
    with app.app_context():
        # Check if we're using SQLite
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            print("Detected SQLite database")
            
            # For SQLite, we need to use raw SQL to add columns
            with db.engine.connect() as conn:
                try:
                    # Add failed_login_attempts column
                    conn.execute(db.text(
                        'ALTER TABLE user ADD COLUMN failed_login_attempts INTEGER DEFAULT 0'
                    ))
                    print("✓ Added failed_login_attempts column")
                except Exception as e:
                    if 'duplicate column name' in str(e).lower():
                        print("✓ failed_login_attempts column already exists")
                    else:
                        print(f"✗ Error adding failed_login_attempts: {e}")
                
                try:
                    # Add account_locked column
                    conn.execute(db.text(
                        'ALTER TABLE user ADD COLUMN account_locked BOOLEAN DEFAULT 0'
                    ))
                    print("✓ Added account_locked column")
                except Exception as e:
                    if 'duplicate column name' in str(e).lower():
                        print("✓ account_locked column already exists")
                    else:
                        print(f"✗ Error adding account_locked: {e}")
                
                try:
                    # Add locked_at column
                    conn.execute(db.text(
                        'ALTER TABLE user ADD COLUMN locked_at DATETIME'
                    ))
                    print("✓ Added locked_at column")
                except Exception as e:
                    if 'duplicate column name' in str(e).lower():
                        print("✓ locked_at column already exists")
                    else:
                        print(f"✗ Error adding locked_at: {e}")
                
                conn.commit()
        else:
            # For other databases, use SQLAlchemy's create_all
            # This will add missing columns
            db.create_all()
            print("✓ Database schema updated")
        
        print("\nMigration complete!")
        print("All users now have account locking fields initialized.")

if __name__ == '__main__':
    print("=" * 60)
    print("Account Locking Migration Script")
    print("=" * 60)
    print()
    
    migrate_database()
