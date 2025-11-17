# Admin Attendance Override Feature

## Overview

The Admin Attendance Override feature allows administrators to directly modify any student's attendance record without requiring a student-submitted correction request. This feature is **independent** from the student correction request system and provides complete audit trail tracking.

**Key Purpose**: Admins can correct system errors, handle special cases, or make manual adjustments to attendance with full accountability.

## Features

### Core Functionality

1. **Direct Override** - Change any student's attendance status
   - Mark present → absent or vice versa
   - Requires reason (5-500 characters)
   - Immediate effect on records

2. **Undo Capability** - Remove previous overrides
   - Clears override flags and reason
   - Maintains audit trail (doesn't delete history)
   - Re-enables student correction requests if needed

3. **Student Search** - Find students efficiently
   - Search by name or username
   - Pagination support (limit results)
   - Real-time search with debouncing

4. **Attendance Record View** - See student's complete attendance history
   - Filter by date range (from_date, to_date)
   - Show only overridden records (overridden_only=true)
   - Display current status and override details

5. **Audit Trail / Override History**
   - Complete record of all overrides
   - Admin name, reason, timestamp
   - Searchable by admin (filter by admin_id)
   - Pagination support (limit, offset)

6. **Statistics & Reporting**
   - Total override count
   - Override percentage of all attendance
   - Breakdown of overrides by admin
   - Useful for auditing and accountability

## User Interface

### Access
- **URL**: `/admin/override-attendance`
- **Route**: Requires `admin` role
- **Authentication**: Must be logged in

### Interface Layout

Three main tabs:

#### 1. Override Attendance Tab
- **Student Search Input** - Type to search students (min 2 chars)
- **Search Results** - Clickable list of matching students
- **Student's Records** - All attendance records for selected student
  - Shows date, current status, override status (if any)
  - Click to select a record
- **Override Form Fields** (after selecting record)
  - Current status and date displayed
  - New Status dropdown (present/absent)
  - Override Reason textarea (5-500 chars with counter)
  - Submit/Reset/Clear buttons

#### 2. Override History Tab
- **Complete audit trail** of all overrides
- Displays:
  - Student name and date
  - Override status (badge)
  - Reason provided by admin
  - Admin who made the override
  - Timestamp of override
- Scrollable list with recent overrides first

#### 3. Statistics Tab
- **Key Metrics**:
  - Total Overrides (count)
  - Override Percentage (% of all records)
- **Overrides by Admin** table
  - Shows each admin and their override count
  - Useful for auditing specific admins

### Visual Design
- Purple gradient background (professional)
- Bootstrap 5 styling
- Responsive layout (mobile-friendly)
- Status color coding (green=present, red=absent, yellow=overridden)
- Real-time form validation
- Toast notifications for success/error messages

## API Reference

### Base URL
```
/api/admin/override
```

### Endpoints

#### 1. Override Attendance Record
```
POST /api/admin/override/attendance/<id>
```

**Purpose**: Change an attendance record's status

**Authentication**: Required (admin role)

**Request Body**:
```json
{
    "new_status": "present",  // or "absent"
    "reason": "System error corrected by administrator"
}
```

**Validation**:
- `new_status`: Must be "present" or "absent"
- `reason`: String, 5-500 characters, required

**Response** (Success - 200):
```json
{
    "success": true,
    "message": "Attendance overridden successfully",
    "record": {
        "id": 123,
        "student_id": 10,
        "date": "2024-01-15",
        "status": "present",
        "is_overridden": true,
        "override_reason": "System error corrected by administrator",
        "overridden_by": 5,
        "override_timestamp": "2024-01-20T14:30:00"
    }
}
```

**Response** (Error - 400/404):
```json
{
    "success": false,
    "error": "Invalid request or record not found"
}
```

---

#### 2. Undo Override
```
POST /api/admin/override/attendance/<id>/undo
```

**Purpose**: Remove an override from an attendance record

**Authentication**: Required (admin role)

**Request Body**: Empty (no parameters needed)

**Response** (Success - 200):
```json
{
    "success": true,
    "message": "Override removed successfully",
    "record": {
        "id": 123,
        "is_overridden": false,
        "override_reason": null,
        "overridden_by": null,
        "override_timestamp": null
    }
}
```

---

#### 3. Get Student's Attendance Records
```
GET /api/admin/override/student/<student_id>/records
```

**Purpose**: Retrieve all attendance records for a specific student with optional filters

**Authentication**: Required (admin role)

**Query Parameters**:
- `from_date` (optional): ISO date format (YYYY-MM-DD)
- `to_date` (optional): ISO date format (YYYY-MM-DD)
- `overridden_only` (optional): Boolean, show only overridden records

**Example**: `/api/admin/override/student/10/records?from_date=2024-01-01&to_date=2024-01-31&overridden_only=true`

**Response** (Success - 200):
```json
{
    "success": true,
    "student": {
        "id": 10,
        "name": "John Doe",
        "username": "johndoe"
    },
    "total_records": 25,
    "records": [
        {
            "id": 101,
            "date": "2024-01-20",
            "status": "present",
            "is_overridden": false,
            "override_reason": null,
            "updated_at": "2024-01-20T10:00:00"
        },
        {
            "id": 102,
            "date": "2024-01-19",
            "status": "absent",
            "is_overridden": true,
            "override_reason": "System error corrected",
            "overridden_by": {
                "id": 5,
                "name": "Admin User"
            },
            "override_timestamp": "2024-01-19T14:30:00"
        }
    ]
}
```

---

#### 4. Get Override History (Audit Trail)
```
GET /api/admin/override/override-history
```

**Purpose**: Retrieve complete audit trail of all overrides performed

**Authentication**: Required (admin role)

**Query Parameters**:
- `limit` (optional): Number of records to return (default: 50, max: 1000)
- `offset` (optional): Pagination offset (default: 0)
- `admin_id` (optional): Filter by specific admin

**Example**: `/api/admin/override/override-history?limit=20&offset=0&admin_id=5`

**Response** (Success - 200):
```json
{
    "success": true,
    "total": 150,
    "limit": 50,
    "offset": 0,
    "history": [
        {
            "id": 1001,
            "student": {
                "id": 10,
                "name": "John Doe",
                "username": "johndoe"
            },
            "date": "2024-01-20",
            "status": "present",
            "override_reason": "System glitch correction",
            "overridden_by": {
                "id": 5,
                "name": "Admin User",
                "username": "admin"
            },
            "override_timestamp": "2024-01-20T14:30:00"
        }
    ]
}
```

---

#### 5. Search Students
```
GET /api/admin/override/search-students
```

**Purpose**: Find students by name or username (for dropdown/autocomplete)

**Authentication**: Required (admin role)

**Query Parameters**:
- `query` (required): Search term (minimum 2 characters)
- `limit` (optional): Max results (default: 20)

**Validation**:
- Query must be at least 2 characters

**Example**: `/api/admin/override/search-students?query=john&limit=10`

**Response** (Success - 200):
```json
{
    "success": true,
    "students": [
        {
            "id": 10,
            "name": "John Doe",
            "username": "johndoe"
        },
        {
            "id": 11,
            "name": "Johnny Smith",
            "username": "jsmith"
        }
    ]
}
```

**Response** (Error - 400):
```json
{
    "success": false,
    "error": "Query must be at least 2 characters"
}
```

---

#### 6. Get Override Statistics
```
GET /api/admin/override/stats
```

**Purpose**: Retrieve overall statistics about overrides

**Authentication**: Required (admin role)

**Response** (Success - 200):
```json
{
    "success": true,
    "stats": {
        "total_overrides": 45,
        "override_percentage": 3.5,
        "total_attendance_records": 1285,
        "overrides_by_admin": [
            {
                "admin_id": 5,
                "admin_name": "Admin User",
                "override_count": 25
            },
            {
                "admin_id": 6,
                "admin_name": "Another Admin",
                "override_count": 20
            }
        ]
    }
}
```

## Database Schema

### Attendance Table (Override Fields)

The following fields in the `attendance` table track overrides:

| Field | Type | Description |
|-------|------|-------------|
| `is_overridden` | BOOLEAN | Whether record was overridden |
| `override_reason` | VARCHAR(500) | Reason for override |
| `overridden_by` | INTEGER (FK) | User ID of admin who override |
| `override_timestamp` | VARCHAR | ISO format timestamp |

### Related Tables

- **User** (referenced by `overridden_by`)
  - Contains admin user details
  - Name, username, email

- **Attendance** (main table)
  - Contains all attendance records
  - One per student per date

## HTTP Status Codes

| Code | Scenario |
|------|----------|
| 200 | Successful operation |
| 400 | Bad request (invalid data or missing fields) |
| 401 | Unauthorized (not logged in) |
| 403 | Forbidden (not admin role) |
| 404 | Record not found |
| 500 | Server error |

## Error Handling

### Invalid Reason Length
```json
{
    "success": false,
    "error": "Reason must be between 5 and 500 characters"
}
```

### Invalid Status
```json
{
    "success": false,
    "error": "Invalid status. Must be 'present' or 'absent'"
}
```

### Record Not Found
```json
{
    "success": false,
    "error": "Attendance record not found"
}
```

### Student Not Found
```json
{
    "success": false,
    "error": "Student not found"
}
```

### RBAC Denied (Non-Admin)
```json
{
    "success": false,
    "error": "Admin access required"
}
```

## Security Features

1. **Role-Based Access Control**
   - All endpoints require `admin` role
   - @require_role('admin') decorator enforces this
   - Logged-in users without admin role receive 403 error

2. **Audit Trail**
   - Every override records:
     - Admin ID who made it
     - Exact timestamp
     - Reason provided
   - Complete immutable history for accountability

3. **Data Validation**
   - Reason field validated (5-500 chars)
   - Status field validated (must be valid enum)
   - Student/record existence verified before override

4. **Input Sanitization**
   - All user inputs validated
   - Reason field limited to safe string length
   - No SQL injection vectors (using parameterized queries)

## Workflow Examples

### Example 1: Simple Override

1. Admin navigates to `/admin/override-attendance`
2. Searches for student: "John"
3. Selects "John Doe" from results
4. System loads John's attendance records (25 total)
5. Admin clicks on record from 2024-01-15 (showing "absent")
6. Form displays: "Current: absent → New: present"
7. Admin fills reason: "Student was present but marked absent by system error"
8. Clicks "Override Attendance"
9. API call: `POST /api/admin/override/attendance/123` with status="present" and reason
10. Success message displays
11. Record updated to show "Overridden" status with yellow badge

### Example 2: Audit Trail Review

1. Admin clicks "Override History" tab
2. System loads recent 50 overrides (default limit)
3. Admin sees:
   - "Jane Smith" - 2024-01-18 - absent → **Overridden to present**
     - Reason: "Lab participation verified by faculty"
     - By: Admin User (5 days ago)
   - "Mike Johnson" - 2024-01-17 - present → **Overridden to absent**
     - Reason: "Duplicate attendance entry removed"
     - By: Admin User (6 days ago)

### Example 3: Admin Accountability

1. Admin clicks "Statistics" tab
2. Sees:
   - Total Overrides: 45 (3.5% of 1285 records)
   - Admin breakdown:
     - "Admin User": 25 overrides (55%)
     - "Another Admin": 20 overrides (45%)
3. Can identify which admins are making most overrides
4. Use for auditing and accountability

## Integration with Correction Requests

The admin override feature is **completely independent** from student correction requests:

| Aspect | Correction Request | Admin Override |
|--------|-------------------|-----------------|
| **Initiated By** | Student | Admin |
| **Requires Approval** | Yes | No |
| **Immediate Effect** | No | Yes |
| **Undo Capability** | Cancel (if pending) | Yes (anytime) |
| **Use Case** | Student disputes attendance | System errors, special cases |
| **Audit Trail** | Request history | Override history |

Both systems can work simultaneously:
- Student submits correction request
- Admin can override independently
- Both are tracked separately in audit trails

## Testing

Run the comprehensive test suite:

```bash
# Run all admin override tests
pytest tests/test_admin_override.py -v

# Run specific test class
pytest tests/test_admin_override.py::TestAdminOverrideAPI -v

# Run specific test
pytest tests/test_admin_override.py::TestAdminOverrideAPI::test_override_attendance_success -v

# Run with coverage
pytest tests/test_admin_override.py --cov=src.admin_override_api
```

### Test Coverage (24 tests)

**API Endpoints (20 tests)**:
- Override success/validation/not found
- Undo override
- Get student records with/without filters
- Override history retrieval
- Student search (valid/invalid)
- Statistics retrieval
- RBAC enforcement (3 tests)
- Audit trail verification
- Concurrent overrides
- Invalid/missing field handling

**Page Access (4 tests)**:
- Admin can access page
- Non-admin denied
- Unauthenticated redirected

## Troubleshooting

### "Record not found" Error
- Verify the attendance record ID exists
- Check student has attendance records for that date
- Ensure record wasn't already deleted

### "Admin access required" Error
- Verify user account has 'admin' role in database
- Check role is spelled correctly (case-sensitive)
- Ensure session/login is active

### Override History Not Showing
- Check that overrides were actually created
- Verify admin user has correct ID in override records
- Try accessing `/api/admin/override/stats` to verify overrides exist

### Student Search Returns No Results
- Ensure query is at least 2 characters
- Check spelling of name/username
- Try broader search term

## Future Enhancements

Potential features for future versions:

1. **Batch Overrides** - Override multiple records at once
2. **Approval Workflow** - Require 2-admin approval for overrides
3. **Revert History** - Restore previous status values
4. **Email Notifications** - Alert students of overrides
5. **Advanced Filtering** - Filter history by date range, admin, reason
6. **Override Reasons Library** - Pre-defined common reasons
7. **Export Reports** - Download override history as CSV/PDF
8. **Time-based Overrides** - Schedule future overrides
9. **Bulk Student Selection** - Override multiple students' same date
10. **Analytics Dashboard** - Visual charts and trends

## Support & Questions

For issues or questions about this feature:

1. Check the troubleshooting section above
2. Review test cases for usage examples
3. Check API response error messages
4. Verify role-based access (admin required)
5. Review audit trail for related changes

---

**Feature Status**: ✅ Production Ready

**Last Updated**: 2024-01-20

**Version**: 1.0
