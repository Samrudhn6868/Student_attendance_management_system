"""
Comprehensive Quality Checks Runner

This script runs:
1. Unit, integration, and system tests with coverage
2. Pylint static analysis
3. Performance benchmarks
4. Generates a unified quality report
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import re


class QualityChecker:
    """Runs comprehensive quality checks and generates report."""
    
    def __init__(self, project_root=None):
        """Initialize quality checker."""
        self.project_root = Path(project_root or Path(__file__).parent.parent).resolve()
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "coverage": {},
            "pylint": {},
            "performance": {}
        }
    
    def run_tests(self):
        """Run pytest with coverage."""
        print("\n" + "=" * 70)
        print("RUNNING TESTS WITH COVERAGE")
        print("=" * 70)
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=term-missing:skip-covered",
            f"--cov-report=html:{self.reports_dir}/coverage_html",
            f"--cov-report=xml:{self.reports_dir}/coverage.xml",
            "--cov-report=json:reports/coverage.json",
            "-v",
            "--tb=short",
            "-m", "not performance"  # Skip performance tests in regular run
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        
        # Parse test results
        output = result.stdout + result.stderr
        self._parse_test_output(output)
        
        # Parse coverage from JSON if available
        coverage_json = self.reports_dir / "coverage.json"
        if coverage_json.exists():
            with open(coverage_json) as f:
                cov_data = json.load(f)
                self.results["coverage"] = {
                    "percent": round(cov_data.get("totals", {}).get("percent_covered", 0), 2),
                    "lines_covered": cov_data.get("totals", {}).get("covered_lines", 0),
                    "lines_total": cov_data.get("totals", {}).get("num_statements", 0),
                    "branches_covered": cov_data.get("totals", {}).get("covered_branches", 0),
                    "branches_total": cov_data.get("totals", {}).get("num_branches", 0),
                }
        else:
            # Fallback: parse from output
            cov_match = re.search(r'TOTAL.*?(\d+)%', output)
            if cov_match:
                self.results["coverage"]["percent"] = float(cov_match.group(1))
        
        print(output)
        return result.returncode == 0
    
    def _parse_test_output(self, output):
        """Parse pytest output for test statistics."""
        # Look for pattern like: "45 passed, 2 failed, 1 skipped in 5.23s"
        match = re.search(r'(\d+) passed', output)
        passed = int(match.group(1)) if match else 0
        
        match = re.search(r'(\d+) failed', output)
        failed = int(match.group(1)) if match else 0
        
        match = re.search(r'(\d+) skipped', output)
        skipped = int(match.group(1)) if match else 0
        
        match = re.search(r'in ([\d.]+)s', output)
        duration = float(match.group(1)) if match else 0
        
        self.results["tests"] = {
            "total": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_seconds": round(duration, 2),
            "success": failed == 0
        }
    
    def run_pylint(self):
        """Run pylint on source code."""
        print("\n" + "=" * 70)
        print("RUNNING PYLINT ANALYSIS")
        print("=" * 70)
        
        cmd = [
            sys.executable, "-m", "pylint",
            "src/",
            "--output-format=json",
            f"--reports=y"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        
        try:
            pylint_data = json.loads(result.stdout) if result.stdout.strip() else []
            
            # Count issues by type
            issues_by_type = {}
            for issue in pylint_data:
                msg_type = issue.get("type", "unknown")
                issues_by_type[msg_type] = issues_by_type.get(msg_type, 0) + 1
            
            # Extract score from stderr (pylint prints score there)
            score_match = re.search(r'Your code has been rated at ([\d.]+)/10', result.stderr)
            score = float(score_match.group(1)) if score_match else 0.0
            
            self.results["pylint"] = {
                "score": score,
                "total_issues": len(pylint_data),
                "issues_by_type": issues_by_type,
                "passed": score >= 9.0
            }
            
            print(f"Pylint Score: {score}/10.0")
            print(f"Total Issues: {len(pylint_data)}")
            
        except json.JSONDecodeError:
            print("Warning: Could not parse pylint JSON output")
            # Fallback: try to get score from stderr
            score_match = re.search(r'Your code has been rated at ([\d.]+)/10', result.stderr)
            if score_match:
                score = float(score_match.group(1))
                self.results["pylint"] = {
                    "score": score,
                    "total_issues": 0,
                    "issues_by_type": {},
                    "passed": score >= 9.0
                }
                print(f"Pylint Score: {score}/10.0")
        
        return self.results["pylint"].get("passed", False)
    
    def run_performance_tests(self):
        """Run performance benchmark tests."""
        print("\n" + "=" * 70)
        print("RUNNING PERFORMANCE BENCHMARKS")
        print("=" * 70)
        
        # Check if performance tests exist
        perf_test_file = self.project_root / "tests" / "test_performance.py"
        if not perf_test_file.exists():
            print("No performance tests found. Skipping...")
            self.results["performance"] = {"skipped": True}
            return True
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/test_performance.py",
            "-v",
            "--benchmark-only",
            f"--benchmark-json={self.reports_dir}/benchmark.json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        
        # Parse benchmark results
        benchmark_json = self.reports_dir / "benchmark.json"
        if benchmark_json.exists():
            with open(benchmark_json) as f:
                bench_data = json.load(f)
                benchmarks = bench_data.get("benchmarks", [])
                
                self.results["performance"] = {
                    "total_benchmarks": len(benchmarks),
                    "benchmarks": [
                        {
                            "name": b["name"],
                            "mean": round(b["stats"]["mean"], 6),
                            "median": round(b["stats"]["median"], 6),
                            "stddev": round(b["stats"]["stddev"], 6),
                            "ops_per_sec": round(1.0 / b["stats"]["mean"], 2) if b["stats"]["mean"] > 0 else 0
                        }
                        for b in benchmarks[:10]  # Top 10
                    ]
                }
        else:
            self.results["performance"] = {"no_data": True}
        
        print(result.stdout)
        return True
    
    def generate_report(self):
        """Generate markdown quality report."""
        print("\n" + "=" * 70)
        print("GENERATING QUALITY REPORT")
        print("=" * 70)
        
        report_path = self.reports_dir / "quality_report.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Quality Report\n\n")
            f.write(f"**Generated:** {self.results['timestamp']}\n\n")
            f.write("---\n\n")
            
            # Test Results
            f.write("## 📊 Test Results\n\n")
            tests = self.results.get("tests", {})
            if tests:
                status = "✅ PASSED" if tests.get("success") else "❌ FAILED"
                f.write(f"**Status:** {status}\n\n")
                f.write(f"- **Total Tests:** {tests.get('total', 0)}\n")
                f.write(f"- **Passed:** {tests.get('passed', 0)} ✅\n")
                f.write(f"- **Failed:** {tests.get('failed', 0)} ❌\n")
                f.write(f"- **Skipped:** {tests.get('skipped', 0)} ⏭️\n")
                f.write(f"- **Duration:** {tests.get('duration_seconds', 0)}s\n\n")
            else:
                f.write("*No test data available*\n\n")
            
            # Coverage Results
            f.write("## 📈 Code Coverage\n\n")
            coverage = self.results.get("coverage", {})
            if coverage:
                percent = coverage.get("percent", 0)
                status = "✅ PASSED" if percent >= 80 else "⚠️ BELOW TARGET"
                f.write(f"**Status:** {status}\n\n")
                f.write(f"- **Overall Coverage:** {percent}%\n")
                f.write(f"- **Lines Covered:** {coverage.get('lines_covered', 0)} / {coverage.get('lines_total', 0)}\n")
                if coverage.get('branches_total', 0) > 0:
                    f.write(f"- **Branches Covered:** {coverage.get('branches_covered', 0)} / {coverage.get('branches_total', 0)}\n")
                f.write(f"\n**Target:** 80% minimum\n\n")
                f.write(f"📁 **Detailed Report:** `reports/coverage_html/index.html`\n\n")
            else:
                f.write("*No coverage data available*\n\n")
            
            # Pylint Results
            f.write("## 🔍 Code Quality (Pylint)\n\n")
            pylint = self.results.get("pylint", {})
            if pylint:
                score = pylint.get("score", 0)
                status = "✅ PASSED" if score >= 9.0 else "⚠️ NEEDS IMPROVEMENT"
                f.write(f"**Status:** {status}\n\n")
                f.write(f"- **Score:** {score}/10.0\n")
                f.write(f"- **Total Issues:** {pylint.get('total_issues', 0)}\n\n")
                
                issues_by_type = pylint.get("issues_by_type", {})
                if issues_by_type:
                    f.write("**Issues by Type:**\n\n")
                    for issue_type, count in sorted(issues_by_type.items(), key=lambda x: -x[1]):
                        f.write(f"- {issue_type}: {count}\n")
                    f.write("\n")
                
                f.write(f"**Target:** 9.0/10.0 minimum\n\n")
            else:
                f.write("*No pylint data available*\n\n")
            
            # Performance Results
            f.write("## ⚡ Performance Benchmarks\n\n")
            perf = self.results.get("performance", {})
            if perf.get("skipped"):
                f.write("*Performance tests skipped*\n\n")
            elif perf.get("no_data"):
                f.write("*No performance data available*\n\n")
            elif perf.get("total_benchmarks", 0) > 0:
                f.write(f"**Total Benchmarks:** {perf['total_benchmarks']}\n\n")
                f.write("| Benchmark | Mean (s) | Median (s) | Ops/Sec |\n")
                f.write("|-----------|----------|------------|----------|\n")
                for bench in perf.get("benchmarks", []):
                    f.write(f"| {bench['name']} | {bench['mean']} | {bench['median']} | {bench['ops_per_sec']} |\n")
                f.write("\n")
            else:
                f.write("*No performance tests run*\n\n")
            
            # Summary
            f.write("---\n\n")
            f.write("## 📋 Summary\n\n")
            
            checks = []
            if tests.get("success"):
                checks.append("✅ All tests passing")
            else:
                checks.append("❌ Some tests failing")
            
            if coverage.get("percent", 0) >= 80:
                checks.append("✅ Coverage target met (≥80%)")
            else:
                checks.append(f"⚠️ Coverage below target ({coverage.get('percent', 0)}% < 80%)")
            
            if pylint.get("score", 0) >= 9.0:
                checks.append("✅ Code quality target met (≥9.0/10)")
            else:
                checks.append(f"⚠️ Code quality below target ({pylint.get('score', 0)}/10 < 9.0/10)")
            
            for check in checks:
                f.write(f"- {check}\n")
            
            f.write("\n---\n\n")
            f.write("*Report generated by `tools/run_quality_checks.py`*\n")
        
        print(f"✅ Report generated: {report_path}")
        return report_path
    
    def run_all(self):
        """Run all quality checks and generate report."""
        print("\n" + "=" * 70)
        print("STUDENT ATTENDANCE SYSTEM - QUALITY CHECKS")
        print("=" * 70)
        
        success = True
        
        # Run tests
        if not self.run_tests():
            success = False
        
        # Run pylint
        if not self.run_pylint():
            success = False
        
        # Run performance tests
        self.run_performance_tests()
        
        # Generate report
        report_path = self.generate_report()
        
        print("\n" + "=" * 70)
        if success:
            print("✅ ALL QUALITY CHECKS PASSED")
        else:
            print("⚠️ SOME QUALITY CHECKS FAILED")
        print("=" * 70)
        print(f"\n📄 Full report: {report_path}\n")
        
        return 0 if success else 1


def main():
    """Main entry point."""
    checker = QualityChecker()
    sys.exit(checker.run_all())


if __name__ == "__main__":
    main()
