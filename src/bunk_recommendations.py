"""Simple Bunk Day Recommendations Service.

This module provides intelligent recommendations for when students can safely
skip classes (bunk) without falling below the minimum attendance requirement.

Features:
- Calculate safe bunk days based on current attendance percentage
- Recommend optimal days to maintain attendance above threshold
- Provide warnings when attendance is critical
- Consider remaining classes in the semester

Classes:
    BunkRecommendationService: Core service for bunk recommendations
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional


class BunkRecommendationService:
    """Service for generating intelligent bunk day recommendations."""

    # Default configuration
    DEFAULT_MIN_ATTENDANCE = 75.0  # Minimum required attendance percentage
    DEFAULT_TARGET_ATTENDANCE = 80.0  # Target attendance to maintain safety buffer
    
    @staticmethod
    def calculate_safe_bunks(
        classes_attended: int,
        total_classes_held: int,
        total_classes_remaining: int = 0,
        min_attendance: float = DEFAULT_MIN_ATTENDANCE
    ) -> Dict:
        """Calculate how many classes can be safely bunked.
        
        Args:
            classes_attended: Number of classes already attended
            total_classes_held: Total classes held so far
            total_classes_remaining: Estimated remaining classes in semester
            min_attendance: Minimum required attendance percentage
            
        Returns:
            dict: Contains safe_bunks, current_percentage, status, and recommendations
        """
        if total_classes_held == 0:
            return {
                'safe_bunks': 0,
                'current_percentage': 0.0,
                'status': 'no_data',
                'message': 'No attendance data available yet',
                'recommendations': []
            }
        
        # Calculate current attendance
        classes_missed = total_classes_held - classes_attended
        current_percentage = (classes_attended / total_classes_held) * 100.0
        
        # Calculate total classes including remaining
        total_classes_semester = total_classes_held + total_classes_remaining
        
        # Calculate minimum classes needed to maintain min_attendance
        min_classes_needed = (min_attendance / 100.0) * total_classes_semester
        
        # Calculate how many more we can miss
        safe_bunks = max(0, int(total_classes_semester - min_classes_needed - classes_missed))
        
        # Determine status
        if current_percentage < min_attendance:
            status = 'critical'
            message = f'⚠️ WARNING: Attendance is below {min_attendance}%! You cannot bunk any classes.'
        elif current_percentage < min_attendance + 5:
            status = 'warning'
            message = f'⚠️ CAUTION: Attendance is close to minimum. Be very careful!'
        elif safe_bunks == 0:
            status = 'no_bunks'
            message = 'You have used all available bunks. Attend all remaining classes!'
        elif safe_bunks <= 2:
            status = 'low_bunks'
            message = f'You can safely bunk {safe_bunks} more class(es). Use them wisely!'
        else:
            status = 'safe'
            message = f'You can safely bunk {safe_bunks} class(es) while maintaining {min_attendance}% attendance.'
        
        # Generate recommendations
        recommendations = BunkRecommendationService._generate_recommendations(
            current_percentage=current_percentage,
            safe_bunks=safe_bunks,
            min_attendance=min_attendance,
            total_classes_remaining=total_classes_remaining
        )
        
        return {
            'safe_bunks': safe_bunks,
            'current_percentage': round(current_percentage, 2),
            'classes_attended': classes_attended,
            'total_classes_held': total_classes_held,
            'classes_missed': classes_missed,
            'total_classes_remaining': total_classes_remaining,
            'total_classes_semester': total_classes_semester,
            'min_attendance_required': min_attendance,
            'status': status,
            'message': message,
            'recommendations': recommendations
        }
    
    @staticmethod
    def _generate_recommendations(
        current_percentage: float,
        safe_bunks: int,
        min_attendance: float,
        total_classes_remaining: int
    ) -> List[str]:
        """Generate personalized recommendations based on attendance status.
        
        Args:
            current_percentage: Current attendance percentage
            safe_bunks: Number of safe bunks available
            min_attendance: Minimum required attendance
            total_classes_remaining: Remaining classes
            
        Returns:
            list: List of recommendation strings
        """
        recommendations = []
        
        if current_percentage < min_attendance:
            recommendations.append('🚨 URGENT: Attend ALL remaining classes to improve attendance')
            recommendations.append(f'You need perfect attendance to recover above {min_attendance}%')
            recommendations.append('Consider requesting official leave if you must miss classes')
        elif current_percentage < min_attendance + 5:
            recommendations.append('⚠️ Your attendance is borderline. Be very cautious!')
            recommendations.append('Avoid bunking unless absolutely necessary')
            recommendations.append('Any absence could push you below minimum requirement')
        elif safe_bunks == 0:
            recommendations.append('You have exhausted all bunk allowance')
            recommendations.append('Plan to attend all remaining classes')
            recommendations.append('Use official leave requests if emergencies arise')
        elif safe_bunks <= 2:
            recommendations.append(f'You have only {safe_bunks} bunk(s) left - use strategically')
            recommendations.append('Save them for genuine emergencies or important events')
            recommendations.append('Consider the academic calendar before deciding')
        else:
            recommendations.append(f'✅ You have {safe_bunks} safe bunks available')
            recommendations.append('Distribute them wisely across remaining weeks')
            recommendations.append(f'Keep attendance above {min_attendance + 5}% for safety buffer')
            
            if total_classes_remaining > 0:
                avg_bunks_per_week = safe_bunks / max(1, total_classes_remaining / 5)
                recommendations.append(
                    f'Suggested: ~{round(avg_bunks_per_week, 1)} bunk(s) per week maximum'
                )
        
        return recommendations
    
    @staticmethod
    def get_weekly_bunk_plan(
        safe_bunks: int,
        weeks_remaining: int,
        classes_per_week: int = 5
    ) -> Dict:
        """Generate a weekly bunk plan for optimal distribution.
        
        Args:
            safe_bunks: Total safe bunks available
            weeks_remaining: Number of weeks remaining in semester
            classes_per_week: Average classes per week
            
        Returns:
            dict: Weekly bunk distribution plan
        """
        if weeks_remaining <= 0:
            return {
                'plan': [],
                'message': 'No weeks remaining in semester'
            }
        
        if safe_bunks <= 0:
            return {
                'plan': [],
                'message': 'No bunks available'
            }
        
        # Calculate bunks per week
        bunks_per_week = safe_bunks / weeks_remaining
        
        plan = []
        remaining_bunks = safe_bunks
        
        for week in range(1, weeks_remaining + 1):
            # Distribute evenly, with extra bunks in early weeks
            week_bunks = min(remaining_bunks, int(bunks_per_week) + (1 if remaining_bunks > bunks_per_week else 0))
            
            if week_bunks > 0:
                plan.append({
                    'week': week,
                    'allowed_bunks': week_bunks,
                    'suggestion': f'Week {week}: You can bunk up to {week_bunks} class(es)'
                })
                remaining_bunks -= week_bunks
        
        return {
            'plan': plan,
            'total_bunks': safe_bunks,
            'weeks_remaining': weeks_remaining,
            'average_per_week': round(bunks_per_week, 2),
            'message': f'Distribute {safe_bunks} bunk(s) across {weeks_remaining} week(s)'
        }
    
    @staticmethod
    def predict_attendance_impact(
        classes_attended: int,
        total_classes_held: int,
        future_bunks: int,
        future_classes: int
    ) -> Dict:
        """Predict attendance percentage after bunking specific days.
        
        Args:
            classes_attended: Current classes attended
            total_classes_held: Total classes held so far
            future_bunks: Number of classes planning to bunk
            future_classes: Total future classes
            
        Returns:
            dict: Predicted attendance impact
        """
        if total_classes_held == 0:
            current_percentage = 0.0
        else:
            current_percentage = (classes_attended / total_classes_held) * 100.0
        
        # Calculate future scenario
        total_future_classes = total_classes_held + future_classes
        future_attended = classes_attended + (future_classes - future_bunks)
        future_percentage = (future_attended / total_future_classes) * 100.0 if total_future_classes > 0 else 0.0
        
        impact = future_percentage - current_percentage
        
        return {
            'current_attendance': round(current_percentage, 2),
            'predicted_attendance': round(future_percentage, 2),
            'impact': round(impact, 2),
            'future_bunks': future_bunks,
            'future_classes': future_classes,
            'is_safe': future_percentage >= BunkRecommendationService.DEFAULT_MIN_ATTENDANCE,
            'warning': None if future_percentage >= BunkRecommendationService.DEFAULT_MIN_ATTENDANCE 
                      else f'⚠️ This will bring attendance below {BunkRecommendationService.DEFAULT_MIN_ATTENDANCE}%'
        }
    
    @staticmethod
    def get_recovery_plan(
        classes_attended: int,
        total_classes_held: int,
        total_classes_remaining: int,
        min_attendance: float = DEFAULT_MIN_ATTENDANCE
    ) -> Dict:
        """Generate a recovery plan if attendance is below minimum.
        
        Args:
            classes_attended: Current classes attended
            total_classes_held: Total classes held
            total_classes_remaining: Remaining classes
            min_attendance: Minimum required attendance
            
        Returns:
            dict: Recovery plan with required attendance
        """
        if total_classes_held == 0:
            return {
                'needs_recovery': False,
                'message': 'No attendance data available'
            }
        
        current_percentage = (classes_attended / total_classes_held) * 100.0
        
        if current_percentage >= min_attendance:
            return {
                'needs_recovery': False,
                'current_percentage': round(current_percentage, 2),
                'message': f'✅ Attendance is above {min_attendance}%. No recovery needed.'
            }
        
        # Calculate required attendance
        total_classes_semester = total_classes_held + total_classes_remaining
        min_classes_needed = (min_attendance / 100.0) * total_classes_semester
        classes_to_attend = int(min_classes_needed - classes_attended) + 1
        
        # Calculate if recovery is possible
        can_recover = classes_to_attend <= total_classes_remaining
        
        if can_recover:
            recovery_percentage = (classes_to_attend / total_classes_remaining) * 100.0
            return {
                'needs_recovery': True,
                'can_recover': True,
                'current_percentage': round(current_percentage, 2),
                'classes_to_attend': classes_to_attend,
                'total_classes_remaining': total_classes_remaining,
                'allowed_bunks_during_recovery': max(0, total_classes_remaining - classes_to_attend),
                'recovery_percentage': round(recovery_percentage, 2),
                'message': f'📈 Attend {classes_to_attend} out of {total_classes_remaining} remaining classes',
                'plan': f'Attend {recovery_percentage:.1f}% of remaining classes to reach {min_attendance}%'
            }
        else:
            return {
                'needs_recovery': True,
                'can_recover': False,
                'current_percentage': round(current_percentage, 2),
                'classes_needed': classes_to_attend,
                'total_classes_remaining': total_classes_remaining,
                'message': '🚨 CRITICAL: Cannot recover to minimum attendance even with perfect attendance',
                'recommendation': 'Speak with faculty/administration immediately about your attendance situation'
            }
    
    @staticmethod
    def get_recommendation_for_student(
        student_srn: str,
        course_id: str,
        classes_attended: int,
        total_classes_held: int,
        total_classes_remaining: int = 20,
        min_attendance: float = DEFAULT_MIN_ATTENDANCE
    ) -> Dict:
        """Get comprehensive bunk recommendations for a student in a course.
        
        Args:
            student_srn: Student SRN
            course_id: Course identifier
            classes_attended: Classes attended
            total_classes_held: Total classes held
            total_classes_remaining: Remaining classes in semester
            min_attendance: Minimum required attendance percentage
            
        Returns:
            dict: Complete recommendation report
        """
        # Calculate safe bunks
        safe_bunks_data = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=classes_attended,
            total_classes_held=total_classes_held,
            total_classes_remaining=total_classes_remaining,
            min_attendance=min_attendance
        )
        
        # Get recovery plan if needed
        recovery_plan = BunkRecommendationService.get_recovery_plan(
            classes_attended=classes_attended,
            total_classes_held=total_classes_held,
            total_classes_remaining=total_classes_remaining,
            min_attendance=min_attendance
        )
        
        # Get weekly plan if bunks are available
        weekly_plan = None
        if safe_bunks_data['safe_bunks'] > 0 and total_classes_remaining > 0:
            weeks_remaining = max(1, total_classes_remaining // 5)
            weekly_plan = BunkRecommendationService.get_weekly_bunk_plan(
                safe_bunks=safe_bunks_data['safe_bunks'],
                weeks_remaining=weeks_remaining
            )
        
        return {
            'student_srn': student_srn,
            'course_id': course_id,
            'generated_at': datetime.now().isoformat(),
            'safe_bunks_analysis': safe_bunks_data,
            'recovery_plan': recovery_plan,
            'weekly_bunk_plan': weekly_plan,
            'summary': {
                'status': safe_bunks_data['status'],
                'main_message': safe_bunks_data['message'],
                'safe_bunks': safe_bunks_data['safe_bunks'],
                'current_attendance': safe_bunks_data['current_percentage']
            }
        }
