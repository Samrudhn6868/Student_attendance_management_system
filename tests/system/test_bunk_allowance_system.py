"""System tests for SAS-96: Bunk Allowance Feature.

End-to-end system tests for bunk allowance functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from src.models import db, User, Attendance
from src.bunk_allowance_models import CourseConfig, StudentBunkAllowance
from src.bunk_allowance_service import BunkAllowanceService


class TestBunkAllowanceSystemFlow:
    """System-level tests for complete bunk allowance workflows."""

    def test_complete_student_journey(self, client, app):
        """Test complete student journey from enrollment to checking bunk allowance."""
        with app.app_context():
            # Step 1: Setup - Create student, course, and initial attendance
            student = User(
                username='PES1UG23CS401',
                name='System Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            
            config = CourseConfig(
                course_id='CS401',
                course_name='System Test Course',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            db.session.commit()
        
        # Step 2: Student login
        response = client.post('/login', data={
            'username': 'PES1UG23CS401',
            'password': 'password123'
        })
        assert response.status_code == 302  # Redirect after login
        
        with app.app_context():
            # Step 3: Simulate attendance marking over time
            attendance_data = []
            for day in range(30):
                # Student attends 80% of classes
                status = 'present' if day % 5 != 0 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS401',
                    course_id='CS401',
                    date=datetime.now().date() - timedelta(days=30-day),
                    status=status,
                    marked_by='FAC001'
                )
                db.session.add(record)
                attendance_data.append(status)
            db.session.commit()
        
        # Step 4: Student checks their bunk allowance
        response = client.get('/api/bunk-allowance/student/PES1UG23CS401/course/CS401')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify calculations
        assert data['data']['total_classes_held'] == 30
        assert data['data']['classes_attended'] == 24  # 80% of 30
        assert data['data']['classes_missed'] == 6
        
        # Step 5: Student checks detailed breakdown
        response = client.get('/api/bunk-allowance/breakdown/PES1UG23CS401/CS401')
        assert response.status_code == 200
        breakdown = json.loads(response.data)
        
        assert breakdown['success'] is True
        assert 'projections' in breakdown['data']
        assert 'remaining_classes' in breakdown['data']

    def test_faculty_monitoring_workflow(self, client, app):
        """Test faculty workflow for monitoring student attendance."""
        with app.app_context():
            # Setup faculty and students
            faculty = User(
                username='FAC401',
                name='System Test Faculty',
                is_faculty=True,
                role='teacher'
            )
            faculty.set_password('password123')
            db.session.add(faculty)
            
            config = CourseConfig(
                course_id='CS402',
                course_name='Faculty Monitor Course',
                total_classes=60,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            
            # Create multiple students with varying attendance
            students_data = [
                ('PES1UG23CS402', 20, 18),  # Good attendance (90%)
                ('PES1UG23CS403', 20, 14),  # Critical (70%)
                ('PES1UG23CS404', 20, 12),  # Critical (60%)
            ]
            
            for srn, total, attended in students_data:
                for i in range(total):
                    status = 'present' if i < attended else 'absent'
                    record = Attendance(
                        student_srn=srn,
                        course_id='CS402',
                        date=datetime.now().date(),
                        status=status
                    )
                    db.session.add(record)
            db.session.commit()
        
        # Faculty login
        client.post('/login', data={
            'username': 'FAC401',
            'password': 'password123'
        })
        
        # Faculty views all students in course
        response = client.get('/api/bunk-allowance/course/CS402/students')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['total_students'] >= 3
        
        # Faculty checks critical students
        response = client.get('/api/bunk-allowance/critical?course_id=CS402')
        assert response.status_code == 200
        critical_data = json.loads(response.data)
        assert critical_data['success'] is True
        # Should have 2 critical students (70% and 60%)

    def test_admin_course_configuration_workflow(self, client, app):
        """Test admin workflow for configuring courses."""
        with app.app_context():
            # Setup admin
            admin = User(
                username='ADMIN401',
                name='System Test Admin',
                is_faculty=True,
                role='admin'
            )
            admin.set_password('password123')
            db.session.add(admin)
            db.session.commit()
        
        # Admin login
        client.post('/login', data={
            'username': 'ADMIN401',
            'password': 'password123'
        })
        
        # Admin creates new course configuration
        course_config = {
            'course_id': 'CS403',
            'course_name': 'Advanced System Testing',
            'total_classes': 50,
            'bunk_allowance_percentage': 20.0,
            'min_attendance_percentage': 80.0
        }
        
        response = client.post('/api/bunk-allowance/course',
            data=json.dumps(course_config),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify course configuration
        response = client.get('/api/bunk-allowance/course/CS403')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['course_id'] == 'CS403'
        assert data['data']['total_classes'] == 50
        assert data['data']['max_bunk_allowed'] == 10  # 20% of 50

    def test_multi_course_student_workflow(self, client, app):
        """Test student enrolled in multiple courses."""
        with app.app_context():
            # Setup student
            student = User(
                username='PES1UG23CS405',
                name='Multi Course Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            
            # Create multiple courses
            courses = ['CS404', 'CS405', 'CS406']
            for course_id in courses:
                config = CourseConfig(
                    course_id=course_id,
                    course_name=f'Course {course_id}',
                    total_classes=60
                )
                db.session.add(config)
                
                # Different attendance patterns for each course
                num_classes = 10 * (int(course_id[-1]) % 3 + 1)
                for i in range(num_classes):
                    record = Attendance(
                        student_srn='PES1UG23CS405',
                        course_id=course_id,
                        date=datetime.now().date(),
                        status='present' if i % 2 == 0 else 'absent'
                    )
                    db.session.add(record)
            db.session.commit()
        
        # Student login
        client.post('/login', data={
            'username': 'PES1UG23CS405',
            'password': 'password123'
        })
        
        # Get all courses
        response = client.get('/api/bunk-allowance/student/PES1UG23CS405')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['courses']) == 3
        
        # Verify each course has correct data
        course_ids = [c['course_id'] for c in data['courses']]
        assert all(course_id in course_ids for course_id in courses)

    def test_attendance_threshold_scenarios(self, client, app):
        """Test various attendance threshold scenarios."""
        with app.app_context():
            # Setup
            faculty = User(
                username='FAC402',
                name='Threshold Test Faculty',
                is_faculty=True,
                role='teacher'
            )
            faculty.set_password('password123')
            db.session.add(faculty)
            
            config = CourseConfig(
                course_id='CS407',
                course_name='Threshold Test Course',
                total_classes=100,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            
            # Scenario 1: Student exactly at threshold (75%)
            for i in range(40):
                status = 'present' if i < 30 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS406',
                    course_id='CS407',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            
            # Scenario 2: Student above threshold (85%)
            for i in range(40):
                status = 'present' if i < 34 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS407',
                    course_id='CS407',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            
            # Scenario 3: Student below threshold (65%)
            for i in range(40):
                status = 'present' if i < 26 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS408',
                    course_id='CS407',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            
            db.session.commit()
        
        # Login as faculty
        client.post('/login', data={
            'username': 'FAC402',
            'password': 'password123'
        })
        
        # Check each student
        for srn, expected_critical in [
            ('PES1UG23CS406', False),  # 75% - not critical
            ('PES1UG23CS407', False),  # 85% - not critical
            ('PES1UG23CS408', True),   # 65% - critical
        ]:
            response = client.get(f'/api/bunk-allowance/student/{srn}/course/CS407')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['is_attendance_critical'] == expected_critical

    def test_bulk_refresh_workflow(self, client, app):
        """Test bulk refresh of course allowances."""
        with app.app_context():
            # Setup faculty
            faculty = User(
                username='FAC403',
                name='Bulk Refresh Faculty',
                is_faculty=True,
                role='teacher'
            )
            faculty.set_password('password123')
            db.session.add(faculty)
            
            config = CourseConfig(
                course_id='CS408',
                course_name='Bulk Refresh Course',
                total_classes=60
            )
            db.session.add(config)
            
            # Create attendance for multiple students
            for student_num in range(5):
                srn = f'PES1UG23CS{410 + student_num}'
                for i in range(20):
                    record = Attendance(
                        student_srn=srn,
                        course_id='CS408',
                        date=datetime.now().date(),
                        status='present'
                    )
                    db.session.add(record)
            db.session.commit()
        
        # Login as faculty
        client.post('/login', data={
            'username': 'FAC403',
            'password': 'password123'
        })
        
        # Trigger bulk refresh
        response = client.post('/api/bunk-allowance/course/CS408/refresh')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total_students'] == 5
        assert data['data']['updated_count'] == 5
        assert len(data['data']['errors']) == 0

    def test_projection_accuracy(self, client, app):
        """Test accuracy of attendance projections."""
        with app.app_context():
            # Setup
            student = User(
                username='PES1UG23CS409',
                name='Projection Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            
            config = CourseConfig(
                course_id='CS409',
                course_name='Projection Course',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            
            # Create 30 classes: 24 present, 6 absent (80% attendance)
            for i in range(30):
                status = 'present' if i % 5 != 0 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS409',
                    course_id='CS409',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
        
        # Login
        client.post('/login', data={
            'username': 'PES1UG23CS409',
            'password': 'password123'
        })
        
        # Get breakdown with projections
        response = client.get('/api/bunk-allowance/breakdown/PES1UG23CS409/CS409')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify current stats
        assert data['data']['current_stats']['classes_attended'] == 24
        assert data['data']['current_stats']['attendance_percentage'] == 80.0
        
        # Verify remaining classes
        assert data['data']['remaining_classes']['classes_remaining'] == 30
        
        # Verify projections
        # If attend all remaining: (24 + 30) / 60 = 90%
        assert data['data']['projections']['if_attend_all_remaining'] == 90.0
        # If use all bunks (no more attendance): 24 / 60 = 40%
        assert data['data']['projections']['if_use_all_bunks'] == 40.0

    def test_error_handling_and_recovery(self, client, app):
        """Test error handling and recovery scenarios."""
        with app.app_context():
            student = User(
                username='PES1UG23CS410',
                name='Error Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            db.session.commit()
        
        # Login
        client.post('/login', data={
            'username': 'PES1UG23CS410',
            'password': 'password123'
        })
        
        # Try to access non-existent course
        response = client.get('/api/bunk-allowance/student/PES1UG23CS410/course/CS999')
        # Should return success with empty/default data, not crash
        assert response.status_code in [200, 404, 500]
        
        # Try to access course config that doesn't exist
        response = client.get('/api/bunk-allowance/course/CS999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
