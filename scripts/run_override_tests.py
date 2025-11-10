"""Test runner script for admin override functionality.

This script runs all tests related to the admin override feature
and generates a comprehensive report.

Usage:
    python scripts/run_override_tests.py
    python scripts/run_override_tests.py --verbose
    python scripts/run_override_tests.py --coverage
"""

import sys
import os
import subprocess
import argparse

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def run_command(cmd, description):
    """Run a command and return success status."""
    print_header(description)
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print(f"\n✓ {description} completed successfully")
        return True
    else:
        print(f"\n✗ {description} failed")
        return False


def main():
    """Run all override-related tests."""
    parser = argparse.ArgumentParser(description='Run admin override tests')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Run with coverage report')
    parser.add_argument('--unit', action='store_true',
                       help='Run only unit tests')
    parser.add_argument('--integration', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--system', action='store_true',
                       help='Run only system tests')
    
    args = parser.parse_args()
    
    print_header("Admin Override Attendance - Test Runner")
    print("This script will run all tests for the admin override feature.")
    
    results = []
    
    # Determine which tests to run
    run_all = not (args.unit or args.integration or args.system)
    
    # Base pytest command
    base_cmd = ['pytest']
    if args.verbose:
        base_cmd.append('-v')
    
    # Run unit tests
    if run_all or args.unit:
        cmd = base_cmd + ['tests/test_admin_override.py']
        if args.coverage:
            cmd.extend(['--cov=src', '--cov-report=term-missing'])
        
        success = run_command(cmd, "Unit Tests (test_admin_override.py)")
        results.append(("Unit Tests", success))
    
    # Run integration tests
    if run_all or args.integration:
        cmd = base_cmd + ['tests/integration/test_override_integration.py']
        if args.coverage:
            cmd.extend(['--cov=src', '--cov-append', '--cov-report=term-missing'])
        
        success = run_command(cmd, "Integration Tests")
        results.append(("Integration Tests", success))
    
    # Run system tests
    if run_all or args.system:
        cmd = base_cmd + ['tests/system/test_override_system.py']
        if args.coverage:
            cmd.extend(['--cov=src', '--cov-append', '--cov-report=term-missing'])
        
        success = run_command(cmd, "System Tests")
        results.append(("System Tests", success))
    
    # Generate coverage report if requested
    if args.coverage:
        print_header("Generating Coverage Report")
        subprocess.run([
            'pytest',
            'tests/test_admin_override.py',
            'tests/integration/test_override_integration.py',
            'tests/system/test_override_system.py',
            '--cov=src',
            '--cov-report=html',
            '--cov-report=term'
        ])
        print("\n✓ HTML coverage report generated in 'htmlcov' directory")
    
    # Print summary
    print_header("Test Results Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} test suites passed")
    
    if args.coverage:
        print("\nCoverage report available at: htmlcov/index.html")
    
    print_header("Test Run Complete")
    
    # Exit with appropriate status code
    if passed_tests == total_tests:
        print("All tests passed! ✓")
        return 0
    else:
        print(f"Some tests failed. {total_tests - passed_tests} suite(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
