## Attendance Correction Request - Quick Reference

### What It Does

Students can submit requests to correct their attendance status for any class. Perfect for:
- Marking errors
- System bugs
- Legitimate absence documentation (doctor's note, emergency, etc.)
- Any attendance discrepancy

### How Students Use It

1. **Access the Feature**
   - Click "Correct Attendance" button on student dashboard
   - Or navigate to `/correction-request`

2. **Submit Request**
   - Select course from dropdown
   - Select date of attendance record
   - View current status (auto-populated)
   - Choose desired status (present/absent)
   - Provide reason (10-500 characters)
   - Click "Submit Request"

3. **Track Request**
   - Click "Request History" tab
   - View all submitted requests
   - See status (pending/approved/rejected/cancelled)
   - Read admin notes if available
   - Cancel pending requests if needed

### API Endpoints (Quick Reference)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/correction/submit` | Submit new request |
| GET | `/correction/student-attendance-records` | Get records for form |
| GET | `/correction/list` | List all requests |
| GET | `/correction/list?status=pending` | Filter by status |
| GET | `/correction/<id>` | Get request details |
| POST | `/correction/<id>/cancel` | Cancel pending request |
| GET | `/correction/stats` | Get statistics |

### Request Status Flow

```
┌─────────┐
│ Pending │ ← Initial status when submitted
└────┬────┘
     │
     ├─→ Approved ─→ Attendance updated by admin
     │
     ├─→ Rejected ─→ Request denied (sees admin notes)
     │
     └─→ Cancelled ─→ Student cancels before review
```

### Database Table

**Table:** `attendance_correction_request`

Key fields:
- `student_id` - Who submitted
- `course_id` - Which course
- `date` - Date of attendance
- `current_status` - Current marked status
- `requested_status` - Desired status
- `reason` - Student's explanation
- `status` - Request status
- `submitted_at` - When submitted
- `reviewed_at` - When reviewed (null if pending)
- `reviewed_by` - Admin who reviewed (null if pending)
- `admin_notes` - Admin's response

### Setup Commands

```bash
# Create/update database table
python scripts/migrate_correction_requests.py

# Run tests
python test_correction_requests.py

# Start app (if not already running)
python src/main.py
```

### Frontend Template

**File:** `src/templates/correction_request.html`
**Route:** `/correction-request`

Features:
- Two-tab interface (submit + history)
- Form validation with helpful messages
- Auto-populated course/date dropdowns
- Character counter for reason
- Status badges with color coding
- Cancel button for pending requests
- Statistics summary

### What's NOT Included

This feature focuses on **student submission only**. The following need to be implemented separately by your admin/faculty system:

- Admin dashboard to view pending requests
- Request review interface
- Approval/rejection logic
- Attendance record updates upon approval
- Email notifications
- Request assignment to reviewers

### Common Validations

**Submission fails if:**
- Course field is empty
- Date field is empty
- Requested status field is empty
- Reason is less than 10 characters
- Reason exceeds 500 characters
- Invalid date format (use YYYY-MM-DD)
- Status is not 'present' or 'absent'
- Attendance record doesn't exist
- Pending request already exists for same record

### Testing the Feature

Run the test script to verify all functionality:

```bash
python test_correction_requests.py
```

Expected output:
```
✅ ATTENDANCE CORRECTION REQUEST FEATURE TEST PASSED

Feature Summary:
  ✅ Students can submit correction requests
  ✅ Requests are stored with complete information
  ✅ Students can view all their requests
  ✅ Requests can be filtered by status
  ✅ Students can cancel pending requests
  ✅ Admin can review and approve/reject requests
  ✅ Validation rules are enforced
  ✅ Request statistics can be calculated
```

### Example Submission

**Request:**
```json
POST /correction/submit
{
    "course_id": "CS101",
    "date": "2024-01-15",
    "current_status": "absent",
    "requested_status": "present",
    "reason": "I was sick but attended all online classes and submitted all assignments"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Correction request submitted successfully",
    "request_id": 42,
    "request": {
        "id": 42,
        "course_id": "CS101",
        "date": "2024-01-15",
        "current_status": "absent",
        "requested_status": "present",
        "status": "pending",
        "submitted_at": "2024-01-17T10:30:00"
    }
}
```

### File Structure

```
src/
├── models.py (AttendanceCorrectionRequest model)
├── correction_request_api.py (All API endpoints)
├── main.py (Flask routes)
└── templates/
    └── correction_request.html (Frontend UI)

scripts/
└── migrate_correction_requests.py (Database migration)

tests/
└── test_correction_requests.py (Test suite)

docs/
├── CORRECTION_REQUEST_FEATURE.md (Full documentation)
└── CORRECTION_REQUEST_QUICKREF.md (This file)
```

### Integration Points

**Dashboard Integration:**
- "Correct Attendance" button added to student dashboard
- Located in "Quick Actions" section
- Links directly to correction request page

**Authentication:**
- Requires login (Flask-Login)
- Requires 'student' role (RBAC)
- CSRF protection via Flask

**Database:**
- Uses existing SQLAlchemy/SQLite setup
- Foreign key to User model
- Proper timestamps with UTC

### Error Handling Examples

**Missing field:**
```json
{
    "success": false,
    "error": "Missing required field: reason"
}
```

**Invalid status:**
```json
{
    "success": false,
    "error": "Status must be either \"present\" or \"absent\""
}
```

**Attendance record not found:**
```json
{
    "success": false,
    "error": "No attendance record found for this course and date"
}
```

**Duplicate pending request:**
```json
{
    "success": false,
    "error": "A pending correction request already exists for this attendance record"
}
```

### Stats Endpoint Example

**Request:**
```
GET /correction/stats
```

**Response:**
```json
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

### Key Design Decisions

1. **Student-Focused Submission:** Feature only handles submission, not approval
2. **Clear Status Tracking:** Status workflow is simple and transparent
3. **Reason Required:** Encourages meaningful explanations
4. **Duplicate Prevention:** Only one pending request per record
5. **Audit Trail:** All timestamps and reviewer info stored
6. **No Automatic Approval:** Admin review always required
7. **Easy Cancellation:** Students can cancel before review
8. **Color-Coded UI:** Easy visual status identification

### Notes

- Requests are immutable once reviewed (except for student cancellation while pending)
- Admin review updates are not exposed in student endpoints
- Attendance updates from approved requests must be done separately
- System supports multiple requests per student across different records
- No rate limiting on submissions (consider adding if needed)
- Request reasons are stored as plain text (consider encryption if sensitive)
