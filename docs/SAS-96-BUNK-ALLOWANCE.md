# SAS-96: Bunk Allowance and Remaining Classes Feature

## Overview

The Bunk Allowance feature provides students and faculty with real-time insights into attendance statistics, remaining classes that can be bunked, and attendance projections. This feature integrates seamlessly with the existing attendance management system without modifying any existing files.

## Features

### For Students
- **View Bunk Allowance**: Check how many classes can still be bunked for each course
- **Attendance Statistics**: See current attendance percentage and classes attended/missed
- **Remaining Classes**: Track how many classes remain in the semester
- **Projections**: View attendance projections if attending all remaining classes or using all bunks
- **Critical Alerts**: Get notified when attendance falls below the minimum threshold

### For Faculty
- **Monitor All Students**: View bunk allowance status for all students in a course
- **Identify Critical Students**: Quickly find students with attendance below threshold
- **Bulk Refresh**: Update all student records at once
- **Course Statistics**: View attendance trends across the course

### For Administrators
- **Configure Courses**: Set up course-specific policies
- **Customize Thresholds**: Define bunk allowance and minimum attendance percentages
- **Total Classes**: Configure total number of classes per course

## Architecture

### New Files Created

```
src/
├── bunk_allowance_models.py       # Database models
├── bunk_allowance_service.py      # Business logic layer
├── bunk_allowance_api.py          # REST API endpoints
└── bunk_allowance_integration.py  # Integration helpers

scripts/
└── migrate_bunk_allowance.py      # Database migration script

tests/
├── conftest.py                    # Shared test fixtures
├── unit/
│   ├── test_bunk_allowance_models.py   # Model unit tests
│   └── test_bunk_allowance_service.py  # Service unit tests
├── integration/
│   └── test_bunk_allowance_api.py      # API integration tests
└── system/
    └── test_bunk_allowance_system.py   # End-to-end tests
```

### Database Schema

#### CourseConfig Table
```sql
CREATE TABLE course_config (
    id INTEGER PRIMARY KEY,
    course_id VARCHAR(50) UNIQUE NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    total_classes INTEGER DEFAULT 60,
    bunk_allowance_percentage FLOAT DEFAULT 25.0,
    min_attendance_percentage FLOAT DEFAULT 75.0,
    created_at DATETIME,
    updated_at DATETIME
);
```

#### StudentBunkAllowance Table
```sql
CREATE TABLE student_bunk_allowance (
    id INTEGER PRIMARY KEY,
    student_srn VARCHAR(100) NOT NULL,
    course_id VARCHAR(50) NOT NULL,
    total_classes_held INTEGER DEFAULT 0,
    classes_attended INTEGER DEFAULT 0,
    classes_missed INTEGER DEFAULT 0,
    current_attendance_percentage FLOAT DEFAULT 100.0,
    remaining_bunk_allowance INTEGER DEFAULT 0,
    is_attendance_critical BOOLEAN DEFAULT FALSE,
    last_updated DATETIME,
    UNIQUE(student_srn, course_id)
);
```

## API Endpoints

### Student Endpoints

#### GET `/api/bunk-allowance/student/<srn>`
Get bunk allowance for all courses of a student.

**Response:**
```json
{
  "success": true,
  "student_srn": "PES1UG23CS001",
  "courses": [
    {
      "course_id": "CS101",
      "total_classes_held": 30,
      "classes_attended": 25,
      "classes_missed": 5,
      "current_attendance_percentage": 83.33,
      "remaining_bunk_allowance": 10,
      "is_attendance_critical": false
    }
  ]
}
```

#### GET `/api/bunk-allowance/student/<srn>/course/<course_id>`
Get bunk allowance for a specific course.

#### GET `/api/bunk-allowance/breakdown/<srn>/<course_id>`
Get detailed breakdown with projections.

**Response:**
```json
{
  "success": true,
  "data": {
    "student_srn": "PES1UG23CS001",
    "course_id": "CS101",
    "current_stats": {
      "total_classes_held": 30,
      "classes_attended": 25,
      "classes_missed": 5,
      "attendance_percentage": 83.33
    },
    "course_policy": {
      "total_classes": 60,
      "min_attendance_percentage": 75.0,
      "bunk_allowance_percentage": 25.0,
      "max_bunk_allowed": 15
    },
    "remaining_classes": {
      "classes_remaining": 30,
      "safe_bunks_remaining": 10,
      "is_attendance_critical": false
    },
    "projections": {
      "if_attend_all_remaining": 91.67,
      "if_use_all_bunks": 41.67
    }
  }
}
```

### Faculty Endpoints

#### GET `/api/bunk-allowance/course/<course_id>/students`
Get all students' bunk allowance in a course (Faculty/Admin only).

#### GET `/api/bunk-allowance/critical?course_id=<course_id>`
Get students with critical attendance (Faculty/Admin only).

#### POST `/api/bunk-allowance/course/<course_id>/refresh`
Refresh all student records for a course (Faculty/Admin only).

### Admin Endpoints

#### POST `/api/bunk-allowance/course`
Create or update course configuration (Admin only).

**Request:**
```json
{
  "course_id": "CS101",
  "course_name": "Introduction to CS",
  "total_classes": 60,
  "bunk_allowance_percentage": 25.0,
  "min_attendance_percentage": 75.0
}
```

#### GET `/api/bunk-allowance/course/<course_id>`
Get course configuration.

### Health Check

#### GET `/api/bunk-allowance/health`
Check API health status.

## Installation & Setup

### 1. Install Dependencies
All required dependencies are already in `requirements.txt`:
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLAlchemy
- pytest (for testing)

### 2. Run Migration
```bash
python scripts/migrate_bunk_allowance.py
```

This will:
- Create necessary database tables
- Set up default course configurations
- Optionally sync existing attendance records

### 3. Register Blueprint in main.py

Add to your `src/main.py` (at the end, before `if __name__ == '__main__'`):

```python
# SAS-96: Register Bunk Allowance API
from bunk_allowance_integration import register_bunk_allowance_blueprint, init_bunk_allowance_tables

init_bunk_allowance_tables(db)
register_bunk_allowance_blueprint(app)
```

Or manually register the blueprint:

```python
from bunk_allowance_api import bunk_allowance_bp
app.register_blueprint(bunk_allowance_bp)
```

### 4. Create Tables
```bash
python -c "from src.main import app, db; app.app_context().push(); db.create_all(); print('Tables created')"
```

## Testing

### Run All Tests
```bash
# Run all bunk allowance tests
pytest tests/unit/test_bunk_allowance_models.py -v
pytest tests/unit/test_bunk_allowance_service.py -v
pytest tests/integration/test_bunk_allowance_api.py -v
pytest tests/system/test_bunk_allowance_system.py -v

# Run all tests
pytest tests/ -v
```

### Test Coverage
```bash
pytest --cov=src.bunk_allowance_models --cov=src.bunk_allowance_service --cov=src.bunk_allowance_api --cov-report=html
```

### CI/CD Integration
The feature is fully compatible with the existing CI pipeline defined in `.github/workflows/ci.yml`. All tests will run automatically on push/pull requests.

## Usage Examples

### Example 1: Student Checking Bunk Allowance

```python
import requests

# Login first
session = requests.Session()
session.post('http://localhost:5000/login', data={
    'username': 'PES1UG23CS001',
    'password': 'password'
})

# Get bunk allowance for all courses
response = session.get('http://localhost:5000/api/bunk-allowance/student/PES1UG23CS001')
data = response.json()

for course in data['courses']:
    print(f"Course: {course['course_id']}")
    print(f"Attendance: {course['current_attendance_percentage']}%")
    print(f"Bunks Remaining: {course['remaining_bunk_allowance']}")
    print(f"Critical: {course['is_attendance_critical']}")
    print()
```

### Example 2: Faculty Monitoring Critical Students

```python
# Login as faculty
session.post('http://localhost:5000/login', data={
    'username': 'FAC001',
    'password': 'password'
})

# Get critical students
response = session.get('http://localhost:5000/api/bunk-allowance/critical?course_id=CS101')
data = response.json()

print(f"Critical Students: {data['total_critical']}")
for student in data['students']:
    print(f"- {student['student_srn']}: {student['current_attendance_percentage']}%")
```

### Example 3: Admin Configuring Course

```python
# Login as admin
session.post('http://localhost:5000/login', data={
    'username': 'ADMIN001',
    'password': 'password'
})

# Create course configuration
response = session.post('http://localhost:5000/api/bunk-allowance/course',
    json={
        'course_id': 'CS201',
        'course_name': 'Data Structures',
        'total_classes': 60,
        'bunk_allowance_percentage': 20.0,
        'min_attendance_percentage': 80.0
    }
)
print(response.json())
```

## Business Logic

### Bunk Allowance Calculation

```
Max Bunks Allowed = (Bunk Allowance % / 100) × Total Classes
Remaining Bunks = Max Bunks Allowed - Classes Already Missed

Example:
- Total Classes: 60
- Bunk Allowance: 25%
- Max Bunks: 15 classes
- Already Missed: 5 classes
- Remaining Bunks: 10 classes
```

### Critical Attendance Detection

```
Current Attendance % = (Classes Attended / Total Classes Held) × 100
Is Critical = Current Attendance % < Minimum Attendance %

Example:
- Classes Held: 30
- Classes Attended: 20
- Current Attendance: 66.67%
- Minimum Required: 75%
- Status: CRITICAL ⚠️
```

### Attendance Projections

```
If Attend All Remaining:
= (Classes Attended + Classes Remaining) / Total Classes × 100

If Use All Bunks:
= (Classes Attended) / Total Classes × 100
```

## Security & Authorization

### Role-Based Access Control

| Endpoint | Student | Faculty | Admin |
|----------|---------|---------|-------|
| View Own Data | ✓ | ✓ | ✓ |
| View All Students | ✗ | ✓ | ✓ |
| View Critical Students | ✗ | ✓ | ✓ |
| Configure Courses | ✗ | ✗ | ✓ |
| Refresh Course Data | ✗ | ✓ | ✓ |

### Authentication
- Supports both Flask-Login session and JWT token authentication
- Automatically detects authentication method
- Secure access to student data

## Performance Considerations

### Caching Strategy
- `StudentBunkAllowance` table acts as a cache
- Updated automatically when accessed
- Manual refresh available for bulk updates

### Database Optimization
- Indexed columns: `student_srn`, `course_id`
- Composite unique constraint prevents duplicates
- Efficient queries using SQLAlchemy ORM

### Scalability
- Service layer separates business logic
- Stateless API design
- Supports horizontal scaling

## Monitoring & Maintenance

### Health Check
Monitor API health:
```bash
curl http://localhost:5000/api/bunk-allowance/health
```

### Database Maintenance
Refresh all records periodically:
```python
from src.bunk_allowance_service import BunkAllowanceService

# Refresh specific course
result = BunkAllowanceService.bulk_update_course_allowances('CS101')
print(f"Updated {result['updated_count']} students")
```

### Logs
All operations are logged through Flask's logging system.

## Troubleshooting

### Issue: Tables Not Created
```bash
# Solution: Run migration script
python scripts/migrate_bunk_allowance.py
```

### Issue: Blueprint Not Registered
```bash
# Solution: Register blueprint in main.py
from bunk_allowance_api import bunk_allowance_bp
app.register_blueprint(bunk_allowance_bp)
```

### Issue: Data Not Syncing
```bash
# Solution: Manually refresh
python -c "from src.bunk_allowance_service import BunkAllowanceService; BunkAllowanceService.bulk_update_course_allowances('COURSE_ID')"
```

## Future Enhancements

- [ ] Email notifications for critical attendance
- [ ] Mobile app integration
- [ ] Attendance prediction using ML
- [ ] Parent portal access
- [ ] Automated reports generation
- [ ] Integration with academic calendar

## Support

For issues or questions, please:
1. Check the logs in the Flask console
2. Run the test suite to identify issues
3. Review the API documentation above
4. Contact the development team

## License

This feature is part of the PESU Student Attendance Management System and follows the same license.
