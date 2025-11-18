"""
Script to retrieve all user credentials from the database
"""

import sys
import os

# Add src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from main import app
from models import User

def get_all_credentials():
    """Retrieve all user credentials from the database."""
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print("\n" + "="*80)
        print("ALL USER CREDENTIALS FROM DATABASE")
        print("="*80)
        print()
        
        for user in users:
            print(f"User ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Name: {user.name}")
            print(f"Role: {user.role}")
            print(f"Is Faculty: {user.is_faculty}")
            print(f"Password Hash: {user.password_hash}")
            print("-" * 80)
        
        print(f"\nTotal Users: {len(users)}")
        print("="*80)

if __name__ == "__main__":
    get_all_credentials()
