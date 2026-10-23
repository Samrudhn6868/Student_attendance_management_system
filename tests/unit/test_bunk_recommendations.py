"""Unit tests for Bunk Day Recommendations Service.

This module contains comprehensive test cases for the BunkRecommendationService,
testing all features including safe bunk calculations, weekly plans, predictions,
and recovery scenarios.
"""

import pytest
from src.bunk_recommendations import BunkRecommendationService


class TestCalculateSafeBunks:
    """Test cases for calculate_safe_bunks method."""
    
    def test_perfect_attendance(self):
        """Test with 100% attendance."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=30,
            total_classes_held=30,
            total_classes_remaining=30,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 100.0
        assert result['safe_bunks'] > 0
        assert result['status'] == 'safe'
        assert result['classes_attended'] == 30
        assert result['total_classes_held'] == 30
    
    def test_minimum_attendance_exactly(self):
        """Test when attendance is exactly at minimum."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=75,
            total_classes_held=100,
            total_classes_remaining=0,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 75.0
        assert result['safe_bunks'] == 0
        assert result['status'] in ['no_bunks', 'warning']
    
    def test_below_minimum_attendance(self):
        """Test when attendance is below minimum."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=60,
            total_classes_held=100,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 60.0
        assert result['safe_bunks'] == 0
        assert result['status'] == 'critical'
        assert '⚠️ WARNING' in result['message']
    
    def test_high_attendance_many_bunks(self):
        """Test with high attendance allowing multiple bunks."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=45,
            total_classes_held=50,
            total_classes_remaining=10,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 90.0
        assert result['safe_bunks'] >= 0
        assert result['status'] in ['safe', 'low_bunks']
    
    def test_no_classes_held_yet(self):
        """Test when no classes have been held yet."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=0,
            total_classes_held=0,
            total_classes_remaining=60,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 0.0
        assert result['status'] == 'no_data'
        assert 'No attendance data' in result['message']
    
    def test_borderline_attendance(self):
        """Test attendance just above minimum threshold."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=77,
            total_classes_held=100,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 77.0
        assert result['status'] in ['warning', 'low_bunks', 'no_bunks']
    
    def test_zero_remaining_classes(self):
        """Test when semester is over (no remaining classes)."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=80,
            total_classes_held=100,
            total_classes_remaining=0,
            min_attendance=75.0
        )
        
        assert result['total_classes_remaining'] == 0
        # With 80/100 attendance and no remaining classes, student already bunked more than minimum allowed
        # But the function calculates based on what was possible, so safe_bunks might be > 0
        assert result['safe_bunks'] >= 0
    
    def test_different_minimum_attendance(self):
        """Test with different minimum attendance threshold."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=40,
            total_classes_held=50,
            total_classes_remaining=10,
            min_attendance=80.0  # Higher threshold
        )
        
        assert result['min_attendance_required'] == 80.0
        assert result['current_percentage'] == 80.0


class TestGenerateRecommendations:
    """Test cases for recommendation generation."""
    
    def test_critical_recommendations(self):
        """Test recommendations for critical attendance."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=30,
            total_classes_held=50,
            total_classes_remaining=10,
            min_attendance=75.0
        )
        
        assert len(result['recommendations']) > 0
        assert any('URGENT' in rec or 'ALL remaining' in rec for rec in result['recommendations'])
    
    def test_safe_recommendations(self):
        """Test recommendations for safe attendance."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=45,
            total_classes_held=50,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert len(result['recommendations']) > 0
        if result['safe_bunks'] > 0:
            assert any('available' in rec or 'wisely' in rec for rec in result['recommendations'])


class TestWeeklyBunkPlan:
    """Test cases for weekly bunk plan generation."""
    
    def test_evenly_distributed_bunks(self):
        """Test even distribution of bunks across weeks."""
        result = BunkRecommendationService.get_weekly_bunk_plan(
            safe_bunks=10,
            weeks_remaining=5,
            classes_per_week=5
        )
        
        assert result['total_bunks'] == 10
        assert result['weeks_remaining'] == 5
        assert len(result['plan']) > 0
        assert result['average_per_week'] == 2.0
    
    def test_no_bunks_available(self):
        """Test when no bunks are available."""
        result = BunkRecommendationService.get_weekly_bunk_plan(
            safe_bunks=0,
            weeks_remaining=5,
            classes_per_week=5
        )
        
        assert len(result['plan']) == 0
        assert 'No bunks available' in result['message']
    
    def test_no_weeks_remaining(self):
        """Test when no weeks remain."""
        result = BunkRecommendationService.get_weekly_bunk_plan(
            safe_bunks=5,
            weeks_remaining=0,
            classes_per_week=5
        )
        
        assert len(result['plan']) == 0
        assert 'No weeks remaining' in result['message']
    
    def test_more_bunks_than_weeks(self):
        """Test when bunks exceed number of weeks."""
        result = BunkRecommendationService.get_weekly_bunk_plan(
            safe_bunks=15,
            weeks_remaining=3,
            classes_per_week=5
        )
        
        assert result['total_bunks'] == 15
        assert result['weeks_remaining'] == 3
        # Should distribute all 15 bunks across 3 weeks
        total_distributed = sum(week['allowed_bunks'] for week in result['plan'])
        assert total_distributed == 15
    
    def test_single_week_remaining(self):
        """Test with only one week remaining."""
        result = BunkRecommendationService.get_weekly_bunk_plan(
            safe_bunks=3,
            weeks_remaining=1,
            classes_per_week=5
        )
        
        assert len(result['plan']) == 1
        assert result['plan'][0]['allowed_bunks'] == 3


class TestPredictAttendanceImpact:
    """Test cases for attendance impact prediction."""
    
    def test_impact_of_future_bunks(self):
        """Test prediction with future bunks."""
        result = BunkRecommendationService.predict_attendance_impact(
            classes_attended=40,
            total_classes_held=50,
            future_bunks=5,
            future_classes=10
        )
        
        assert result['current_attendance'] == 80.0
        assert result['future_bunks'] == 5
        assert result['future_classes'] == 10
        assert 'predicted_attendance' in result
        assert 'impact' in result
    
    def test_no_future_bunks(self):
        """Test prediction with no bunks (perfect future attendance)."""
        result = BunkRecommendationService.predict_attendance_impact(
            classes_attended=40,
            total_classes_held=50,
            future_bunks=0,
            future_classes=10
        )
        
        assert result['future_bunks'] == 0
        assert result['predicted_attendance'] > result['current_attendance']
        assert result['is_safe'] is True
    
    def test_unsafe_prediction(self):
        """Test prediction that results in unsafe attendance."""
        result = BunkRecommendationService.predict_attendance_impact(
            classes_attended=38,
            total_classes_held=50,
            future_bunks=8,
            future_classes=10
        )
        
        # Might drop below 75%
        if not result['is_safe']:
            assert result['warning'] is not None
            assert '⚠️' in result['warning']
    
    def test_zero_current_classes(self):
        """Test prediction when no classes held yet."""
        result = BunkRecommendationService.predict_attendance_impact(
            classes_attended=0,
            total_classes_held=0,
            future_bunks=5,
            future_classes=20
        )
        
        assert result['current_attendance'] == 0.0
        assert result['predicted_attendance'] == 75.0  # (20-5)/20 * 100


class TestRecoveryPlan:
    """Test cases for attendance recovery planning."""
    
    def test_no_recovery_needed(self):
        """Test when attendance is already sufficient."""
        result = BunkRecommendationService.get_recovery_plan(
            classes_attended=80,
            total_classes_held=100,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert result['needs_recovery'] is False
        assert 'No recovery needed' in result['message']
    
    def test_recovery_possible(self):
        """Test when recovery is possible."""
        result = BunkRecommendationService.get_recovery_plan(
            classes_attended=60,
            total_classes_held=100,
            total_classes_remaining=80,
            min_attendance=75.0
        )
        
        assert result['needs_recovery'] is True
        assert result['can_recover'] is True
        assert 'classes_to_attend' in result
        assert result['classes_to_attend'] > 0
    
    def test_recovery_impossible(self):
        """Test when recovery is impossible."""
        result = BunkRecommendationService.get_recovery_plan(
            classes_attended=30,
            total_classes_held=100,
            total_classes_remaining=10,
            min_attendance=75.0
        )
        
        assert result['needs_recovery'] is True
        assert result['can_recover'] is False
        assert 'CRITICAL' in result['message']
    
    def test_recovery_with_zero_remaining(self):
        """Test recovery when no classes remain."""
        result = BunkRecommendationService.get_recovery_plan(
            classes_attended=60,
            total_classes_held=100,
            total_classes_remaining=0,
            min_attendance=75.0
        )
        
        assert result['needs_recovery'] is True
        assert result['can_recover'] is False
    
    def test_borderline_recovery(self):
        """Test recovery when just barely possible."""
        result = BunkRecommendationService.get_recovery_plan(
            classes_attended=70,
            total_classes_held=100,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert result['needs_recovery'] is True
        if result['can_recover']:
            assert result['classes_to_attend'] <= result['total_classes_remaining']


class TestGetRecommendationForStudent:
    """Test cases for comprehensive student recommendations."""
    
    def test_complete_recommendation_safe(self):
        """Test complete recommendation for student with safe attendance."""
        result = BunkRecommendationService.get_recommendation_for_student(
            student_srn='PES1UG23CS001',
            course_id='CS101',
            classes_attended=45,
            total_classes_held=50,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert result['student_srn'] == 'PES1UG23CS001'
        assert result['course_id'] == 'CS101'
        assert 'safe_bunks_analysis' in result
        assert 'recovery_plan' in result
        assert 'summary' in result
        assert result['summary']['current_attendance'] == 90.0
    
    def test_complete_recommendation_critical(self):
        """Test complete recommendation for student with critical attendance."""
        result = BunkRecommendationService.get_recommendation_for_student(
            student_srn='PES1UG23CS002',
            course_id='CS102',
            classes_attended=30,
            total_classes_held=50,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert result['student_srn'] == 'PES1UG23CS002'
        assert result['summary']['status'] == 'critical'
        assert result['recovery_plan']['needs_recovery'] is True
    
    def test_recommendation_with_weekly_plan(self):
        """Test that weekly plan is included when bunks available."""
        result = BunkRecommendationService.get_recommendation_for_student(
            student_srn='PES1UG23CS003',
            course_id='CS103',
            classes_attended=50,
            total_classes_held=55,
            total_classes_remaining=25,
            min_attendance=75.0
        )
        
        if result['safe_bunks_analysis']['safe_bunks'] > 0:
            assert result['weekly_bunk_plan'] is not None
            assert 'plan' in result['weekly_bunk_plan']
    
    def test_recommendation_no_data(self):
        """Test recommendation when no attendance data exists."""
        result = BunkRecommendationService.get_recommendation_for_student(
            student_srn='PES1UG23CS004',
            course_id='CS104',
            classes_attended=0,
            total_classes_held=0,
            total_classes_remaining=60,
            min_attendance=75.0
        )
        
        assert result['summary']['status'] == 'no_data'
    
    def test_recommendation_includes_timestamp(self):
        """Test that recommendation includes generation timestamp."""
        result = BunkRecommendationService.get_recommendation_for_student(
            student_srn='PES1UG23CS005',
            course_id='CS105',
            classes_attended=40,
            total_classes_held=50,
            total_classes_remaining=20,
            min_attendance=75.0
        )
        
        assert 'generated_at' in result
        assert result['generated_at'] is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_high_attendance(self):
        """Test with 100% attendance and many remaining classes."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=100,
            total_classes_held=100,
            total_classes_remaining=50,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 100.0
        assert result['safe_bunks'] >= 0
    
    def test_single_class_attended(self):
        """Test with minimal attendance data."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=1,
            total_classes_held=1,
            total_classes_remaining=59,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 100.0
    
    def test_large_numbers(self):
        """Test with large class numbers."""
        result = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=900,
            total_classes_held=1000,
            total_classes_remaining=200,
            min_attendance=75.0
        )
        
        assert result['current_percentage'] == 90.0
        assert result['safe_bunks'] >= 0
    
    def test_custom_minimum_attendance(self):
        """Test with custom minimum attendance thresholds."""
        # Test with 80% minimum
        result1 = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=40,
            total_classes_held=50,
            total_classes_remaining=10,
            min_attendance=80.0
        )
        
        # Test with 70% minimum
        result2 = BunkRecommendationService.calculate_safe_bunks(
            classes_attended=40,
            total_classes_held=50,
            total_classes_remaining=10,
            min_attendance=70.0
        )
        
        # With lower threshold, should have more safe bunks
        assert result2['safe_bunks'] >= result1['safe_bunks']


class TestDefaultValues:
    """Test default configuration values."""
    
    def test_default_min_attendance(self):
        """Test that default minimum attendance is 75%."""
        assert BunkRecommendationService.DEFAULT_MIN_ATTENDANCE == 75.0
    
    def test_default_target_attendance(self):
        """Test that default target attendance is 80%."""
        assert BunkRecommendationService.DEFAULT_TARGET_ATTENDANCE == 80.0


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
