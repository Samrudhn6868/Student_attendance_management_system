"""Script to improve pylint scores across the codebase."""

import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime


class PylintImprover:
    """Analyze and suggest pylint improvements."""
    
    def __init__(self, project_root):
        """Initialize with project root."""
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / 'src'
        self.reports_dir = self.project_root / 'reports'
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_pylint_analysis(self):
        """Run pylint on all Python files and generate report."""
        print("Running pylint analysis...")
        
        # Run pylint with JSON output
        result = subprocess.run(
            ['pylint', str(self.src_dir), '--output-format=json', '--reports=y'],
            capture_output=True,
            text=True
        )
        
        # Parse JSON output
        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Could not parse pylint JSON output")
            issues = []
        
        # Also get the score
        result_text = subprocess.run(
            ['pylint', str(self.src_dir)],
            capture_output=True,
            text=True
        )
        
        return issues, result_text.stdout
    
    def categorize_issues(self, issues):
        """Categorize issues by type and severity."""
        categories = {
            'convention': [],
            'refactor': [],
            'warning': [],
            'error': [],
            'fatal': []
        }
        
        for issue in issues:
            issue_type = issue.get('type', 'warning').lower()
            if issue_type in categories:
                categories[issue_type].append(issue)
        
        return categories
    
    def get_module_scores(self, issues):
        """Calculate scores by module."""
        module_issues = {}
        
        for issue in issues:
            module = issue.get('module', 'unknown')
            if module not in module_issues:
                module_issues[module] = []
            module_issues[module].append(issue)
        
        # Sort by issue count
        sorted_modules = sorted(
            module_issues.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        return sorted_modules
    
    def generate_improvement_plan(self, categorized_issues, module_scores):
        """Generate improvement plan."""
        plan = []
        
        # Priority 1: Fix fatal errors
        if categorized_issues['fatal']:
            plan.append({
                'priority': 'CRITICAL',
                'category': 'Fatal Errors',
                'count': len(categorized_issues['fatal']),
                'recommendation': 'Fix immediately - these prevent code execution',
                'files': list(set([i['path'] for i in categorized_issues['fatal']]))
            })
        
        # Priority 2: Fix errors
        if categorized_issues['error']:
            plan.append({
                'priority': 'HIGH',
                'category': 'Errors',
                'count': len(categorized_issues['error']),
                'recommendation': 'Fix these to prevent potential runtime issues',
                'common_types': self._get_common_message_ids(categorized_issues['error'][:10])
            })
        
        # Priority 3: Address warnings
        if categorized_issues['warning']:
            plan.append({
                'priority': 'MEDIUM',
                'category': 'Warnings',
                'count': len(categorized_issues['warning']),
                'recommendation': 'Address to improve code quality',
                'common_types': self._get_common_message_ids(categorized_issues['warning'][:10])
            })
        
        # Priority 4: Refactoring opportunities
        if categorized_issues['refactor']:
            plan.append({
                'priority': 'MEDIUM',
                'category': 'Refactoring',
                'count': len(categorized_issues['refactor']),
                'recommendation': 'Improve code structure and maintainability',
                'common_types': self._get_common_message_ids(categorized_issues['refactor'][:10])
            })
        
        # Priority 5: Convention improvements
        if categorized_issues['convention']:
            plan.append({
                'priority': 'LOW',
                'category': 'Conventions',
                'count': len(categorized_issues['convention']),
                'recommendation': 'Follow PEP 8 and Python best practices',
                'common_types': self._get_common_message_ids(categorized_issues['convention'][:10])
            })
        
        # Identify worst modules
        if module_scores:
            worst_modules = module_scores[:5]
            plan.append({
                'priority': 'HIGH',
                'category': 'Modules needing most work',
                'modules': [
                    {'name': m[0], 'issues': len(m[1])}
                    for m in worst_modules
                ]
            })
        
        return plan
    
    def _get_common_message_ids(self, issues):
        """Get most common message IDs from issues."""
        from collections import Counter
        
        message_ids = [i.get('message-id', 'unknown') for i in issues]
        common = Counter(message_ids).most_common(5)
        
        return [{'id': msg_id, 'count': count} for msg_id, count in common]
    
    def generate_report(self, issues, full_output):
        """Generate markdown report."""
        categorized = self.categorize_issues(issues)
        module_scores = self.get_module_scores(issues)
        plan = self.generate_improvement_plan(categorized, module_scores)
        
        report = []
        report.append("# Pylint Improvement Report\n")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Extract score
        score_line = [line for line in full_output.split('\n') if 'Your code has been rated' in line]
        if score_line:
            report.append(f"## Current Score\n\n{score_line[0]}\n\n")
        
        # Issue summary
        report.append("## Issue Summary\n\n")
        report.append(f"- **Fatal**: {len(categorized['fatal'])}\n")
        report.append(f"- **Error**: {len(categorized['error'])}\n")
        report.append(f"- **Warning**: {len(categorized['warning'])}\n")
        report.append(f"- **Refactor**: {len(categorized['refactor'])}\n")
        report.append(f"- **Convention**: {len(categorized['convention'])}\n")
        report.append(f"- **Total**: {len(issues)}\n\n")
        
        # Improvement plan
        report.append("## Improvement Plan\n\n")
        for item in plan:
            report.append(f"### {item.get('priority', 'N/A')} Priority: {item['category']}\n\n")
            
            if 'count' in item:
                report.append(f"**Count**: {item['count']}\n\n")
            
            if 'recommendation' in item:
                report.append(f"**Recommendation**: {item['recommendation']}\n\n")
            
            if 'common_types' in item:
                report.append("**Most common issues**:\n")
                for ct in item['common_types']:
                    report.append(f"- {ct['id']}: {ct['count']} occurrences\n")
                report.append("\n")
            
            if 'modules' in item:
                report.append("**Modules**:\n")
                for mod in item['modules']:
                    report.append(f"- {mod['name']}: {mod['issues']} issues\n")
                report.append("\n")
            
            if 'files' in item:
                report.append("**Files**:\n")
                for file in item['files'][:10]:  # Limit to 10
                    report.append(f"- {file}\n")
                report.append("\n")
        
        # Quick wins
        report.append("## Quick Wins\n\n")
        report.append("These improvements can significantly boost your score:\n\n")
        report.append("1. **Add module docstrings** - Every module should have a docstring\n")
        report.append("2. **Add function docstrings** - Document all public functions\n")
        report.append("3. **Remove unused imports** - Clean up import statements\n")
        report.append("4. **Fix line length** - Keep lines under 100 characters\n")
        report.append("5. **Add type hints** - Use type annotations where appropriate\n")
        report.append("6. **Remove unused variables** - Clean up dead code\n")
        report.append("7. **Fix naming conventions** - Use snake_case for functions/variables\n\n")
        
        # Save report
        report_file = self.reports_dir / 'pylint_improvement_plan.md'
        with open(report_file, 'w') as f:
            f.write(''.join(report))
        
        print(f"\nReport saved to: {report_file}")
        
        return ''.join(report)
    
    def run(self):
        """Run full analysis and generate report."""
        print("=" * 60)
        print("Pylint Improvement Analysis")
        print("=" * 60)
        
        issues, full_output = self.run_pylint_analysis()
        report = self.generate_report(issues, full_output)
        
        print("\n" + report)
        
        return issues, report


def main():
    """Main entry point."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Run analysis
    improver = PylintImprover(project_root)
    improver.run()


if __name__ == '__main__':
    main()
