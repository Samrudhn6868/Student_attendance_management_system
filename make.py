"""Quick command shortcuts for testing and quality checks.

This script provides simple shortcuts for common development tasks.
Equivalent to a Makefile for Python projects.

Usage:
    python make.py <command>

Commands:
    test            - Run all tests with coverage
    test-unit       - Run unit tests only
    test-integration - Run integration tests only
    test-system     - Run system/E2E tests only
    test-perf       - Run performance benchmarks
    test-fast       - Run tests in parallel (skip slow tests)
    
    quality         - Run complete quality check suite
    coverage        - Generate HTML coverage report and open it
    lint            - Run pylint analysis
    lint-fix        - Generate pylint improvement plan
    
    load-test       - Run load test (interactive)
    load-test-quick - Run quick load test (headless, 50 users, 30s)
    
    clean           - Remove generated files and caches
    help            - Show this help message

Examples:
    python make.py test
    python make.py quality
    python make.py coverage
    python make.py lint
"""

import sys
import os
import subprocess
import webbrowser
from pathlib import Path


class TaskRunner:
    """Simple task runner for development commands."""
    
    def __init__(self):
        """Initialize task runner."""
        self.project_root = Path(__file__).parent
        self.python_exe = sys.executable
    
    def run_command(self, command: str, shell: bool = True) -> int:
        """Run a shell command and return exit code."""
        print(f"\n> Running: {command}\n")
        result = subprocess.run(command, shell=shell, cwd=self.project_root)
        return result.returncode
    
    def test(self):
        """Run all tests with coverage."""
        return self.run_command(
            f'{self.python_exe} -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html:reports/coverage_html'
        )
    
    def test_unit(self):
        """Run unit tests only."""
        return self.run_command(f'{self.python_exe} -m pytest tests/unit/ -v')
    
    def test_integration(self):
        """Run integration tests only."""
        return self.run_command(f'{self.python_exe} -m pytest tests/integration/ -v -m integration')
    
    def test_system(self):
        """Run system/E2E tests only."""
        return self.run_command(f'{self.python_exe} -m pytest tests/system/ -v -m system')
    
    def test_perf(self):
        """Run performance benchmarks."""
        return self.run_command(f'{self.python_exe} -m pytest tests/test_performance.py --benchmark-only')
    
    def test_fast(self):
        """Run tests in parallel, skip slow tests."""
        return self.run_command(
            f'{self.python_exe} -m pytest tests/ -n auto -m "not slow" --cov=src'
        )
    
    def quality(self):
        """Run complete quality check suite."""
        return self.run_command(f'{self.python_exe} tools/run_quality_checks.py')
    
    def coverage(self):
        """Generate HTML coverage report and open it."""
        result = self.run_command(
            f'{self.python_exe} -m pytest tests/ --cov=src --cov-report=html:reports/coverage_html'
        )
        
        if result == 0:
            coverage_file = self.project_root / 'reports' / 'coverage_html' / 'index.html'
            if coverage_file.exists():
                print(f"\n✓ Opening coverage report: {coverage_file}")
                webbrowser.open(str(coverage_file))
        
        return result
    
    def lint(self):
        """Run pylint analysis."""
        return self.run_command(f'{self.python_exe} -m pylint src/')
    
    def lint_fix(self):
        """Generate pylint improvement plan."""
        return self.run_command(f'{self.python_exe} tools/improve_pylint.py')
    
    def load_test(self):
        """Run load test (interactive)."""
        print("\n✓ Starting Locust in interactive mode")
        print("✓ Open http://localhost:8089 in your browser\n")
        return self.run_command('locust -f perf/load_test.py --host=http://localhost:5000')
    
    def load_test_quick(self):
        """Run quick load test (headless, 50 users, 30s)."""
        return self.run_command(
            'locust -f perf/load_test.py --headless --users 50 --spawn-rate 5 '
            '--run-time 30s --host=http://localhost:5000 '
            '--html=reports/load_test_report.html --csv=reports/load_test'
        )
    
    def clean(self):
        """Remove generated files and caches."""
        print("\n▶ Cleaning generated files and caches...\n")
        
        patterns = [
            '**/__pycache__',
            '**/*.pyc',
            '**/*.pyo',
            '**/*.pyd',
            '.pytest_cache',
            '.coverage',
            'reports/coverage_html',
            'reports/*.xml',
            'reports/*.json',
            'reports/*.html',
            'reports/*.csv',
            '**/.hypothesis',
        ]
        
        import shutil
        
        for pattern in patterns:
            for path in self.project_root.glob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                        print(f"  Deleted: {path}")
                    elif path.is_dir():
                        shutil.rmtree(path)
                        print(f"  Deleted: {path}")
                except Exception as e:
                    print(f"  Error deleting {path}: {e}")
        
        print("\n✓ Cleanup complete\n")
        return 0
    
    def help(self):
        """Show help message."""
        print(__doc__)
        return 0
    
    def run(self, task_name: str):
        """Run a task by name."""
        # Map task names to methods
        tasks = {
            'test': self.test,
            'test-unit': self.test_unit,
            'test-integration': self.test_integration,
            'test-system': self.test_system,
            'test-perf': self.test_perf,
            'test-fast': self.test_fast,
            'quality': self.quality,
            'coverage': self.coverage,
            'lint': self.lint,
            'lint-fix': self.lint_fix,
            'load-test': self.load_test,
            'load-test-quick': self.load_test_quick,
            'clean': self.clean,
            'help': self.help,
        }
        
        if task_name not in tasks:
            print(f"❌ Error: Unknown task '{task_name}'")
            print("\nAvailable tasks:")
            for task in sorted(tasks.keys()):
                print(f"  - {task}")
            print("\nRun 'python make.py help' for more information")
            return 1
        
        return tasks[task_name]()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("❌ Error: No task specified")
        print("\nUsage: python make.py <task>")
        print("Run 'python make.py help' for available tasks")
        return 1
    
    task_name = sys.argv[1]
    runner = TaskRunner()
    exit_code = runner.run(task_name)
    
    if exit_code == 0:
        print(f"\n✓ Task '{task_name}' completed successfully\n")
    else:
        print(f"\n❌ Task '{task_name}' failed with exit code {exit_code}\n")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
