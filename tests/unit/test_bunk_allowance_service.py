"""Unit tests for SAS-96: Bunk Allowance Service Layer.

Tests the BunkAllowanceService business logic.
"""

import pytest
from datetime import datetime
from src.models import db, Attendance
from src.bunk_allowance_models import CourseConfig, StudentBunkAllowance
from src.bunk_allowance_service import BunkAllowanceService


class TestBunkAllowanceService:
    """Test cases for BunkAllowanceService."""

    def test_get_or_create_course_config_new(self, app):
        """Test creating a new course config."""
        with app.app_context():
            config = BunkAllowanceService.get_or_create_course_config(
                'CS201',
                course_name='Advanced Programming',
                total_classes=50,
                bunk_allowance_percentage=20.0,
                min_attendance_percentage=80.0
            )
            
            assert config is not None
            assert config.course_id == 'CS201'
            assert config.course_name == 'Advanced Programming'
            assert config.total_classes == 50
            assert config.bunk_allowance_percentage == 20.0

    def test_get_or_create_course_config_existing(self, app):
        """Test getting an existing course config."""
        with app.app_context():
            # Create initial config
            config1 = BunkAllowanceService.get_or_create_course_config(
                'CS202',
                course_name='Web Development',
                total_classes=60
            )
            first_id = config1.id
            
            # Get the same config
            config2 = BunkAllowanceService.get_or_create_course_config('CS202')
            
            assert config2.id == first_id
            assert config2.course_name == 'Web Development'

    def test_calculate_student_attendance_stats(self, app):
        """Test calculating attendance statistics."""
        with app.app_context():
            # Create attendance records
            records = [
                Attendance(student_srn='PES1UG23CS101', course_id='CS203',
                          date=datetime.now().date(), status='present'),
                Attendance(student_srn='PES1UG23CS101', course_id='CS203',
                          date=datetime.now().date(), status='present'),
                Attendance(student_srn='PES1UG23CS101', course_id='CS203',
                          date=datetime.now().date(), status='absent'),
                Attendance(student_srn='PES1UG23CS101', course_id='CS203',
                          date=datetime.now().date(), status='present'),
            ]
            for record in records:
                db.session.add(record)
            db.session.commit()
            
            stats = BunkAllowanceService.calculate_student_attendance_stats(
                'PES1UG23CS101', 'CS203'
            )
            
            assert stats['total_classes_held'] == 4
            assert stats['classes_attended'] == 3
            assert stats['classes_missed'] == 1
            assert stats['attendance_percentage'] == 75.0

    def test_calculate_student_attendance_stats_no_records(self, app):
        """Test stats calculation with no attendance records."""
        with app.app_context():
            stats = BunkAllowanceService.calculate_student_attendance_stats(
                'PES1UG23CS999', 'CS999'
            )
            
            assert stats['total_classes_held'] == 0
            assert stats['classes_attended'] == 0
            assert stats['classes_missed'] == 0
            assert stats['attendance_percentage'] == 100.0

    def test_update_student_bunk_allowance(self, app):
        """Test updating student bunk allowance."""
        with app.app_context():
            # Create course config
            BunkAllowanceService.get_or_create_course_config(
                'CS204',
                total_classes=60,
                bunk_allowance_percentage=25.0
            )
            
            # Create attendance records
            for i in range(20):
                status = 'present' if i < 16 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS102',
                    course_id='CS204',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
            
            # Update bunk allowance
            allowance = BunkAllowanceService.update_student_bunk_allowance(
                'PES1UG23CS102', 'CS204'
            )
            
            assert allowance.total_classes_held == 20
            assert allowance.classes_attended == 16
            assert allowance.classes_missed == 4
            assert allowance.current_attendance_percentage == 80.0
            assert allowance.remaining_bunk_allowance == 11  # 15 max - 4 used

    def test_get_student_bunk_allowance_single_course(self, app):
        """Test getting bunk allowance for a single course."""
        with app.app_context():
            # Setup
            BunkAllowanceService.get_or_create_course_config('CS205')
            record = Attendance(
                student_srn='PES1UG23CS103',
                course_id='CS205',
                date=datetime.now().date(),
                status='present'
            )
            db.session.add(record)
            db.session.commit()
            
            # Get allowance
            allowance = BunkAllowanceService.get_student_bunk_allowance(
                'PES1UG23CS103', 'CS205'
            )
            
            assert isinstance(allowance, dict)
            assert allowance['student_srn'] == 'PES1UG23CS103'
            assert allowance['course_id'] == 'CS205'

    def test_get_student_bunk_allowance_all_courses(self, app):
        """Test getting bunk allowance for all courses."""
        with app.app_context():
            # Setup multiple courses
            for course in ['CS206', 'CS207']:
                BunkAllowanceService.get_or_create_course_config(course)
                record = Attendance(
                    student_srn='PES1UG23CS104',
                    course_id=course,
                    date=datetime.now().date(),
                    status='present'
                )
                db.session.add(record)
            db.session.commit()
            
            # Get all allowances
            allowances = BunkAllowanceService.get_student_bunk_allowance(
                'PES1UG23CS104'
            )
            
            assert isinstance(allowances, list)
            assert len(allowances) == 2
            course_ids = [a['course_id'] for a in allowances]
            assert 'CS206' in course_ids
            assert 'CS207' in course_ids

    def test_get_remaining_classes_breakdown(self, app):
        """Test getting detailed breakdown."""
        with app.app_context():
            # Setup
            BunkAllowanceService.get_or_create_course_config(
                'CS208',
                course_name='Distributed Systems',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            
            # Create 30 attendance records (24 present, 6 absent)
            for i in range(30):
                status = 'present' if i < 24 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS105',
                    course_id='CS208',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
            
            # Get breakdown
            breakdown = BunkAllowanceService.get_remaining_classes_breakdown(
                'PES1UG23CS105', 'CS208'
            )
            
            assert breakdown['student_srn'] == 'PES1UG23CS105'
            assert breakdown['course_id'] == 'CS208'
            assert breakdown['current_stats']['total_classes_held'] == 30
            assert breakdown['current_stats']['classes_attended'] == 24
            assert breakdown['current_stats']['attendance_percentage'] == 80.0
            assert breakdown['course_policy']['total_classes'] == 60
            assert breakdown['remaining_classes']['classes_remaining'] == 30
            assert 'projections' in breakdown

    def test_get_all_students_bunk_status(self, app):
        """Test getting all students' bunk status."""
        with app.app_context():
            # Setup
            BunkAllowanceService.get_or_create_course_config('CS209')
            
            students = ['PES1UG23CS106', 'PES1UG23CS107', 'PES1UG23CS108']
            for srn in students:
                record = Attendance(
                    student_srn=srn,
                    course_id='CS209',
                    date=datetime.now().date(),
                    status='present'
                )
                db.session.add(record)
            db.session.commit()
            
            # Update all allowances
            for srn in students:
                BunkAllowanceService.update_student_bunk_allowance(srn, 'CS209')
            
            # Get all statuses
            statuses = BunkAllowanceService.get_all_students_bunk_status('CS209')
            
            assert len(statuses) >= 3
            srns = [s['student_srn'] for s in statuses]
            for srn in students:
                assert srn in srns

    def test_get_critical_students(self, app):
        """Test getting students with critical attendance."""
        with app.app_context():
            # Setup
            BunkAllowanceService.get_or_create_course_config(
                'CS210',
                total_classes=60,
                min_attendance_percentage=75.0
            )
            
            # Student with critical attendance (60%)
            for i in range(10):
                status = 'present' if i < 6 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS109',
                    course_id='CS210',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
            
            BunkAllowanceService.update_student_bunk_allowance(
                'PES1UG23CS109', 'CS210'
            )
            
            # Get critical students
            critical = BunkAllowanceService.get_critical_students('CS210')
            
            assert len(critical) >= 1
            critical_srns = [s['student_srn'] for s in critical]
            assert 'PES1UG23CS109' in critical_srns

    def test_bulk_update_course_allowances(self, app):
        """Test bulk update of course allowances."""
        with app.app_context():
            # Setup
            BunkAllowanceService.get_or_create_course_config('CS211')
            
            students = ['PES1UG23CS110', 'PES1UG23CS111']
            for srn in students:
                record = Attendance(
                    student_srn=srn,
                    course_id='CS211',
                    date=datetime.now().date(),
                    status='present'
                )
                db.session.add(record)
            db.session.commit()
            
            # Bulk update
            result = BunkAllowanceService.bulk_update_course_allowances('CS211')
            
            assert result['course_id'] == 'CS211'
            assert result['total_students'] >= 2
            assert result['updated_count'] >= 2
            assert len(result['errors']) == 0

    def test_projection_calculations(self, app):
        """Test attendance projections."""
        with app.app_context():
            # Setup with 20/40 classes held, 16 attended
            BunkAllowanceService.get_or_create_course_config(
                'CS212',
                total_classes=40,
                bunk_allowance_percentage=25.0
            )
            
            for i in range(20):
                status = 'present' if i < 16 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS112',
                    course_id='CS212',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
            
            breakdown = BunkAllowanceService.get_remaining_classes_breakdown(
                'PES1UG23CS112', 'CS212'
            )
            
            # Current: 16/20 = 80%
            # If attend all remaining 20: (16+20)/40 = 90%
            # If use all bunks (no more attendance): 16/40 = 40%
            assert breakdown['projections']['if_attend_all_remaining'] == 90.0
            assert breakdown['projections']['if_use_all_bunks'] == 40.0
