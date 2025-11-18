# Instrumentation & Profiling Guide

## Quick Start

### 1. Health Check

Test if the application is running and database is connected:

```bash
# Start the app
python src/main.py

# In another terminal, test health endpoint
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T10:30:00",
  "service": "PESU Attendance System",
  "version": "1.0.0",
  "database": {
    "status": "connected",
    "type": "SQLAlchemy",
    "dialect": "sqlite"
  },
  "statistics": {
    "total_users": 3,
    "students": 1,
    "teachers": 1,
    "admins": 1
  }
}
```

### 2. Request Timing

The application automatically logs slow requests (>1 second):

```
⚠️  SLOW REQUEST: GET /dashboard -> 200 (1.234s)
```

Check response time in headers:
```bash
curl -I http://localhost:5000/dashboard
# Look for: X-Response-Time: 0.123456s
```

### 3. Profile the Application

#### Run All Profiling Scenarios

```bash
# Setup test data and run all scenarios
python tools/profile_app.py --setup --scenario all
```

This will:
- Create 100 test students
- Generate 5000 attendance records
- Profile 4 scenarios
- Save results to `reports/profiles/`

#### Run Specific Scenario

```bash
# Profile student dashboard only
python tools/profile_app.py --scenario student_dashboard

# Profile with custom output name
python tools/profile_app.py --scenario faculty_dashboard --output my_profile.prof
```

Available scenarios:
- `student_dashboard` - Student dashboard loading
- `faculty_dashboard` - Faculty dashboard loading
- `attendance_submit` - Attendance submission workflow
- `bunk_calculation` - Bunk allowance calculations
- `all` - Run all scenarios (default)

### 4. Analyze Profile Results

#### Basic Analysis

```bash
# Analyze a single profile
python tools/analyze_profile.py reports/profiles/student_dashboard_20251118_103000.prof
```

#### Show Top 50 Functions

```bash
python tools/analyze_profile.py reports/profiles/student_dashboard.prof --top 50
```

#### Sort by Different Criteria

```bash
# Sort by total time (default: cumulative)
python tools/analyze_profile.py reports/profiles/student_dashboard.prof --sort tottime

# Sort by number of calls
python tools/analyze_profile.py reports/profiles/student_dashboard.prof --sort calls
```

#### Compare Multiple Profiles

```bash
# Compare all profiles
python tools/analyze_profile.py reports/profiles/*.prof --compare

# Compare specific scenarios
python tools/analyze_profile.py reports/profiles/student_*.prof reports/profiles/faculty_*.prof --compare
```

#### Find Bottlenecks

```bash
# Find functions taking >10% of total time
python tools/analyze_profile.py reports/profiles/student_dashboard.prof --bottlenecks --threshold 10

# Find functions taking >5% (more sensitive)
python tools/analyze_profile.py reports/profiles/student_dashboard.prof --bottlenecks --threshold 5
```

#### Generate Detailed Report

```bash
# Save comprehensive report to file
python tools/analyze_profile.py reports/profiles/student_dashboard.prof --report analysis_report.txt

# Generate reports for all profiles
python tools/analyze_profile.py reports/profiles/*.prof --report full_analysis.txt
```

## Using the Profiling Decorators

### Time a Function

```python
from tools.profiling import timed

@timed
def my_slow_function():
    # ... code
    return result
```

This will print execution time and log to `reports/timing.json`.

### Profile a Function

```python
from tools.profiling import profile

@profile('my_function.prof')
def my_function():
    # ... code
    return result
```

This generates a `.prof` file in `reports/profiles/`.

### Track Memory Usage

```python
from tools.profiling import memory_tracked

@memory_tracked
def memory_intensive_function():
    # ... code
    return result
```

This prints memory delta before and after execution.

## Understanding Profile Output

### Reading the Stats

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1234    0.100    0.000    0.500    0.000 models.py:42(query_students)
```

- **ncalls**: Number of times function was called
- **tottime**: Total time spent in function (excluding subcalls)
- **percall**: tottime / ncalls
- **cumtime**: Total time including subcalls
- **percall**: cumtime / ncalls

### What to Look For

1. **High cumtime** - Functions taking the most overall time
2. **High tottime** - Functions doing the most work themselves
3. **High ncalls** - Functions called very frequently (potential optimization)
4. **Database queries** - Look for SQLAlchemy operations in output

## Performance Optimization Workflow

1. **Profile** the application:
   ```bash
   python tools/profile_app.py --setup --scenario all
   ```

2. **Analyze** results:
   ```bash
   python tools/analyze_profile.py reports/profiles/*.prof --compare
   ```

3. **Identify** bottlenecks:
   ```bash
   python tools/analyze_profile.py reports/profiles/student_dashboard.prof --bottlenecks --threshold 5
   ```

4. **Review** optimization guide:
   - Read `docs/PERFORMANCE_OPTIMIZATION.md`
   - Check TODOs in code files

5. **Implement** fixes:
   - Start with high-priority items
   - Focus on N+1 queries first
   - Add database indexes
   - Implement caching

6. **Re-profile** to verify improvements:
   ```bash
   python tools/profile_app.py --scenario student_dashboard --output after_optimization.prof
   ```

7. **Compare** before and after:
   ```bash
   python tools/analyze_profile.py reports/profiles/before.prof reports/profiles/after.prof --compare
   ```

## Common Performance Issues

### N+1 Query Problem

**Symptom:** Many small database queries in a loop

**Detection:** Look for repeated calls to same query function in profile

**Fix:** Use eager loading or aggregation:
```python
# Bad (N+1)
for student in students:
    records = Attendance.query.filter_by(student_id=student.id).all()

# Good (1 query)
from sqlalchemy import func
stats = db.session.query(
    Attendance.student_id,
    func.count(Attendance.id)
).group_by(Attendance.student_id).all()
```

### Missing Pagination

**Symptom:** `.all()` called on large query result

**Detection:** Look for high memory usage and slow queries

**Fix:** Use pagination:
```python
# Bad
records = query.all()  # Loads everything

# Good
records = query.paginate(page=1, per_page=50)
```

### No Caching

**Symptom:** Same queries executed repeatedly

**Detection:** High database query count in profiles

**Fix:** Add caching:
```python
from flask_caching import Cache
cache = Cache(app)

@cache.memoize(timeout=300)
def get_student_data(student_id):
    return Attendance.query.filter_by(student_id=student_id).all()
```

## Tips & Tricks

1. **Profile in production-like environment** - Use realistic data volumes
2. **Profile multiple scenarios** - Different code paths have different bottlenecks
3. **Focus on hot paths** - Optimize code that runs frequently
4. **Measure before and after** - Verify your optimizations actually help
5. **Don't over-optimize** - Profile first, optimize second

## Troubleshooting

### "No module named tools.profiling"

Solution: Run from project root or add to PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Profile file not found

Check the `reports/profiles/` directory exists:
```bash
mkdir -p reports/profiles
```

### psutil not found (memory profiling)

Install psutil:
```bash
pip install psutil
```

## Additional Resources

- **Performance Optimization Guide**: `docs/PERFORMANCE_OPTIMIZATION.md`
- **Profiling Library**: `tools/profiling.py`
- **Profile Runner**: `tools/profile_app.py`
- **Analysis Tool**: `tools/analyze_profile.py`

---

**Last Updated:** 2025-11-18
