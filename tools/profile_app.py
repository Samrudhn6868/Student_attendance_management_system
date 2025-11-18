"""Application profiling script using cProfile.

This script profiles critical code paths in the attendance system and saves
profiling data to reports/profiles/ for analysis.

Usage:
    python tools/profile_app.py [--scenario SCENARIO] [--output OUTPUT]

Scenarios:
    - student_dashboard: Profile student dashboard loading
    - faculty_dashboard: Profile faculty dashboard loading
    - attendance_submit: Profile attendance submission workflow
    - bunk_calculation: Profile bunk allowance calculations
    - all: Run all scenarios (default)
"""

import cProfile
import pstats
import os
import sys
import argparse
from datetime import datetime, date

# Add src to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
sys.path.insert(0, SRC_DIR)

# Import after path setup
os.environ['FLASK_ENV'] = 'testing'
os.environ['DISABLE_DEMO_SEED'] = '1'

from main import app, db
from models import User, Attendance


class AppProfiler:
    """Profile application performance."""
    
    def __init__(self, output_dir='reports/profiles'):
        """Initialize profiler with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.app = app
        self.client = app.test_client()
        
    def setup_test_data(self):
        """Create test data for profiling."""
        with self.app.app_context():
            # Clear existing data
            db.drop_all()
            db.create_all()
            
            # Create test users
            admin = User(username='admin_test', name='Admin Test', is_faculty=True, role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            
            teacher = User(username='teacher_test', name='Teacher Test', is_faculty=True, role='teacher')
            teacher.set_password('teacher123')
            db.session.add(teacher)
            
            # Create 100 test students
            students = []
            for i in range(100):
                student = User(
                    username=f'student{i:03d}',
                    name=f'Student {i:03d}',
                    is_faculty=False,
                    role='student'
                )
                student.set_password('student123')
                students.append(student)
                db.session.add(student)
            
            db.session.commit()
            
            # Create attendance records (simulate semester data)
            print("Creating test attendance records...")
            for student in students:
                for day_offset in range(50):  # 50 days of attendance
                    attendance = Attendance(
                        student_id=student.id,
                        course_id=f'CS{100 + (day_offset % 5)}',
                        date=date(2025, 1, 1),
                        status='present' if (day_offset % 4) != 0 else 'absent',
                        marked_by=teacher.name
                    )
                    db.session.add(attendance)
            
            db.session.commit()
            print(f"✓ Created {len(students)} students with {50 * len(students)} attendance records")
    
    def profile_scenario(self, scenario_name, func, output_file=None):
        """Profile a specific scenario."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'{scenario_name}_{timestamp}.prof'
        
        filepath = os.path.join(self.output_dir, output_file)
        
        print(f"\n{'='*60}")
        print(f"Profiling: {scenario_name}")
        print(f"Output: {filepath}")
        print(f"{'='*60}\n")
        
        # Run profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func()
        
        profiler.disable()
        
        # Save binary stats
        profiler.dump_stats(filepath)
        
        # Save human-readable stats
        txt_filepath = filepath.replace('.prof', '.txt')
        with open(txt_filepath, 'w', encoding='utf-8') as f:
            f.write(f"Profile: {scenario_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"{'='*60}\n\n")
            
            stats = pstats.Stats(profiler, stream=f)
            
            # Top functions by cumulative time
            f.write("TOP 30 FUNCTIONS BY CUMULATIVE TIME:\n")
            f.write("-" * 60 + "\n")
            stats.sort_stats('cumulative')
            stats.print_stats(30)
            
            f.write("\n\n")
            
            # Top functions by total time
            f.write("TOP 30 FUNCTIONS BY TOTAL TIME:\n")
            f.write("-" * 60 + "\n")
            stats.sort_stats('tottime')
            stats.print_stats(30)
            
            f.write("\n\n")
            
            # Top callers
            f.write("TOP 20 CALLERS:\n")
            f.write("-" * 60 + "\n")
            stats.print_callers(20)
        
        print(f"✓ Profile saved to: {filepath}")
        print(f"✓ Human-readable: {txt_filepath}")
        
        # Print quick summary
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        print("\nTop 10 slowest functions:")
        stats.print_stats(10)
        
        return result
    
    def scenario_student_dashboard(self):
        """Profile student dashboard loading."""
        with self.app.app_context():
            # Login as student
            with self.client:
                self.client.post('/login', data={
                    'username': 'student000',
                    'password': 'student123'
                })
                
                # Load dashboard multiple times
                for _ in range(10):
                    response = self.client.get('/dashboard')
                    assert response.status_code == 200
        
        return "Student dashboard profiled (10 requests)"
    
    def scenario_faculty_dashboard(self):
        """Profile faculty dashboard loading."""
        with self.app.app_context():
            # Login as teacher
            with self.client:
                self.client.post('/login', data={
                    'username': 'teacher_test',
                    'password': 'teacher123'
                })
                
                # Load dashboard multiple times
                for _ in range(10):
                    response = self.client.get('/dashboard')
                    assert response.status_code == 200
        
        return "Faculty dashboard profiled (10 requests)"
    
    def scenario_attendance_submit(self):
        """Profile attendance submission."""
        with self.app.app_context():
            # Login as teacher
            with self.client:
                self.client.post('/login', data={
                    'username': 'teacher_test',
                    'password': 'teacher123'
                })
                
                # Submit attendance for 20 students
                for i in range(20):
                    response = self.client.post('/api/attendance/submit', json={
                        'student_srn': f'PES1UG{i:05d}',
                        'course_id': 'CS101',
                        'date': '2025-01-15',
                        'status': 'present'
                    })
        
        return "Attendance submission profiled (20 submissions)"
    
    def scenario_bunk_calculation(self):
        """Profile bunk allowance calculations."""
        try:
            from bunk_recommendations import BunkRecommendationService
            
            # Calculate for 50 different scenarios
            results = []
            for attended in range(10, 60):
                for total in range(attended, 80):
                    result = BunkRecommendationService.calculate_safe_bunks(
                        classes_attended=attended,
                        total_classes_held=total,
                        total_classes_remaining=30,
                        min_attendance=75.0
                    )
                    results.append(result)
            
            return f"Bunk calculation profiled ({len(results)} calculations)"
        except ImportError:
            return "Bunk calculation skipped (module not available)"
    
    def run_all_scenarios(self):
        """Run all profiling scenarios."""
        scenarios = {
            'student_dashboard': self.scenario_student_dashboard,
            'faculty_dashboard': self.scenario_faculty_dashboard,
            'attendance_submit': self.scenario_attendance_submit,
            'bunk_calculation': self.scenario_bunk_calculation,
        }
        
        results = {}
        for name, func in scenarios.items():
            try:
                result = self.profile_scenario(name, func)
                results[name] = {'status': 'success', 'message': result}
            except Exception as e:
                results[name] = {'status': 'error', 'message': str(e)}
                print(f"✗ Error in {name}: {e}")
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Profile PESU Attendance System')
    parser.add_argument(
        '--scenario',
        choices=['student_dashboard', 'faculty_dashboard', 'attendance_submit', 'bunk_calculation', 'all'],
        default='all',
        help='Scenario to profile (default: all)'
    )
    parser.add_argument(
        '--output',
        help='Output filename (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Setup test data before profiling'
    )
    
    args = parser.parse_args()
    
    profiler = AppProfiler()
    
    # Setup test data if requested
    if args.setup:
        print("Setting up test data...")
        profiler.setup_test_data()
    
    # Run profiling
    if args.scenario == 'all':
        print("\n" + "="*60)
        print("RUNNING ALL PROFILING SCENARIOS")
        print("="*60)
        results = profiler.run_all_scenarios()
        
        print("\n" + "="*60)
        print("PROFILING SUMMARY")
        print("="*60)
        for scenario, result in results.items():
            status_symbol = "✓" if result['status'] == 'success' else "✗"
            print(f"{status_symbol} {scenario}: {result['message']}")
    else:
        # Run single scenario
        scenario_map = {
            'student_dashboard': profiler.scenario_student_dashboard,
            'faculty_dashboard': profiler.scenario_faculty_dashboard,
            'attendance_submit': profiler.scenario_attendance_submit,
            'bunk_calculation': profiler.scenario_bunk_calculation,
        }
        
        func = scenario_map[args.scenario]
        profiler.profile_scenario(args.scenario, func, args.output)
    
    print("\n✓ Profiling complete!")
    print(f"Results saved to: {profiler.output_dir}/")


if __name__ == '__main__':
    main()
