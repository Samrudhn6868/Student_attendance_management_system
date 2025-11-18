# SAS-99: Teacher Review and Approval of Correction Requests

## Overview

This feature implements a teacher review system for student attendance correction requests with a strict 48-hour review window. Teachers can approve or deny student correction requests, and requests that are not reviewed within 48 hours automatically expire.

## User Story

**As a teacher**, I want to review and approve/deny student attendance correction requests within 48 hours, so that attendance records remain accurate while giving students a fair chance to correct genuine errors.

## Features Implemented

### 1. Pending Request Queue
- View all pending correction requests sorted by submission time
- Visual indicator showing time remaining (48-hour countdown)
- Urgent badge for requests with less than 6 hours remaining
- Auto-refresh capability

### 2. Approve/Deny Actions
- **Approve**: Updates attendance record + marks request as approved
- **Deny**: Rejects request with mandatory reason/notes
- Both actions logged in audit trail

### 3. 48-Hour Auto-Expiration
- Requests older than 48 hours automatically marked as "expired"
- Prevents stale requests from cluttering the queue
- Expired requests visible in review history

### 4. Review History
- View all reviewed requests (approved/rejected/expired)
- Filter by status, date range, or reviewer
- Complete audit trail of all review decisions

### 5. Statistics Dashboard
- Pending requests count
- Urgent requests (< 6 hours remaining)
- Total approved/rejected counts
- Real-time updates

## Implementation Details

### Backend API

**Module:** `src/teacher_review_api.py`

#### Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/teacher-review/pending-requests` | Get all pending requests | Teacher/Admin |
| POST | `/teacher-review/approve/<id>` | Approve a request | Teacher/Admin |
| POST | `/teacher-review/deny/<id>` | Deny a request | Teacher/Admin |
| GET | `/teacher-review/history` | Get review history | Teacher/Admin |
| GET | `/teacher-review/stats` | Get statistics | Teacher/Admin |

#### API Examples

**Get Pending Requests:**
```bash
GET /teacher-review/pending-requests
```

Response:
```json
{
  "success": true,
  "total": 2,
  "requests": [
    {
      "id": 1,
      "student_id": 5,
      "student_name": "John Doe",
      "course_id": "CS101",
      "date": "2025-11-15",
      "current_status": "absent",
      "requested_status": "present",
      "reason": "I was present but system marked me absent",
      "submitted_at": "2025-11-17T10:00:00",
      "hours_remaining": 35.5,
      "is_urgent": false
    }
  ]
}
```

**Approve Request:**
```bash
POST /teacher-review/approve/1
Content-Type: application/json

{
  "notes": "Verified with attendance log. Approved."
}
```

Response:
```json
{
  "success": true,
  "message": "Correction request approved successfully",
  "request": {
    "id": 1,
    "status": "approved",
    "reviewed_at": "2025-11-17T14:30:00",
    "reviewed_by": "Prof. Smith",
    "admin_notes": "Verified with attendance log. Approved."
  }
}
```

**Deny Request:**
```bash
POST /teacher-review/deny/2
Content-Type: application/json

{
  "notes": "No valid documentation provided."
}
```

Response:
```json
{
  "success": true,
  "message": "Correction request denied",
  "request": {
    "id": 2,
    "status": "rejected",
    "reviewed_at": "2025-11-17T14:35:00",
    "reviewed_by": "Prof. Smith",
    "admin_notes": "No valid documentation provided."
  }
}
```

### Frontend UI

**Template:** `src/templates/teacher_review.html`

#### Features
- **Statistics Cards**: Real-time counts of pending, urgent, approved, rejected requests
- **Request Cards**: Rich display of each request with student details, time remaining, and action buttons
- **Urgent Indicators**: Red border and badge for requests with < 6 hours remaining
- **Modal Dialogs**: Confirmation modals for approve/deny actions
- **Filter View**: Switch between pending requests and review history
- **Auto-refresh**: Manual refresh button to reload pending requests

### Database Updates

**Model:** `AttendanceCorrectionRequest` (in `src/models.py`)

Added status: `'expired'` to existing statuses (`'pending'`, `'approved'`, `'rejected'`, `'cancelled'`)

### Integration

**Routes registered in:** `src/main.py`
```python
from teacher_review_api import teacher_review_bp
app.register_blueprint(teacher_review_bp)
```

**Dashboard link added to:** `src/templates/faculty_dashboard.html`
- "Review Pending Requests" button
- "View Review History" button

## Business Rules

### 48-Hour Window
1. **Submission**: Student submits correction request
2. **Window Opens**: 48-hour countdown begins immediately
3. **Teacher Review**: Teacher must review within 48 hours
4. **Auto-Expire**: If not reviewed within 48 hours, status → `'expired'`
5. **No Late Reviews**: Cannot approve/deny expired requests

### Approval Process
- Attendance record updated to requested status
- Request marked as `'approved'`
- Optional notes added by teacher
- Audit log entry created

### Denial Process
- Attendance record remains unchanged
- Request marked as `'rejected'`
- **Mandatory** notes explaining denial reason
- Audit log entry created

### Permissions
- **Teacher Role**: Can review all requests
- **Admin Role**: Can review all requests
- **Student Role**: Cannot access review endpoints

## Testing

### Unit Tests

**File:** `tests/unit/test_teacher_review.py`

Test coverage:
- ✅ Fetch pending requests
- ✅ Approve request with notes
- ✅ Deny request (requires notes)
- ✅ Auto-expire requests after 48 hours
- ✅ Get review statistics
- ✅ Permission enforcement
- ✅ 48-hour window validation

Run tests:
```bash
pytest tests/unit/test_teacher_review.py -v
```

### Manual Testing Checklist

- [ ] Teacher can see pending requests
- [ ] Time remaining displays correctly
- [ ] Urgent badge shows for < 6 hours
- [ ] Approve button updates attendance
- [ ] Deny button requires notes
- [ ] Expired requests auto-marked
- [ ] Statistics update after actions
- [ ] History shows reviewed requests
- [ ] Only teachers/admins can access

## Security

### Authentication
- All endpoints require `@login_required`
- Role-based access control via `@require_role('teacher', 'admin')`

### Authorization
- Teachers can only review (not create) requests
- Students cannot access review endpoints
- Audit trail logs all review actions

### Data Validation
- Request ID validated (must exist)
- Status validated (must be 'pending')
- 48-hour window enforced
- Notes required for denial

## Performance Considerations

### Auto-Expiration
- Runs on every `/pending-requests` call
- Efficient: Only checks pending requests older than 48h
- Database indexed on `submitted_at` for fast queries

### Optimization Opportunities
- Consider background job for expiration (cron/celery)
- Cache statistics for high-traffic scenarios
- Paginate history for large datasets

## Audit Trail Integration

All review actions logged via `log_audit_event()`:
- **Action**: `approve_correction_request` or `deny_correction_request`
- **Entity**: `correction_request`
- **Details**: Student ID, course ID, date, status change, notes

## Future Enhancements

1. **Email Notifications**
   - Notify student when request is reviewed
   - Remind teacher of urgent requests

2. **Bulk Actions**
   - Approve/deny multiple requests at once
   - Batch processing for efficiency

3. **Analytics Dashboard**
   - Approval rate by teacher
   - Average review time
   - Most common denial reasons

4. **Escalation System**
   - Auto-escalate to admin if teacher doesn't respond
   - Priority queue for urgent requests

5. **Mobile App Support**
   - Push notifications for urgent requests
   - Quick approve/deny from mobile

## Troubleshooting

### Common Issues

**Issue**: Old requests not expiring
- **Solution**: Check that `/pending-requests` endpoint is being called

**Issue**: Cannot approve/deny request
- **Solution**: Verify teacher is logged in with correct role

**Issue**: Attendance not updating after approval
- **Solution**: Check attendance record exists for that date

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Compliance

- **FERPA**: Student data protected, audit trail maintained
- **SOC 2**: All actions logged with timestamp and user
- **Data Retention**: Review history retained for audit purposes

## Related Features

- **SAS-98**: Student Correction Request Submission
- **SAS-94**: Audit Trail Logging
- **SAS-88**: Role-Based Access Control

## Support

For issues or questions:
1. Check this documentation
2. Review test cases for usage examples
3. Check audit logs for action history
4. Contact development team

---

**Last Updated**: November 17, 2025  
**Version**: 1.0  
**Feature**: SAS-99 - Teacher Review of Correction Requests
