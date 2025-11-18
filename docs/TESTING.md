# Testing and Quality Infrastructure

This document describes the comprehensive testing and quality assurance infrastructure for the Student Attendance System.

## Table of Contents
- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Performance Testing](#performance-testing)
- [Load Testing](#load-testing)
- [Code Quality](#code-quality)
- [Profiling and Instrumentation](#profiling-and-instrumentation)
- [Continuous Improvement](#continuous-improvement)

## Overview

The project implements a multi-layered testing approach:
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test interactions between components
- **System Tests**: End-to-end workflow testing
- **Performance Tests**: Benchmark critical operations
- **Load Tests**: Simulate concurrent users

**Coverage Target**: ≥80%  
**Pylint Score Target**: ≥9.0/10

## Test Structure

```
tests/
├── unit/               # Unit tests for individual modules
│   ├── test_password_security.py
│   ├── test_encryption_comprehensive.py
│   ├── test_rbac.py
│   ├── test_audit_trail.py
│   └── ...
├── integration/        # Integration tests for component interaction
│   ├── test_attendance_api.py
│   ├── test_login.py
│   └── ...
├── system/            # End-to-end system tests
│   ├── test_end_to_end_workflows.py
│   ├── test_account_locking_system.py
│   └── ...
├── test_performance.py  # Performance benchmarks
└── conftest.py         # Shared fixtures

perf/
└── load_test.py        # Locust load testing script

tools/
├── run_quality_checks.py  # Main quality automation
├── improve_pylint.py      # Pylint analysis and improvement
└── profiling.py           # Performance profiling tools
```

## Running Tests

### All Tests with Coverage
```bash
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html:reports/coverage_html
```

### By Test Type
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v -m integration

# System/E2E tests only
pytest tests/system/ -v -m system

# Performance benchmarks
pytest tests/test_performance.py --benchmark-only
```

### Parallel Execution
```bash
# Run tests in parallel (faster)
pytest tests/ -n auto --cov=src
```

### Specific Test Categories
```bash
# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Performance tests only
pytest -m performance --benchmark-only
```

## Performance Testing

Performance tests benchmark critical operations:

### Running Benchmarks
```bash
# All performance tests
pytest tests/test_performance.py --benchmark-only

# Specific benchmark groups
pytest tests/test_performance.py::TestPasswordPerformance --benchmark-only

# Save benchmark results
pytest tests/test_performance.py --benchmark-only --benchmark-json=reports/benchmark.json
```

### What's Benchmarked
- Password hashing and verification
- Data encryption and decryption
- Database queries
- Bulk operations
- Concurrent operations

### Performance Targets
- Password hashing: <500ms per hash
- Password verification: <200ms per verification
- Encryption: <50ms per operation
- Database queries: <100ms for simple queries

## Load Testing

Locust is used for load testing with realistic user scenarios.

### Running Load Tests

#### Interactive Mode
```bash
cd perf
locust -f load_test.py --host=http://localhost:5000
# Open http://localhost:8089 in browser
# Configure users and spawn rate
```

#### Headless Mode
```bash
# 100 users, spawn 10/second, run for 60 seconds
locust -f perf/load_test.py --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 60s \
    --host=http://localhost:5000 \
    --html=reports/load_test_report.html \
    --csv=reports/load_test
```

### User Types
- **StudentUser**: Simulates student viewing dashboard and attendance
- **TeacherUser**: Simulates teacher marking attendance
- **MixedUserBehavior**: 80% students, 20% teachers

### Load Test Targets
- Response time p95: <1000ms
- Response time p99: <2000ms
- Error rate: <1%
- Concurrent users: 100+ without degradation

## Code Quality

### Running Quality Checks

#### Full Quality Suite
```bash
python tools/run_quality_checks.py
```

This runs:
1. All tests with coverage
2. Pylint analysis
3. Performance benchmarks
4. Generates unified report at `reports/quality_report.md`

#### Pylint Only
```bash
pylint src/

# With detailed report
python tools/improve_pylint.py
```

### Pylint Improvement

The `improve_pylint.py` tool analyzes pylint issues and generates an improvement plan:

```bash
python tools/improve_pylint.py
```

Generates `reports/pylint_improvement_plan.md` with:
- Current score
- Issues categorized by priority
- Module-specific issues
- Quick wins for score improvement

### Quick Wins for Pylint Score
1. Add module docstrings to all `.py` files
2. Add docstrings to all public functions/classes
3. Remove unused imports and variables
4. Fix line length (max 100 characters)
5. Use proper naming conventions (snake_case)
6. Add type hints to function signatures

## Profiling and Instrumentation

### Using Profiling Tools

```python
from tools.profiling import profile, timed, memory_tracked

# Profile a function
@profile('my_function.prof')
def my_function():
    # Your code here
    pass

# Time function execution
@timed
def slow_function():
    # Your code here
    pass

# Track memory usage
@memory_tracked
def memory_intensive_function():
    # Your code here
    pass
```

### Request Logging

Add to your Flask app:

```python
from tools.profiling import RequestLogger

app = Flask(__name__)
request_logger = RequestLogger(app)

# ... your routes ...

# On shutdown, save logs
request_logger.save_logs()
stats = request_logger.get_statistics()
print(stats)
```

### Manual Profiling

```python
from tools.profiling import profiler

result, stats = profiler.profile_function(my_function, arg1, arg2)
print(stats)  # View profiling results
```

## Continuous Improvement

### Weekly Quality Checklist

- [ ] Run full test suite: `pytest tests/`
- [ ] Check coverage: Must be ≥80%
- [ ] Run quality checks: `python tools/run_quality_checks.py`
- [ ] Review quality report: `reports/quality_report.md`
- [ ] Run pylint improvement: `python tools/improve_pylint.py`
- [ ] Address high-priority issues
- [ ] Run load tests: `locust -f perf/load_test.py --headless ...`
- [ ] Review performance benchmarks

### Before Each Release

1. Run full quality suite
2. Ensure all tests pass
3. Coverage ≥80%
4. Pylint score ≥9.0/10
5. Load test with expected user count
6. Review performance benchmarks
7. Update documentation

### CI/CD Integration

Add to your CI pipeline:

```yaml
# Example GitHub Actions
- name: Run tests with coverage
  run: pytest tests/ --cov=src --cov-report=xml --cov-fail-under=80

- name: Run pylint
  run: pylint src/ --fail-under=9.0

- name: Run quality checks
  run: python tools/run_quality_checks.py
```

## Troubleshooting

### Tests Failing
```bash
# Run with verbose output
pytest tests/ -vv

# Run specific failing test
pytest tests/unit/test_password_security.py::test_specific_function -vv

# See full error output
pytest tests/ --tb=long
```

### Coverage Too Low
```bash
# See which lines are not covered
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML coverage report for detailed view
pytest tests/ --cov=src --cov-report=html:reports/coverage_html
# Open reports/coverage_html/index.html
```

### Slow Tests
```bash
# Find slowest tests
pytest tests/ --durations=10

# Run fast tests only
pytest tests/ -m "not slow"
```

### Pylint Score Low
```bash
# Generate improvement plan
python tools/improve_pylint.py

# Focus on high-priority issues first
# Check reports/pylint_improvement_plan.md
```

## Configuration Files

### pyproject.toml
Contains pytest and coverage configuration:
- Test paths
- Coverage thresholds (80%)
- Test markers
- Report formats

### .pylintrc
Pylint configuration for code quality standards.

### requirements.txt
All testing dependencies:
- pytest, pytest-cov, pytest-benchmark
- hypothesis (property-based testing)
- locust (load testing)
- faker (test data generation)
- pytest-xdist (parallel testing)

## Best Practices

1. **Write tests first** (TDD) for new features
2. **Run tests frequently** during development
3. **Maintain coverage** above 80%
4. **Profile slow code** before optimizing
5. **Use fixtures** for common test setup
6. **Parametrize tests** for multiple scenarios
7. **Mark slow tests** with `@pytest.mark.slow`
8. **Document test purpose** with clear docstrings
9. **Clean up after tests** (use fixtures with cleanup)
10. **Review quality report** regularly

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [coverage.py documentation](https://coverage.readthedocs.io/)
- [pylint documentation](https://pylint.pycqa.org/)
- [Locust documentation](https://docs.locust.io/)
- [hypothesis documentation](https://hypothesis.readthedocs.io/)

## Getting Help

If you encounter issues:
1. Check this README
2. Review test output carefully
3. Check `reports/quality_report.md`
4. Review individual test files for examples
5. Consult team members

---

**Last Updated**: November 2025  
**Maintained By**: RollCall Coders Team
