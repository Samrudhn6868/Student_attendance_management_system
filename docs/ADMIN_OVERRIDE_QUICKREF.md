# Admin Override - Quick Reference

## Quick Start

### Access the Feature
```
Navigate to: /admin/override-attendance
OR
Dashboard → Attendance Override (link in navbar)
```

## One-Minute Overview

**What it does**: Admins directly modify any student's attendance without a student request.

**Three main tabs**:
1. **Override Attendance** - Search student, select record, override
2. **Override History** - See all overrides with reasons
3. **Statistics** - View override trends and admin breakdown

## Common Tasks

### Task 1: Override a Student's Attendance

1. Go to **Override Attendance** tab
2. In "Search Student" field: type student name/username
3. Click on student from dropdown
4. Click on attendance date you want to change
5. New status auto-selects (opposite of current)
6. Enter reason (5-500 chars) - **required**
7. Click "Override Attendance"

**Expected result**: "Override Successful" toast, record updated

---

### Task 2: View Override History

1. Click **Override History** tab
2. System auto-loads last 50 overrides
3. See:
   - Student name and date
   - New status with badge color
   - Reason why override was made
   - Which admin made it
   - When it happened

**Example**: 
```
Jane Smith - 2024-01-18
absent → Present ✓ (yellow badge = overridden)
"Lab participation verified by faculty"
By: Admin User, 3 days ago
```

---

### Task 3: Check Override Statistics

1. Click **Statistics** tab
2. See:
   - **Total Overrides**: X
   - **Override Percentage**: Y% (of all records)
   - **By Admin Table**: Who made how many overrides

**Use for**: Auditing, ensuring fair distribution of overrides

---

### Task 4: Undo an Override

1. Go to **Override Attendance** tab
2. Search and select student
3. Click on overridden record (has yellow badge)
4. Click **"Clear Selection"** button
5. Go to **Override History**
6. Find the override entry
7. (Coming soon: Undo button in history)

**Alternative**: API direct call:
```bash
POST /api/admin/override/attendance/{id}/undo
```

---

### Task 5: Find Students

1. In "Search Student" field: type **minimum 2 characters**
2. Wait for autocomplete dropdown
3. Click student name from results

**Works with**:
- Student first/last name
- Username
- Email prefix

---

## API Endpoints (for Integration)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/admin/override/attendance/{id}` | Override a record |
| POST | `/api/admin/override/attendance/{id}/undo` | Remove override |
| GET | `/api/admin/override/student/{id}/records` | Get student's records |
| GET | `/api/admin/override/override-history` | View all overrides |
| GET | `/api/admin/override/search-students` | Find students |
| GET | `/api/admin/override/stats` | Get statistics |

---

## API Usage Examples

### Override Attendance
```bash
curl -X POST http://localhost:5000/api/admin/override/attendance/123 \
  -H "Content-Type: application/json" \
  -d '{
    "new_status": "present",
    "reason": "System error corrected"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Attendance overridden successfully",
  "record": {
    "id": 123,
    "status": "present",
    "is_overridden": true,
    "override_reason": "System error corrected",
    "override_timestamp": "2024-01-20T14:30:00"
  }
}
```

---

### Get Student's Records
```bash
curl http://localhost:5000/api/admin/override/student/10/records?from_date=2024-01-01&to_date=2024-01-31
```

**Response**:
```json
{
  "success": true,
  "student": {"id": 10, "name": "John Doe"},
  "total_records": 25,
  "records": [
    {
      "id": 101,
      "date": "2024-01-20",
      "status": "present",
      "is_overridden": false
    }
  ]
}
```

---

### Get Override History
```bash
curl http://localhost:5000/api/admin/override/override-history?limit=10
```

---

### Search Students
```bash
curl http://localhost:5000/api/admin/override/search-students?query=john
```

---

### Get Statistics
```bash
curl http://localhost:5000/api/admin/override/stats
```

---

## Form Validation

### Reason Field
- **Minimum**: 5 characters
- **Maximum**: 500 characters
- **Required**: Yes
- **Character counter**: Shows current/max count

**Valid**: "System error corrected by admin"
**Invalid**: "Bad" (too short)

### New Status
- **Options**: "present" or "absent"
- **Required**: Yes
- **Default**: Auto-selects opposite of current

### Student Search
- **Minimum**: 2 characters
- **Required**: Yes
- **Auto-complete**: Loads as you type

---

## Status Badges & Colors

| Badge | Color | Meaning |
|-------|-------|---------|
| Present | Green | Marked present |
| Absent | Red | Marked absent |
| Overridden | Yellow | Record was overridden by admin |

---

## Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Reason must be 5-500 characters" | Reason too short/long | Type 5-500 chars |
| "Admin access required" | Not admin user | Use admin account |
| "Record not found" | ID doesn't exist | Refresh and try again |
| "Query must be 2+ characters" | Search too short | Type at least 2 chars |
| "Invalid status" | Wrong status value | Use "present" or "absent" |
| "Student not found" | No matching student | Check spelling |

---

## Permission & Access

### Who Can Access?
✅ **Admin users only**

### What Happens If I Try to Access as Non-Admin?
❌ Redirected to login or get "403 Forbidden" error

### How to Get Admin Role?
- Database: Set `role='admin'` in users table
- Contact: System administrator

---

## Audit & Compliance

### What Gets Tracked?
- ✅ Student name and ID
- ✅ Date of attendance
- ✅ New status (present/absent)
- ✅ Reason for override
- ✅ Admin who made override (ID & name)
- ✅ Exact timestamp

### Where to Review?
- **UI**: Override History tab
- **API**: `/api/admin/override/override-history`
- **Database**: `attendance` table fields:
  - `is_overridden`
  - `override_reason`
  - `overridden_by` (admin user ID)
  - `override_timestamp`

### How Long Is History Kept?
- **Permanently** - All overrides kept for full audit trail
- Can be filtered/searched by date range

---

## Keyboard Shortcuts

- **Ctrl+K** or **Cmd+K**: Focus search field (when on page)
- **Escape**: Clear search results
- **Tab**: Navigate between form fields
- **Enter**: Submit form (when all fields valid)

---

## Troubleshooting Quick Fixes

### Problem: Can't find student
**Solution**: 
- Try searching by username instead of name
- Use first name or last name individually
- Check spelling

### Problem: "Reason must be 5-500 characters"
**Solution**:
- Check minimum 5 characters
- Character counter shows: current/max
- Example: "System glitch found and corrected" (✓)

### Problem: Can't access `/admin/override-attendance`
**Solution**:
- Verify you're logged in
- Check user role is 'admin' in database
- Try logging out and back in

### Problem: Override not saving
**Solution**:
- Ensure all fields filled (status + reason)
- Check reason is 5-500 characters
- Try refreshing page and retry
- Check browser console for errors

### Problem: Statistics showing wrong numbers
**Solution**:
- Refresh the Statistics tab
- Clear browser cache
- Manually reload page

---

## Tips & Best Practices

### Do's ✅
- ✅ Always provide clear, specific reason
- ✅ Document system errors as reason
- ✅ Use consistent reason format for similar issues
- ✅ Review Override History regularly for auditing
- ✅ Use Statistics to identify patterns

### Don'ts ❌
- ❌ Don't override without valid reason
- ❌ Don't use vague reasons like "just because"
- ❌ Don't override as workaround for system bugs
- ❌ Don't mass-override without documentation

---

## Integration with Other Features

### vs. Correction Requests
- **Correction Requests**: Student initiated, needs approval
- **Admin Override**: Admin initiated, immediate effect
- **Both can coexist**: Student can request AND admin can override

### vs. Mark Attendance
- **Mark Attendance**: Faculty marks during/after class
- **Admin Override**: Corrects marked attendance

---

## Performance Notes

### Search Performance
- Searches are **debounced** (300ms delay)
- Returns max 20 results by default
- Indexed on username/name for speed

### History Load
- Default limit: 50 records
- Maximum limit: 1000 records
- Can paginate with offset parameter

### Statistics Cache
- Updated in real-time
- May take 1-2 seconds to calculate

---

## Database Info (For Developers)

### Relevant Fields in `attendance` Table
```sql
ALTER TABLE attendance ADD COLUMN is_overridden BOOLEAN DEFAULT FALSE;
ALTER TABLE attendance ADD COLUMN override_reason VARCHAR(500);
ALTER TABLE attendance ADD COLUMN overridden_by INTEGER;
ALTER TABLE attendance ADD COLUMN override_timestamp VARCHAR;
```

### Query to View All Overrides
```sql
SELECT 
  a.id, 
  u.name as student_name,
  a.date,
  a.status,
  a.override_reason,
  admin.name as overridden_by_name,
  a.override_timestamp
FROM attendance a
JOIN user u ON a.student_id = u.id
LEFT JOIN user admin ON a.overridden_by = admin.id
WHERE a.is_overridden = TRUE
ORDER BY a.override_timestamp DESC;
```

---

## FAQ

**Q: Can I override an override?**
A: Yes! If a record is already overridden, you can override it again. Previous reason is kept, new override creates new history entry.

**Q: What if I undo an override by mistake?**
A: Check Override History to see what the original status was, then override again if needed.

**Q: Can students see overrides?**
A: Yes, in their attendance view they'll see "Overridden" status. Reason visible only to admins.

**Q: Does student correction request still work if override exists?**
A: Yes! Both systems are independent. Student can still submit a correction request even if record is overridden.

**Q: How do I bulk override multiple students?**
A: Currently one-by-one. Bulk override feature planned for future version.

**Q: Is there a limit to how many overrides I can make?**
A: No limit, but all are tracked in history for audit purposes.

**Q: Can I filter override history by reason?**
A: Not yet - planned for future version. Can search using browser's Ctrl+F on history tab.

---

## Support

**Report Issues**:
1. Check troubleshooting section
2. Review test cases for usage examples
3. Check browser console for errors
4. Contact system administrator

**Documentation**:
- Full docs: `docs/ADMIN_OVERRIDE_FEATURE.md`
- Tests: `tests/test_admin_override.py`
- Code: `src/admin_override_api.py`

---

**Version**: 1.0  
**Last Updated**: 2024-01-20  
**Status**: Production Ready ✅
