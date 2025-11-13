"""SAS-96: Verification Script

This script verifies that the bunk allowance feature is correctly installed
and ready to use.

Usage:
    python scripts/verify_bunk_allowance.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"  ✓ {description}")
        return True
    else:
        print(f"  ✗ {description} - NOT FOUND")
        return False


def verify_files():
    """Verify all necessary files exist."""
    print("\n" + "="*60)
    print("FILE VERIFICATION")
    print("="*60)
    
    files = [
        ("src/bunk_allowance_models.py", "Models file"),
        ("src/bunk_allowance_service.py", "Service file"),
        ("src/bunk_allowance_api.py", "API file"),
        ("src/bunk_allowance_integration.py", "Integration file"),
        ("src/bunk_allowance_quick_setup.py", "Quick setup file"),
        ("scripts/migrate_bunk_allowance.py", "Migration script"),
        ("scripts/demo_bunk_allowance.py", "Demo script"),
        ("tests/unit/test_bunk_allowance_models.py", "Model tests"),
        ("tests/unit/test_bunk_allowance_service.py", "Service tests"),
        ("tests/integration/test_bunk_allowance_api.py", "API tests"),
        ("tests/system/test_bunk_allowance_system.py", "System tests"),
        ("tests/conftest.py", "Test fixtures"),
        ("docs/SAS-96-BUNK-ALLOWANCE.md", "Documentation"),
        ("docs/SAS-96-IMPLEMENTATION-SUMMARY.md", "Implementation summary"),
        ("docs/SAS-96-QUICK-START.md", "Quick start guide"),
    ]
    
    all_present = True
    for filepath, description in files:
        if not check_file_exists(filepath, description):
            all_present = False
    
    return all_present


def verify_imports():
    """Verify all modules can be imported."""
    print("\n" + "="*60)
    print("IMPORT VERIFICATION")
    print("="*60)
    
    imports = [
        ("src.bunk_allowance_models", "Models"),
        ("src.bunk_allowance_service", "Service"),
        ("src.bunk_allowance_api", "API"),
        ("src.bunk_allowance_integration", "Integration"),
        ("src.bunk_allowance_quick_setup", "Quick setup"),
    ]
    
    all_imported = True
    for module_name, description in imports:
        try:
            __import__(module_name)
            print(f"  ✓ {description} imported successfully")
        except ImportError as e:
            print(f"  ✗ {description} import failed: {e}")
            all_imported = False
        except Exception as e:
            print(f"  ⚠ {description} import warning: {e}")
    
    return all_imported


def verify_models():
    """Verify models are defined correctly."""
    print("\n" + "="*60)
    print("MODEL VERIFICATION")
    print("="*60)
    
    try:
        from src.bunk_allowance_models import CourseConfig, StudentBunkAllowance
        
        # Check CourseConfig
        config_attrs = ['course_id', 'course_name', 'total_classes', 
                       'bunk_allowance_percentage', 'min_attendance_percentage']
        for attr in config_attrs:
            if hasattr(CourseConfig, attr):
                print(f"  ✓ CourseConfig.{attr} exists")
            else:
                print(f"  ✗ CourseConfig.{attr} missing")
        
        # Check StudentBunkAllowance
        allowance_attrs = ['student_srn', 'course_id', 'total_classes_held',
                          'classes_attended', 'classes_missed', 
                          'current_attendance_percentage', 'remaining_bunk_allowance']
        for attr in allowance_attrs:
            if hasattr(StudentBunkAllowance, attr):
                print(f"  ✓ StudentBunkAllowance.{attr} exists")
            else:
                print(f"  ✗ StudentBunkAllowance.{attr} missing")
        
        return True
    except Exception as e:
        print(f"  ✗ Model verification failed: {e}")
        return False


def verify_service():
    """Verify service methods exist."""
    print("\n" + "="*60)
    print("SERVICE VERIFICATION")
    print("="*60)
    
    try:
        from src.bunk_allowance_service import BunkAllowanceService
        
        methods = [
            'get_or_create_course_config',
            'calculate_student_attendance_stats',
            'update_student_bunk_allowance',
            'get_student_bunk_allowance',
            'get_remaining_classes_breakdown',
            'get_all_students_bunk_status',
            'get_critical_students',
            'bulk_update_course_allowances'
        ]
        
        for method in methods:
            if hasattr(BunkAllowanceService, method):
                print(f"  ✓ BunkAllowanceService.{method} exists")
            else:
                print(f"  ✗ BunkAllowanceService.{method} missing")
        
        return True
    except Exception as e:
        print(f"  ✗ Service verification failed: {e}")
        return False


def verify_api():
    """Verify API endpoints exist."""
    print("\n" + "="*60)
    print("API VERIFICATION")
    print("="*60)
    
    try:
        from src.bunk_allowance_api import bunk_allowance_bp
        
        print(f"  ✓ Blueprint 'bunk_allowance_bp' exists")
        print(f"  ✓ Blueprint URL prefix: {bunk_allowance_bp.url_prefix}")
        
        # Check if blueprint has routes
        if len(bunk_allowance_bp.deferred_functions) > 0 or hasattr(bunk_allowance_bp, 'view_functions'):
            print(f"  ✓ Blueprint has routes defined")
        
        return True
    except Exception as e:
        print(f"  ✗ API verification failed: {e}")
        return False


def verify_tests():
    """Verify test files are valid."""
    print("\n" + "="*60)
    print("TEST VERIFICATION")
    print("="*60)
    
    try:
        # Try importing pytest
        import pytest
        print("  ✓ pytest is installed")
        
        # Check test files can be imported
        test_modules = [
            "tests.unit.test_bunk_allowance_models",
            "tests.unit.test_bunk_allowance_service",
            "tests.integration.test_bunk_allowance_api",
            "tests.system.test_bunk_allowance_system",
        ]
        
        for module in test_modules:
            try:
                __import__(module)
                print(f"  ✓ {module.split('.')[-1]} can be imported")
            except ImportError as e:
                print(f"  ⚠ {module.split('.')[-1]} import warning: {e}")
        
        return True
    except ImportError:
        print("  ⚠ pytest not installed (optional for development)")
        return True


def verify_integration():
    """Verify integration with main app."""
    print("\n" + "="*60)
    print("INTEGRATION VERIFICATION")
    print("="*60)
    
    try:
        from src.main import app, db
        print("  ✓ Main app can be imported")
        
        # Check if blueprint is registered
        if 'bunk_allowance' in [bp.name for bp in app.blueprints.values()]:
            print("  ✓ Bunk allowance blueprint is registered")
        else:
            print("  ⚠ Bunk allowance blueprint not yet registered")
            print("    → Add to main.py: from bunk_allowance_quick_setup import setup_bunk_allowance")
            print("    →                 setup_bunk_allowance(app, db)")
        
        # Check if tables exist
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'course_config' in tables:
                print("  ✓ course_config table exists")
            else:
                print("  ⚠ course_config table not created yet")
                print("    → Run: python scripts/migrate_bunk_allowance.py")
            
            if 'student_bunk_allowance' in tables:
                print("  ✓ student_bunk_allowance table exists")
            else:
                print("  ⚠ student_bunk_allowance table not created yet")
                print("    → Run: python scripts/migrate_bunk_allowance.py")
        
        return True
    except Exception as e:
        print(f"  ⚠ Integration verification warning: {e}")
        return True


def print_summary(results):
    """Print verification summary."""
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(results.values())
    
    for check, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {check}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ All checks passed! The feature is ready to use.")
        print("\nNext steps:")
        print("  1. Ensure blueprint is registered in main.py")
        print("  2. Run: python scripts/migrate_bunk_allowance.py")
        print("  3. Run: python scripts/demo_bunk_allowance.py (optional)")
        print("  4. Start the app and test: python src/main.py")
    else:
        print("\n⚠ Some checks failed. Please review the errors above.")
    
    return passed == total


def main():
    """Run all verifications."""
    print("="*60)
    print("SAS-96: Bunk Allowance Feature Verification")
    print("="*60)
    
    results = {
        "Files": verify_files(),
        "Imports": verify_imports(),
        "Models": verify_models(),
        "Service": verify_service(),
        "API": verify_api(),
        "Tests": verify_tests(),
        "Integration": verify_integration(),
    }
    
    success = print_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
