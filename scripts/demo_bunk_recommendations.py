"""Demo script for Bunk Day Recommendations System.

This script demonstrates how to use the BunkRecommendationService
to get intelligent recommendations for when students can safely bunk classes.

Run this script to see example outputs for different attendance scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bunk_recommendations import BunkRecommendationService


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80)


def demo_safe_attendance():
    """Demonstrate recommendations for a student with safe attendance."""
    print_separator()
    print("SCENARIO 1: Student with Safe Attendance (90%)")
    print_separator()
    
    result = BunkRecommendationService.get_recommendation_for_student(
        student_srn='PES1UG23CS001',
        course_id='CS101',
        classes_attended=45,
        total_classes_held=50,
        total_classes_remaining=20,
        min_attendance=75.0
    )
    
    summary = result['summary']
    print(f"\n📊 Current Status:")
    print(f"   Attendance: {summary['current_attendance']}%")
    print(f"   Status: {summary['status'].upper()}")
    print(f"   {summary['main_message']}")
    
    print(f"\n💡 Recommendations:")
    for rec in result['safe_bunks_analysis']['recommendations']:
        print(f"   • {rec}")
    
    if result['weekly_bunk_plan']:
        print(f"\n📅 Weekly Bunk Plan:")
        for week in result['weekly_bunk_plan']['plan'][:3]:  # Show first 3 weeks
            print(f"   {week['suggestion']}")


def demo_critical_attendance():
    """Demonstrate recommendations for a student with critical attendance."""
    print_separator()
    print("SCENARIO 2: Student with Critical Attendance (60%)")
    print_separator()
    
    result = BunkRecommendationService.get_recommendation_for_student(
        student_srn='PES1UG23CS002',
        course_id='CS102',
        classes_attended=30,
        total_classes_held=50,
        total_classes_remaining=20,
        min_attendance=75.0
    )
    
    summary = result['summary']
    print(f"\n📊 Current Status:")
    print(f"   Attendance: {summary['current_attendance']}%")
    print(f"   Status: {summary['status'].upper()}")
    print(f"   {summary['main_message']}")
    
    print(f"\n💡 Recommendations:")
    for rec in result['safe_bunks_analysis']['recommendations']:
        print(f"   • {rec}")
    
    recovery = result['recovery_plan']
    if recovery['needs_recovery']:
        print(f"\n🚨 Recovery Plan Required:")
        if recovery['can_recover']:
            print(f"   • Attend {recovery['classes_to_attend']} out of {recovery['total_classes_remaining']} remaining classes")
            print(f"   • Recovery is possible with {recovery['recovery_percentage']:.1f}% attendance")
        else:
            print(f"   • {recovery['message']}")


def demo_borderline_attendance():
    """Demonstrate recommendations for borderline attendance."""
    print_separator()
    print("SCENARIO 3: Student with Borderline Attendance (77%)")
    print_separator()
    
    result = BunkRecommendationService.calculate_safe_bunks(
        classes_attended=77,
        total_classes_held=100,
        total_classes_remaining=20,
        min_attendance=75.0
    )
    
    print(f"\n📊 Current Status:")
    print(f"   Attendance: {result['current_percentage']}%")
    print(f"   Classes Attended: {result['classes_attended']}/{result['total_classes_held']}")
    print(f"   Classes Missed: {result['classes_missed']}")
    print(f"   Safe Bunks Available: {result['safe_bunks']}")
    print(f"   Status: {result['status'].upper()}")
    
    print(f"\n💡 Recommendations:")
    for rec in result['recommendations']:
        print(f"   • {rec}")


def demo_attendance_prediction():
    """Demonstrate attendance impact prediction."""
    print_separator()
    print("SCENARIO 4: Predicting Impact of Bunking 3 Classes")
    print_separator()
    
    current_attended = 40
    current_total = 50
    
    print(f"\n📊 Current Situation:")
    print(f"   Classes Attended: {current_attended}/{current_total}")
    print(f"   Current Attendance: {(current_attended/current_total)*100:.2f}%")
    
    prediction = BunkRecommendationService.predict_attendance_impact(
        classes_attended=current_attended,
        total_classes_held=current_total,
        future_bunks=3,
        future_classes=10
    )
    
    print(f"\n🔮 Prediction (if you bunk 3 out of next 10 classes):")
    print(f"   Predicted Attendance: {prediction['predicted_attendance']}%")
    print(f"   Impact: {prediction['impact']:+.2f}%")
    print(f"   Is Safe: {'✅ Yes' if prediction['is_safe'] else '❌ No'}")
    
    if prediction['warning']:
        print(f"   {prediction['warning']}")


def demo_weekly_plan():
    """Demonstrate weekly bunk distribution plan."""
    print_separator()
    print("SCENARIO 5: Weekly Bunk Distribution Plan")
    print_separator()
    
    plan = BunkRecommendationService.get_weekly_bunk_plan(
        safe_bunks=8,
        weeks_remaining=4,
        classes_per_week=5
    )
    
    print(f"\n📅 Distribution Plan:")
    print(f"   Total Bunks Available: {plan['total_bunks']}")
    print(f"   Weeks Remaining: {plan['weeks_remaining']}")
    print(f"   Average per Week: {plan['average_per_week']}")
    
    print(f"\n   Weekly Breakdown:")
    for week in plan['plan']:
        print(f"      Week {week['week']}: {week['allowed_bunks']} bunk(s) allowed")


def demo_all_scenarios():
    """Run all demonstration scenarios."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "BUNK DAY RECOMMENDATIONS SYSTEM" + " " * 26 + "║")
    print("║" + " " * 25 + "Demonstration Examples" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Run all demos
    demo_safe_attendance()
    demo_critical_attendance()
    demo_borderline_attendance()
    demo_attendance_prediction()
    demo_weekly_plan()
    
    # Summary
    print_separator()
    print("SUMMARY")
    print_separator()
    print("""
The Bunk Day Recommendations System provides:
    
✅ Safe bunk calculations based on current attendance
✅ Intelligent recommendations for different scenarios
✅ Weekly distribution plans for optimal bunk usage
✅ Attendance impact predictions before bunking
✅ Recovery plans for students below minimum attendance
✅ Critical warnings when attendance is at risk

Key Features:
• Configurable minimum attendance threshold (default: 75%)
• Considers remaining classes in semester
• Provides actionable, personalized recommendations
• Helps students maintain required attendance while optimizing their schedule
    """)
    
    print("\n" + "=" * 80 + "\n")


if __name__ == '__main__':
    # Run the demonstration
    demo_all_scenarios()
    
    print("\n💡 TIP: You can import and use these functions in your own code:")
    print("""
    from src.bunk_recommendations import BunkRecommendationService
    
    # Get recommendations for a student
    result = BunkRecommendationService.get_recommendation_for_student(
        student_srn='YOUR_SRN',
        course_id='COURSE_ID',
        classes_attended=45,
        total_classes_held=50,
        total_classes_remaining=20
    )
    
    print(result['summary']['main_message'])
    """)
