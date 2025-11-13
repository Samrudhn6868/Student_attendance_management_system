"""Simple unit tests for SAS-96: Bunk Allowance Models."""

import pytest


class TestCourseConfigSimple:
    """Simple test cases for CourseConfig model."""

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


class TestStudentBunkAllowanceSimple:
    """Simple test cases for StudentBunkAllowance model."""

    def test_student_bunk_allowance_creation(self, app):
        """Test creating a student bunk allowance record."""
        with app.app_context():
            StudentBunkAllowance = app.StudentBunkAllowance
            db = app.db
            
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

    def test_calculate_attendance_percentage(self, app):
        """Test attendance percentage calculation."""
        with app.app_context():
            StudentBunkAllowance = app.StudentBunkAllowance
            
            allowance = StudentBunkAllowance(
                student_srn='PES1UG23CS002',
                course_id='CS101',
                total_classes_held=20,
                classes_attended=16,
                classes_missed=4
            )
            
            percentage = allowance.calculate_attendance_percentage()
            assert percentage == 80.0
