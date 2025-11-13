"""Unit tests for SAS-96: Bunk Allowance Models.

Tests the CourseConfig and StudentBunkAllowance models.
"""

import pytest
from datetime import datetime


class TestCourseConfig:
    """Test cases for CourseConfig model."""

    def test_course_config_creation(self, app):
        """Test creating a course configuration."""
        with app.app_context():
            CourseConfig = app.CourseConfig
            db = app.db
            config = CourseConfig(
                course_id='CS101',
                course_name='Introduction to Computer Science',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            db.session.commit()

            retrieved = CourseConfig.query.filter_by(course_id='CS101').first()
            assert retrieved is not None
            assert retrieved.course_name == 'Introduction to Computer Science'
            assert retrieved.total_classes == 60
            assert retrieved.bunk_allowance_percentage == 25.0
            assert retrieved.min_attendance_percentage == 75.0

    def test_get_max_bunk_allowed(self, app):
        """Test calculation of maximum bunk allowed."""
        with app.app_context():
            CourseConfig = app.CourseConfig
            config = CourseConfig(
                course_id='CS102',
                course_name='Data Structures',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            
            max_bunk = config.get_max_bunk_allowed()
            assert max_bunk == 15  # 25% of 60

    def test_get_min_classes_required(self, app):
        """Test calculation of minimum classes required."""
        with app.app_context():
            config = CourseConfig(
                course_id='CS103',
                course_name='Algorithms',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            
            min_required = config.get_min_classes_required()
            assert min_required == 45  # 75% of 60

    def test_course_config_to_dict(self, app):
        """Test conversion to dictionary."""
        with app.app_context():
            config = CourseConfig(
                course_id='CS104',
                course_name='Operating Systems',
                total_classes=50,
                bunk_allowance_percentage=20.0,
                min_attendance_percentage=80.0
            )
            
            config_dict = config.to_dict()
            assert config_dict['course_id'] == 'CS104'
            assert config_dict['course_name'] == 'Operating Systems'
            assert config_dict['total_classes'] == 50
            assert config_dict['max_bunk_allowed'] == 10
            assert config_dict['min_classes_required'] == 40

    def test_course_config_unique_constraint(self, app):
        """Test that course_id is unique."""
        with app.app_context():
            config1 = CourseConfig(
                course_id='CS105',
                course_name='Networks',
                total_classes=60
            )
            db.session.add(config1)
            db.session.commit()

            config2 = CourseConfig(
                course_id='CS105',
                course_name='Networks 2',
                total_classes=60
            )
            db.session.add(config2)
            
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()


class TestStudentBunkAllowance:
    """Test cases for StudentBunkAllowance model."""

    def test_student_bunk_allowance_creation(self, app):
        """Test creating a student bunk allowance record."""
        with app.app_context():
            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS001',
                course_id='CS101',
                total_classes_held=20,
                classes_attended=18,
                classes_missed=2
            )
            db.session.add(allowance)
            db.session.commit()

            retrieved = StudentBunkAllowance.query.filter_by(
                student_srn='PES1UG23CS001',
                course_id='CS101'
            ).first()
            
            assert retrieved is not None
            assert retrieved.total_classes_held == 20
            assert retrieved.classes_attended == 18
            assert retrieved.classes_missed == 2

    def test_calculate_attendance_percentage(self, app):
        """Test attendance percentage calculation."""
        with app.app_context():
            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS002',
                course_id='CS101',
                total_classes_held=20,
                classes_attended=16,
                classes_missed=4
            )
            
            percentage = allowance.calculate_attendance_percentage()
            assert percentage == 80.0

    def test_calculate_attendance_percentage_zero_classes(self, app):
        """Test attendance percentage with zero classes."""
        with app.app_context():
            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS003',
                course_id='CS101',
                total_classes_held=0,
                classes_attended=0,
                classes_missed=0
            )
            
            percentage = allowance.calculate_attendance_percentage()
            assert percentage == 100.0

    def test_update_from_attendance_records(self, app):
        """Test updating from attendance records."""
        with app.app_context():
            # Create course config
            config = CourseConfig(
                course_id='CS106',
                course_name='Database Systems',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            db.session.commit()

            # Create student allowance
            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS004',
                course_id='CS106',
                total_classes_held=20,
                classes_attended=14,
                classes_missed=6
            )
            
            allowance.update_from_attendance_records(config)
            
            assert allowance.current_attendance_percentage == 70.0
            assert allowance.remaining_bunk_allowance == 9  # 15 max - 6 missed
            assert allowance.is_attendance_critical is True  # Below 75%

    def test_student_bunk_allowance_to_dict(self, app):
        """Test conversion to dictionary."""
        with app.app_context():
            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS005',
                course_id='CS107',
                total_classes_held=30,
                classes_attended=25,
                classes_missed=5,
                current_attendance_percentage=83.33,
                remaining_bunk_allowance=10,
                is_attendance_critical=False
            )
            
            allowance_dict = allowance.to_dict()
            assert allowance_dict['student_srn'] == 'PES1UG23CS005'
            assert allowance_dict['course_id'] == 'CS107'
            assert allowance_dict['total_classes_held'] == 30
            assert allowance_dict['classes_attended'] == 25
            assert allowance_dict['classes_missed'] == 5
            assert allowance_dict['is_attendance_critical'] is False

    def test_unique_student_course_constraint(self, app):
        """Test unique constraint on student_srn and course_id."""
        with app.app_context():
            allowance1 = StudentBunkAllowance(
                student_srn='PES1UG23CS006',
                course_id='CS108',
                total_classes_held=10,
                classes_attended=9,
                classes_missed=1
            )
            db.session.add(allowance1)
            db.session.commit()

            allowance2 = StudentBunkAllowance(
                student_srn='PES1UG23CS006',
                course_id='CS108',
                total_classes_held=20,
                classes_attended=18,
                classes_missed=2
            )
            db.session.add(allowance2)
            
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_attendance_critical_threshold(self, app):
        """Test critical attendance detection."""
        with app.app_context():
            # Create course config with 75% minimum
            config = CourseConfig(
                course_id='CS109',
                course_name='Software Engineering',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            db.session.commit()

            # Test case 1: Above threshold (not critical)
            allowance1 = StudentBunkAllowance(
                student_srn='PES1UG23CS007',
                course_id='CS109',
                total_classes_held=40,
                classes_attended=32,
                classes_missed=8
            )
            allowance1.update_from_attendance_records(config)
            assert allowance1.is_attendance_critical is False  # 80% > 75%

            # Test case 2: Below threshold (critical)
            allowance2 = StudentBunkAllowance(
                student_srn='PES1UG23CS008',
                course_id='CS109',
                total_classes_held=40,
                classes_attended=28,
                classes_missed=12
            )
            allowance2.update_from_attendance_records(config)
            assert allowance2.is_attendance_critical is True  # 70% < 75%

    def test_remaining_bunk_calculation(self, app):
        """Test remaining bunk allowance calculation."""
        with app.app_context():
            config = CourseConfig(
                course_id='CS110',
                course_name='Machine Learning',
                total_classes=60,
                bunk_allowance_percentage=20.0,  # 12 bunks allowed
                min_attendance_percentage=80.0
            )
            db.session.add(config)
            db.session.commit()

            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS009',
                course_id='CS110',
                total_classes_held=30,
                classes_attended=26,
                classes_missed=4
            )
            allowance.update_from_attendance_records(config)
            
            # 12 max bunks - 4 used = 8 remaining
            assert allowance.remaining_bunk_allowance == 8
