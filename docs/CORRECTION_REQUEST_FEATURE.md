## Attendance Correction Request Feature

### Overview

The Attendance Correction Request feature allows students to submit formal requests to correct their attendance status for specific classes. This provides a channel for students to appeal or correct potential errors in their attendance records without requiring direct admin intervention for the submission process.

### Key Features

**For Students:**
- Submit correction requests with detailed reasoning
- View all submitted requests with status tracking
- View request history and admin feedback
- Cancel pending requests
- View statistics on submitted requests

**System Features:**
- Request validation (prevents duplicate pending requests)
- Status workflow: pending → approved/rejected/cancelled
- Admin notes and review timestamps
- Complete audit trail of all requests

### Database Schema

The `AttendanceCorrectionRequest` model stores:

```
id                      - Primary key
student_id              - Student who submitted the request (FK to User)
student_name            - Student's name (for easy reference)
course_id               - Course identifier
date                    - Date of attendance record
current_status          - Current attendance status ('present' or 'absent')
requested_status        - Desired attendance status ('present' or 'absent')
reason                  - Student's explanation (required, 10-500 chars)
status                  - Request status ('pending', 'approved', 'rejected', 'cancelled')
submitted_at            - Submission timestamp
reviewed_at             - Review timestamp (nullable)
reviewed_by             - Admin user ID who reviewed (nullable)
admin_notes             - Response/notes from admin (nullable)
```

### API Endpoints

#### Student Endpoints

All student endpoints require login and `student` role.

**1. Submit Correction Request**
```
POST /correction/submit
Content-Type: application/json

{
    "course_id": "CS101",
    "date": "2024-01-15",
    "current_status": "absent",
    "requested_status": "present",
    "reason": "I was sick but attended online classes and completed assignments"
}

Response:
{
    "success": true,
    "message": "Correction request submitted successfully",
    "request_id": 123,
    "request": {
        "id": 123,
        "course_id": "CS101",
        "date": "2024-01-15",
        "current_status": "absent",
        "requested_status": "present",
        "reason": "...",
        "status": "pending",
        "submitted_at": "2024-01-17T10:30:00"
    }
}
```

**2. Get Student Attendance Records** (for form population)
```
GET /correction/student-attendance-records

Response:
{
    "success": true,
    "records": [
        {
            "course_id": "CS101",
            "date": "2024-01-15",
            "status": "absent",
            "marked_by": "faculty_name",
            "marked_date": "2024-01-15T14:00:00"
        },
        ...
    ]
}
```

**3. List All Student Requests**
```
GET /correction/list
GET /correction/list?status=pending
GET /correction/list?status=approved
GET /correction/list?status=rejected
GET /correction/list?status=cancelled

Response:
{
    "success": true,
    "total": 5,
    "requests": [
        {
            "id": 1,
            "course_id": "CS101",
            "date": "2024-01-15",
            "current_status": "absent",
            "requested_status": "present",
            "reason": "...",
            "status": "pending",
            "submitted_at": "2024-01-17T10:30:00",
            "reviewed_at": null,
            "admin_notes": null
        },
        ...
    ]
}
```

**4. Get Single Request Details**
```
GET /correction/<request_id>

Response:
{
    "success": true,
    "request": {
        "id": 1,
        "course_id": "CS101",
        "date": "2024-01-15",
        "current_status": "absent",
        "requested_status": "present",
        "reason": "...",
        "status": "pending",
        "submitted_at": "2024-01-17T10:30:00",
        "reviewed_at": null,
        "admin_notes": null
    }
}
```

**5. Cancel Request**
```
POST /correction/<request_id>/cancel

Response:
{
    "success": true,
    "message": "Correction request cancelled successfully",
    "request": {
        "id": 1,
        "course_id": "CS101",
        "date": "2024-01-15",
        "status": "cancelled"
    }
}
```

**6. Get Request Statistics**
```
GET /correction/stats

Response:
{
    "success": true,
    "stats": {
        "total": 5,
        "pending": 2,
        "approved": 2,
        "rejected": 1,
        "cancelled": 0
    }
}
```

### Frontend UI

**URL:** `/correction-request`

**Tabs:**
1. **Submit Request** - Form to submit new correction requests
   - Course selector (populated from student's attendance records)
   - Date selector (populated based on selected course)
   - Current status display (read-only)
   - Requested status dropdown
   - Reason textarea with character counter
   - Validation feedback

2. **Request History** - View all submitted requests
   - Statistics cards (total, pending, approved, rejected)
   - Request list with status badges
   - Color-coded request cards by status
   - Admin notes display when available
   - Cancel button for pending requests

**Integration:**
- Added "Correct Attendance" button to student dashboard
- Accessible from quick actions menu

### Validation Rules

1. **Reason Length:**
   - Minimum: 10 characters
   - Maximum: 500 characters

2. **Status Values:**
   - Only 'present' and 'absent' allowed
   - Must be different from current status (can't request same status)

3. **Duplicate Prevention:**
   - Cannot have multiple pending requests for same course/date
   - Previous approved/rejected requests don't block new requests

4. **Attendance Verification:**
   - Requested attendance record must exist in system
   - Returns 404 if record not found

5. **Permission:**
   - Students can only view/manage their own requests
   - Returns 403 if attempting to access others' requests

### Status Workflow

```
pending → approved
       → rejected
       → cancelled (by student only)
```

**Pending:** Request awaiting review
**Approved:** Request accepted, attendance should be updated
**Rejected:** Request declined with admin notes
**Cancelled:** Cancelled by student before review

### Error Handling

The API provides detailed error responses:

**400 Bad Request:**
- Missing required fields
- Invalid status values
- Reason too short/long
- Invalid date format

**404 Not Found:**
- Request doesn't exist
- Attendance record doesn't exist

**409 Conflict:**
- Duplicate pending request exists
- Cannot cancel non-pending request

**500 Server Error:**
- Database errors
- Processing errors

### Setup & Migration

1. **Create/Update Database:**
   ```bash
   python scripts/migrate_correction_requests.py
   ```

2. **Verify Table Creation:**
   ```bash
   python test_correction_requests.py
   ```

### Testing

Run the comprehensive test suite:
```bash
python test_correction_requests.py
```

**Tests Included:**
- View student attendance records
- Submit valid correction request
- Submit multiple requests
- Retrieve and filter requests
- Cancel pending requests
- Simulate admin review
- Calculate statistics
- Validate business rules

### Notes on Admin/Faculty Review

**Important:** This feature focuses on student submission only. The review and approval logic is handled separately by the admin/faculty system (not included in this implementation).

To complete the workflow, admins/faculty need to:
1. Query pending requests (not yet displayed in admin UI)
2. Review request details and reason
3. Update `status` field to 'approved' or 'rejected'
4. Optionally add notes in `admin_notes` field
5. Set `reviewed_at` and `reviewed_by` fields
6. If approved, update the corresponding Attendance record status

**Example Admin Workflow (pseudocode):**
```python
# Get pending requests
pending = AttendanceCorrectionRequest.query.filter_by(status='pending').all()

# Review and approve
req = pending[0]
req.status = 'approved'
req.reviewed_at = datetime.utcnow()
req.reviewed_by = admin_user.id
req.admin_notes = 'Verified with faculty - attendance corrected'
db.session.commit()

# Update attendance record
attendance = Attendance.query.filter_by(
    student_id=req.student_id,
    course_id=req.course_id,
    date=req.date
).first()
attendance.status = req.requested_status
db.session.commit()
```

### Example Usage Flow

**Student Submission:**
1. Navigate to "Correct Attendance" from dashboard
2. Select course with marking error
3. Select the specific date
4. Review current status (shown as read-only)
5. Select desired status
6. Provide detailed reason
7. Submit request
8. See confirmation with request ID
9. Track request in "Request History" tab

**Admin Review (separate system):**
1. View pending correction requests
2. Verify student's claim
3. Contact faculty if needed
4. Approve or reject with notes
5. If approved, update attendance record
6. Student sees updated request status and notes

### Future Enhancements

Potential improvements for future versions:
- Admin dashboard for viewing/processing requests
- Email notifications for submission and review
- Request assignment to specific reviewers
- Appeal process for rejected requests
- Bulk operations for admin review
- Request templates for common scenarios
- Integration with leave request system
- Analytics on correction request trends
- Request deadline system
- Automatic reminders for pending requests

### Security Considerations

- All requests are role-based (students only for submission)
- Students can only access their own requests
- Admin review notes are separate from student-visible information
- All actions are timestamp-recorded
- Database constraints prevent orphaned records
