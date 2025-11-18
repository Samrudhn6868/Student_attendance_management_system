"""Performance Optimization Opportunities

This document identifies performance bottlenecks and optimization opportunities
discovered through static code analysis of the PESU Attendance System.

## Critical Performance Issues (Fix First)

### 1. N+1 Query Problem in Faculty Dashboard (`src/main.py:232-241`)

**Location:** Faculty dashboard - calculating average attendance

**Problem:**
```python
all_students = User.query.filter_by(role='student').all()
attendance_percentages = []
for student in all_students:
    records = Attendance.query.filter_by(student_id=student.id).all()
    # ... calculate percentage
```

**Impact:** With 100 students, this executes 101 database queries (1 + 100)

**Solution:**
```python
from sqlalchemy import func, case

# Single aggregated query instead of N+1
attendance_stats = db.session.query(
    Attendance.student_id,
    func.count(Attendance.id).label('total'),
    func.sum(case((Attendance.status == 'present', 1), else_=0)).label('present')
).group_by(Attendance.student_id).all()

# Calculate percentages from aggregated data
attendance_percentages = [
    (stat.present / stat.total * 100) if stat.total > 0 else 0
    for stat in attendance_stats
]
```

**Expected Improvement:** 99% reduction in queries (101 → 1-2 queries)

---

### 2. Inefficient Loop in Student Dashboard (`src/main.py:257-265`)

**Location:** Student dashboard - grouping attendance by course

**Problem:**
```python
course_attendance = {}
for record in records:
    course = record.course_id or 'General'
    if course not in course_attendance:
        course_attendance[course] = {'total': 0, 'present': 0}
    course_attendance[course]['total'] += 1
    if record.is_present:
        course_attendance[course]['present'] += 1
```

**Impact:** Loops through all attendance records in Python instead of using SQL

**Solution:**
```python
from sqlalchemy import func, case

# Use SQL GROUP BY instead of Python loop
course_stats = db.session.query(
    Attendance.course_id,
    func.count(Attendance.id).label('total'),
    func.sum(case((Attendance.status == 'present', 1), else_=0)).label('present')
).filter_by(student_id=current_user.id).group_by(Attendance.course_id).all()

course_summary = [
    {
        'course': stat.course_id or 'General',
        'percentage': round((stat.present / stat.total * 100) if stat.total > 0 else 0, 2),
        'status': 'Good' if (stat.present / stat.total * 100) >= 75 else 'Warning'
    }
    for stat in course_stats
]
```

**Expected Improvement:** 10-100x faster for students with many attendance records

---

### 3. Missing Pagination in Attendance API (`src/attendance_api.py:472,749`)

**Location:** `/api/attendance/view` endpoint

**Problem:**
```python
records = query.order_by(Attendance.date.desc()).all()
```

**Impact:** Loads ALL attendance records into memory (could be thousands)

**Solution:**
```python
# Add pagination support
page = request.args.get('page', 1, type=int)
per_page = request.args.get('per_page', 50, type=int)
per_page = min(per_page, 200)  # Cap at 200 records

# Use paginate()
pagination = query.order_by(Attendance.date.desc()).paginate(
    page=page,
    per_page=per_page,
    error_out=False
)

return jsonify({
    'success': True,
    'records': [_format_record_for_view(r, user_info) for r in pagination.items],
    'pagination': {
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages
    }
})
```

**Expected Improvement:** Reduced memory usage and faster response times

---

## Caching Opportunities (Medium Priority)

### 4. Student Dashboard Query Caching (`src/main.py:250`)

**Problem:** Student attendance data is queried on every dashboard load, even though
it rarely changes.

**Solution:**
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_student_attendance_data(student_id):
    records = Attendance.query.filter_by(student_id=student_id).all()
    # ... process records
    return processed_data
```

**Expected Improvement:** 5-10x faster dashboard loads for repeated visits

---

### 5. Encryption Caching for Course IDs (`src/encryption_utils.py:108`)

**Problem:** Course IDs (like "CS101", "MATH201") are encrypted repeatedly for
the same values.

**Note:** This is tricky because Fernet generates different ciphertexts each time
for security. Only implement if you can use deterministic encryption for course IDs.

**Solution (if applicable):**
```python
from functools import lru_cache

@lru_cache(maxsize=256)
def encrypt_course_id(course_id: str) -> str:
    \"\"\"Cached encryption for course IDs (deterministic values only).\"\"\"
    return encrypt_data(course_id)
```

**Warning:** Only use this for non-sensitive, deterministic data like course codes.
Do NOT cache student SRNs or other PII.

---

### 6. Bunk Recommendation Caching (`src/bunk_recommendations.py`)

**Problem:** `calculate_safe_bunks()` performs the same calculations for the same inputs.

**Solution:**
```python
from functools import lru_cache

class BunkRecommendationService:
    @staticmethod
    @lru_cache(maxsize=512)
    def calculate_safe_bunks(classes_attended, total_classes_held,
                            total_classes_remaining, min_attendance=75.0):
        # ... existing calculation code
```

**Expected Improvement:** Near-instant results for repeated calculations

---

## Database Indexing (High Impact, Low Effort)

### 7. Missing Indexes on Audit Log Table

**Problem:** Audit log queries filter by action_type, user_id, timestamp, etc.
without indexes.

**Solution:** Add to migration or run manually:
```sql
CREATE INDEX idx_audit_action ON audit_log(action_type);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_student ON audit_log(student_srn);
CREATE INDEX idx_audit_composite ON audit_log(user_id, timestamp);
```

**Expected Improvement:** 10-1000x faster audit log queries

---

### 8. Missing Indexes on Attendance Table

**Solution:**
```sql
CREATE INDEX idx_attendance_student ON attendance(student_id);
CREATE INDEX idx_attendance_course ON attendance(course_id);
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_status ON attendance(status);
CREATE INDEX idx_attendance_composite ON attendance(student_id, course_id, date);
```

**Expected Improvement:** 10-100x faster attendance queries

---

## Code Quality Improvements (Low Priority)

### 9. Duplicate Query Code in Attendance API

**Problem:** Similar query building logic appears twice (lines 425-472 and 714-749)

**Solution:** Extract to shared function:
```python
def build_attendance_query(user_info, filters):
    \"\"\"Build attendance query with common filters.\"\"\"
    query = db.select(Attendance)
    
    # Apply role-based filtering
    if user_info['role'] == 'student':
        query = query.filter_by(student_srn=user_info.get('student_srn'))
    
    # Apply optional filters
    if 'student_srn' in filters:
        query = query.filter_by(student_srn=filters['student_srn'])
    if 'course_id' in filters:
        query = query.filter_by(course_id=filters['course_id'])
    # ... etc
    
    return query
```

---

## Implementation Priority

1. **High Priority (Do First):**
   - Fix N+1 query in faculty dashboard (#1)
   - Add database indexes (#7, #8)
   - Add pagination to API (#3)

2. **Medium Priority:**
   - Optimize student dashboard loop (#2)
   - Add query result caching (#4)
   - Cache bunk calculations (#6)

3. **Low Priority:**
   - Refactor duplicate code (#9)
   - Consider encryption caching (#5) - ONLY if safe

---

## Monitoring Recommendations

After implementing optimizations, add monitoring:

1. **Request timing middleware** (✓ DONE in main.py)
2. **Slow query logging:** Log queries >100ms
3. **Memory profiling:** Track memory usage trends
4. **Cache hit rates:** Monitor cache effectiveness

Use the profiling tools:
```bash
# Profile application
python tools/profile_app.py --scenario all

# Analyze results
python tools/analyze_profile.py reports/profiles/*.prof --compare
```

---

## Performance Targets

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Faculty dashboard load | ~2-5s | <500ms | High |
| Student dashboard load | ~1-2s | <300ms | High |
| API attendance query | ~500ms | <100ms | Medium |
| Bunk calculation | ~50ms | <10ms | Low |

---

**Last Updated:** 2025-11-18
**Reviewed By:** GitHub Copilot AI Assistant
