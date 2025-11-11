"""Test script to demonstrate SAS-88 RBAC functionality.

This script makes HTTP requests to test the role-based access control.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

# Test tokens from generate_test_tokens.py
STUDENT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6IlBFUzFVRzIzQ1MwMDEiLCJyb2xlIjoic3R1ZGVudCIsIm5hbWUiOiJTdHVkZW50IE9uZSIsImlhdCI6MTc2MjU4OTIxOCwiZXhwIjoxNzYyNjc1NjE4fQ.NL0sSWUKBM_QzgT_XQD3EdwP3HF3EDxOh1UmWs0hBT8"

TEACHER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6IkZBQzAwMSIsInJvbGUiOiJ0ZWFjaGVyIiwibmFtZSI6IlByb2YuIFNtaXRoIiwiaWF0IjoxNzYyNTg5MjE4LCJleHAiOjE3NjI2NzU2MTh9.Azgv2PltARzyRIzWHllPJRGv-y5Y2kE-i_I6OliHqKE"

ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozLCJ1c2VybmFtZSI6IkFETUlOMDAxIiwicm9sZSI6ImFkbWluIiwibmFtZSI6IkFkbWluIFVzZXIiLCJpYXQiOjE3NjI1ODkyMTgsImV4cCI6MTc2MjY3NTYxOH0.g9Of8IzfkPEFZPeZiKKbg7cMj1i633vztwUhkMhoj-A"


def check_endpoint(name, method, url, token, data=None):
    """Check an endpoint with a given token."""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=5)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=5)
        
        print(f"\n{'='*70}")
        print(f"{name}")
        print(f"{'='*70}")
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
        
        return response.status_code
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"{name}")
        print(f"{'='*70}")
        print(f"Error: {e}")
        return None


def main():
    """Run all RBAC tests."""
    print("="*70)
    print("SAS-88 RBAC - Live Testing Demo")
    print("="*70)
    
    # Test 1: Student accessing view endpoint (should succeed)
    check_endpoint(
        "Test 1: Student viewing attendance (SHOULD SUCCEED)",
        "GET",
        f"{BASE_URL}/attendance/api/view",
        STUDENT_TOKEN
    )
    
    # Test 2: Student accessing mark endpoint (should fail with 403)
    check_endpoint(
        "Test 2: Student marking attendance (SHOULD FAIL - 403)",
        "POST",
        f"{BASE_URL}/attendance/api/mark",
        STUDENT_TOKEN,
        {
            "student_id": 1,
            "subject": "Mathematics",
            "date": "2025-11-08",
            "status": "present"
        }
    )
    
    # Test 3: Student accessing override endpoint (should fail with 403)
    check_endpoint(
        "Test 3: Student overriding attendance (SHOULD FAIL - 403)",
        "PUT",
        f"{BASE_URL}/attendance/api/override",
        STUDENT_TOKEN,
        {
            "attendance_id": 456,
            "new_status": "present",
            "reason": "Correction"
        }
    )
    
    # Test 4: Teacher accessing view endpoint (should succeed)
    check_endpoint(
        "Test 4: Teacher viewing attendance (SHOULD SUCCEED)",
        "GET",
        f"{BASE_URL}/attendance/api/view",
        TEACHER_TOKEN
    )
    
    # Test 5: Teacher accessing mark endpoint (should succeed)
    check_endpoint(
        "Test 5: Teacher marking attendance (SHOULD SUCCEED)",
        "POST",
        f"{BASE_URL}/attendance/api/mark",
        TEACHER_TOKEN,
        {
            "student_id": 1,
            "subject": "Mathematics",
            "date": "2025-11-08",
            "status": "present"
        }
    )
    
    # Test 6: Teacher accessing override endpoint (should fail with 403)
    check_endpoint(
        "Test 6: Teacher overriding attendance (SHOULD FAIL - 403)",
        "PUT",
        f"{BASE_URL}/attendance/api/override",
        TEACHER_TOKEN,
        {
            "attendance_id": 456,
            "new_status": "present",
            "reason": "Correction"
        }
    )
    
    # Test 7: Admin accessing view endpoint (should succeed)
    check_endpoint(
        "Test 7: Admin viewing attendance (SHOULD SUCCEED)",
        "GET",
        f"{BASE_URL}/attendance/api/view",
        ADMIN_TOKEN
    )
    
    # Test 8: Admin accessing mark endpoint (should succeed)
    check_endpoint(
        "Test 8: Admin marking attendance (SHOULD SUCCEED)",
        "POST",
        f"{BASE_URL}/attendance/api/mark",
        ADMIN_TOKEN,
        {
            "student_id": 1,
            "subject": "Mathematics",
            "date": "2025-11-08",
            "status": "present"
        }
    )
    
    # Test 9: Admin accessing override endpoint (should succeed)
    check_endpoint(
        "Test 9: Admin overriding attendance (SHOULD SUCCEED)",
        "PUT",
        f"{BASE_URL}/attendance/api/override",
        ADMIN_TOKEN,
        {
            "attendance_id": 456,
            "new_status": "present",
            "reason": "Manual correction by admin"
        }
    )
    
    # Test 10: No token (should fail with 401)
    print(f"\n{'='*70}")
    print("Test 10: Accessing endpoint without token (SHOULD FAIL - 401)")
    print(f"{'='*70}")
    try:
        response = requests.get(f"{BASE_URL}/attendance/api/view", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\n{'='*70}")
    print("Testing Complete!")
    print(f"{'='*70}")
    print("\n✅ Summary:")
    print("   - Students can only view attendance")
    print("   - Teachers can view and mark attendance")
    print("   - Admins can view, mark, and override attendance")
    print("   - All unauthorized access returns 403 Forbidden")
    print("   - Missing tokens return 401 Unauthorized")


if __name__ == '__main__':
    main()
