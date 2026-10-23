# Bunk Allowance & Recommendations Feature - Complete Analysis & Integration

## 📋 Executive Summary

The **Bunk Allowance** feature (SAS-96) is **fully functional** and working properly. It now includes:
- ✅ Course-level bunk allowance policies
- ✅ Per-student attendance tracking
- ✅ Safe bunk day calculations
- ✅ Intelligent recommendations
- ✅ **Frontend integration on student dashboard** (NEW)

---

## 🔍 Feature Breakdown

### 1️⃣ **Bunk Allowance Models** (`bunk_allowance_models.py`)

#### CourseConfig Model
Stores course-level configuration:
```
- course_id: Unique course identifier (e.g., 'CS101')
- course_name: Full course name (e.g., 'Data Structures')
- total_classes: Total classes in the course (default: 60)
- bunk_allowance_percentage: % of classes that can be bunked (default: 25%)
- min_attendance_percentage: Minimum required attendance (default: 75%)
```

**Methods:**
- `get_max_bunk_allowed()`: Calculates max classes that can be bunked
- `get_min_classes_required()`: Calculates minimum classes required
- `to_dict()`: Converts to dictionary for API responses

#### StudentBunkAllowance Model
Tracks per-student, per-course attendance:
- Caches student attendance data for quick lookups
- Automatically calculates remaining bunks
- Provides bunk allowance details

---

### 2️⃣ **Bunk Allowance Service** (`bunk_allowance_service.py`)

**Key Methods:**

#### `get_or_create_course_config()`
- Creates or retrieves course configuration
- Supports custom bunk allowance policies per course

#### `calculate_student_attendance_stats()`
- Queries attendance records for student-course combination
- Returns:
  - `total_classes_held`: Classes held so far
  - `classes_attended`: Classes student attended
  - `classes_missed`: Classes student missed
  - `attendance_percentage`: Current attendance %

#### `update_student_bunk_allowance()`
- Updates student's bunk tracking
- Calculates remaining bunks available

#### `get_student_bunk_allowance()`
- Retrieves bunk allowance data for a student

#### `get_remaining_classes_breakdown()`
- Detailed class projections and bunk calculations

---

### 3️⃣ **Bunk Recommendations Service** (`bunk_recommendations.py`)

**Purpose:** Provides intelligent recommendations for safe bunk days

#### `calculate_safe_bunks()` Method

**Input Parameters:**
- `classes_attended`: Classes already attended
- `total_classes_held`: Classes held so far
- `total_classes_remaining`: Estimated remaining classes (default: 10)
- `min_attendance`: Minimum required percentage (default: 75%)

**Returns:**
```python
{
    'safe_bunks': 7,                                    # Can safely bunk
    'current_percentage': 87.5,                         # Current attendance %
    'classes_attended': 35,                             # Classes attended
    'total_classes_held': 40,                           # Total held so far
    'classes_missed': 5,                                # Classes missed
    'total_classes_remaining': 10,                      # Remaining
    'total_classes_semester': 50,                       # Total in semester
    'min_attendance_required': 75.0,                    # Minimum %
    'status': 'safe',                                   # Status (safe, warning, critical, no_bunks)
    'message': 'You can safely bunk 7 class(es)...',  # Main message
    'recommendations': [                                # List of recommendations
        '✅ You have 7 safe bunks available',
        'Distribute them wisely across remaining weeks',
        'Keep attendance above 80.0% for safety buffer',
        'Suggested: ~3.5 bunk(s) per week maximum'
    ]
}
```

#### Status Types:
1. **safe**: Student has bunks available and attendance is healthy
2. **warning**: Attendance is close to minimum (75-80%)
3. **critical**: Attendance is below minimum - cannot bunk
4. **no_bunks**: All bunk allowance exhausted
5. **low_bunks**: Only 1-2 bunks left
6. **no_data**: No attendance records yet

---

## 🌐 REST API Endpoints (bunk_allowance_api.py)

### Student Endpoints:
```
GET /api/bunk-allowance/student/<srn>
  - Get bunk allowance for all courses

GET /api/bunk-allowance/student/<srn>/course/<course_id>
  - Get bunk allowance for specific course

GET /api/bunk-allowance/breakdown/<srn>/<course_id>
  - Get detailed breakdown with projections
```

### Faculty/Admin Endpoints:
```
GET /api/bunk-allowance/course/<course_id>/students
  - Get all students' bunk status in a course

GET /api/bunk-allowance/critical
  - Get students with critical attendance

POST /api/bunk-allowance/course/config
  - Create/update course configuration

GET /api/bunk-allowance/course/<course_id>/config
  - Get course configuration

PUT /api/bunk-allowance/course/<course_id>/refresh
  - Refresh bunk calculations for all students
```

**Authentication:** Supports both session-based (Flask-Login) and JWT token auth

---

## 🎨 Frontend Integration (NEW)

### Changes Made:

#### 1. **Backend Route** (`src/main.py` - `/dashboard` route)
```python
# Added bunk recommendations calculation
bunk_recommendations = BunkRecommendationService.calculate_safe_bunks(
    classes_attended=present_count,
    total_classes_held=total_classes,
    total_classes_remaining=10,
    min_attendance=75.0
)

# Pass to template
return render_template('student_dashboard.html',
    total_classes=total_classes,
    present_count=present_count,
    absence_count=absence_count,
    attendance_percentage=round(percentage, 2),
    course_summary=course_summary,
    bunk_recommendations=bunk_recommendations)  # NEW
```

#### 2. **Frontend Template** (`src/templates/student_dashboard.html`)

**Added:** "Bunk Allowance & Recommendations" card showing:

##### Status Section:
- Color-coded status badge (green=safe, yellow=warning, red=critical)
- Visual icons for each status

##### Key Metrics Table:
| Metric | Value |
|--------|-------|
| Safe Bunks Left | 7 |
| Current Attendance | 87.5% |
| Classes Attended | 35 |
| Classes Held | 40 |

##### Alert Box:
- Displays the main recommendation message
- Changes based on attendance status

##### Recommendations List:
- 3-5 personalized recommendations
- Tips for maintaining attendance
- Safe bunk distribution suggestions

##### Empty State:
- Shows message when no attendance records exist yet
- Gracefully handles when feature is unavailable

---

## ✅ Feature Status - Test Results

### Test 1: Bunk Allowance Calculations
```
✓ Course configuration working
✓ Attendance statistics calculated correctly
✓ Bunk allowance calculations functional
✓ Safe bunk recommendations generating
✓ Different scenarios handled properly
```

### Test 2: Different Attendance Scenarios

| Attendance | Safe Bunks | Status | Message |
|-----------|-----------|--------|---------|
| 95% | 10 | safe | You can safely bunk 10 classes |
| 75% | 2 | warning | Attendance is close to minimum |
| 70% | 0 | critical | Attendance is below 75%! |
| 50% | 0 | critical | Cannot bunk any classes |

### Test 3: Dashboard Integration
```
✓ Attendance data calculated correctly
✓ Course-wise summary generated
✓ Bunk allowance recommendations created
✓ Status badges (safe, warning, critical) implemented
✓ Recommendations list displayed to student
✓ Empty state handled gracefully
```

---

## 🚀 How It Works End-to-End

```
1. Teacher marks attendance for students
   ↓
2. System updates Attendance table
   ↓
3. Student views dashboard
   ↓
4. Dashboard route queries student's attendance records
   ↓
5. Route groups data by course and calculates statistics
   ↓
6. Route calls BunkRecommendationService.calculate_safe_bunks()
   ↓
7. Service analyzes:
   - Current attendance percentage
   - Remaining classes in semester
   - Safe bunk threshold (75%)
   ↓
8. Returns status and recommendations
   ↓
9. Template dynamically renders:
   - Status badge (safe/warning/critical)
   - Safe bunks available
   - Personalized recommendations
```

---

## 📊 Example Student Dashboard Display

### Current Status (Safe)
```
Bunk Allowance
─────────────
Current Status: ✅ Safe

Safe Bunks Left:      7
Current Attendance:   87.5%
Classes Attended:     35
Classes Held:         40

⚠️ Message: You can safely bunk 7 class(es) while maintaining 75% attendance.

💡 Recommendations:
   → ✅ You have 7 safe bunks available
   → Distribute them wisely across remaining weeks
   → Keep attendance above 80% for safety buffer
   → Suggested: ~3.5 bunk(s) per week maximum
```

### Critical Status Example
```
Bunk Allowance
─────────────
Current Status: ⚠️ Critical

Safe Bunks Left:      0
Current Attendance:   70%
Classes Attended:     28
Classes Held:         40

🚨 Message: WARNING: Attendance is below 75%! You cannot bunk any classes.

💡 Recommendations:
   → 🚨 URGENT: Attend ALL remaining classes
   → You need perfect attendance to recover above 75%
   → Consider requesting official leave if you must miss
```

---

## 🔧 Configuration

### Course Configuration (per-course basis):
```python
CourseConfig(
    course_id='CS101',
    course_name='Data Structures',
    total_classes=50,
    bunk_allowance_percentage=25.0,    # 25% = 12.5 classes
    min_attendance_percentage=75.0     # 75% = 37.5 classes
)
```

### Recommendation Thresholds (built-in):
- **Safe**: Attendance ≥ 80%
- **Borderline**: 75% ≤ Attendance < 80%
- **Critical**: Attendance < 75%
- **Target Buffer**: 80% (5% above minimum)

---

## 📁 Files Modified

### Backend (no changes - feature already working):
- `src/bunk_allowance_models.py` - Unchanged
- `src/bunk_allowance_service.py` - Unchanged
- `src/bunk_recommendations.py` - Unchanged
- `src/bunk_allowance_api.py` - Unchanged

### Frontend (NEWLY INTEGRATED):
- `src/main.py` - Updated `/dashboard` route to calculate and pass bunk recommendations
- `src/templates/student_dashboard.html` - Added bunk allowance section with recommendations

---

## ✨ Features & Benefits

### For Students:
✅ **Real-time bunk tracking** - Know exactly how many safe bunks available
✅ **Smart recommendations** - Personalized advice based on attendance
✅ **Risk awareness** - Clear status indicators (safe/warning/critical)
✅ **Strategic planning** - Distribute bunks wisely across semester

### For Faculty/Admins:
✅ **Course policies** - Set different allowances per course
✅ **Student monitoring** - Identify at-risk students via API
✅ **Bulk updates** - Update all students in a course at once
✅ **REST API** - Full API access for integrations

---

## 🧪 Testing Evidence

All test scripts available:
- `test_bunk_allowance.py` - Core feature testing
- `test_dashboard_bunk.py` - Frontend integration testing

Run tests:
```bash
python test_bunk_allowance.py
python test_dashboard_bunk.py
```

---

## 📝 Summary

The Bunk Allowance feature is **production-ready** with full frontend integration. Students can now see:
- How many classes they can safely bunk
- Their current attendance percentage
- Personalized recommendations based on status
- Color-coded status indicators
- Details about their bunk allowance

The feature integrates seamlessly with the existing attendance system and provides intelligent, context-aware recommendations to help students maintain healthy attendance while managing their study-life balance.
