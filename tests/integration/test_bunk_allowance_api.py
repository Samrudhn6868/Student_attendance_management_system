"""Integration tests for SAS-96: Bunk Allowance API.

Tests the bunk allowance REST API endpoints.
"""

import pytest
import json
from datetime import datetime
from src.models import db, User, Attendance
from src.bunk_allowance_models import CourseConfig, StudentBunkAllowance


class TestBunkAllowanceAPI:
    """Integration tests for Bunk Allowance API."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/api/bunk-allowance/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['service'] == 'Bunk Allowance API'

    def test_get_student_bunk_allowance_unauthorized(self, client):
        """Test getting bunk allowance without authentication."""
        response = client.get('/api/bunk-allowance/student/PES1UG23CS001')
        assert response.status_code == 401

    def test_get_student_bunk_allowance_as_student(self, client, app):
        """Test student viewing their own bunk allowance."""
        with app.app_context():
            # Create student user
            student = User(
                username='PES1UG23CS201',
                name='Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            
            # Create course config and attendance
            config = CourseConfig(
                course_id='CS301',
                course_name='Test Course',
                total_classes=60
            )
            db.session.add(config)
            
            for i in range(10):
                record = Attendance(
                    student_srn='PES1UG23CS201',
                    course_id='CS301',
                    date=datetime.now().date(),
                    status='present'
                )
                db.session.add(record)
            db.session.commit()
        
        # Login
        client.post('/login', data={
            'username': 'PES1UG23CS201',
            'password': 'password123'
        })
        
        # Get bunk allowance
        response = client.get('/api/bunk-allowance/student/PES1UG23CS201')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['student_srn'] == 'PES1UG23CS201'
        assert len(data['courses']) > 0

    def test_get_student_bunk_allowance_wrong_student(self, client, app):
        """Test student trying to view another student's data."""
        with app.app_context():
            # Create students
            student1 = User(
                username='PES1UG23CS202',
                name='Student One',
                is_faculty=False,
                role='student'
            )
            student1.set_password('password123')
            db.session.add(student1)
            db.session.commit()
        
        # Login as student1
        client.post('/login', data={
            'username': 'PES1UG23CS202',
            'password': 'password123'
        })
        
        # Try to access another student's data
        response = client.get('/api/bunk-allowance/student/PES1UG23CS999')
        assert response.status_code == 403

    def test_get_student_course_bunk_allowance(self, client, app):
        """Test getting bunk allowance for specific course."""
        with app.app_context():
            # Create student
            student = User(
                username='PES1UG23CS203',
                name='Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            
            # Create course and attendance
            config = CourseConfig(course_id='CS302', course_name='Course 302', total_classes=60)
            db.session.add(config)
            
            for i in range(15):
                status = 'present' if i < 12 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS203',
                    course_id='CS302',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
        
        # Login and request
        client.post('/login', data={
            'username': 'PES1UG23CS203',
            'password': 'password123'
        })
        
        response = client.get('/api/bunk-allowance/student/PES1UG23CS203/course/CS302')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['student_srn'] == 'PES1UG23CS203'
        assert data['data']['course_id'] == 'CS302'
        assert data['data']['classes_attended'] == 12
        assert data['data']['classes_missed'] == 3

    def test_get_remaining_classes_breakdown(self, client, app):
        """Test getting detailed breakdown of remaining classes."""
        with app.app_context():
            # Create student
            student = User(
                username='PES1UG23CS204',
                name='Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            
            # Create course
            config = CourseConfig(
                course_id='CS303',
                course_name='Advanced Course',
                total_classes=60,
                bunk_allowance_percentage=25.0,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            
            # Create attendance (20 classes, 18 attended)
            for i in range(20):
                status = 'present' if i < 18 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS204',
                    course_id='CS303',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
        
        # Login and request
        client.post('/login', data={
            'username': 'PES1UG23CS204',
            'password': 'password123'
        })
        
        response = client.get('/api/bunk-allowance/breakdown/PES1UG23CS204/CS303')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'current_stats' in data['data']
        assert 'course_policy' in data['data']
        assert 'remaining_classes' in data['data']
        assert 'projections' in data['data']

    def test_get_course_students_as_faculty(self, client, app):
        """Test faculty viewing all students in a course."""
        with app.app_context():
            # Create faculty
            faculty = User(
                username='FAC001',
                name='Test Faculty',
                is_faculty=True,
                role='teacher'
            )
            faculty.set_password('password123')
            db.session.add(faculty)
            
            # Create course and students
            config = CourseConfig(course_id='CS304', course_name='Faculty Course', total_classes=60)
            db.session.add(config)
            
            for i in range(3):
                srn = f'PES1UG23CS{300 + i}'
                record = Attendance(
                    student_srn=srn,
                    course_id='CS304',
                    date=datetime.now().date(),
                    status='present'
                )
                db.session.add(record)
            db.session.commit()
        
        # Login as faculty
        client.post('/login', data={
            'username': 'FAC001',
            'password': 'password123'
        })
        
        response = client.get('/api/bunk-allowance/course/CS304/students')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['course_id'] == 'CS304'
        assert data['total_students'] >= 3

    def test_get_course_students_as_student_forbidden(self, client, app):
        """Test student cannot view all students in course."""
        with app.app_context():
            student = User(
                username='PES1UG23CS205',
                name='Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            db.session.commit()
        
        # Login as student
        client.post('/login', data={
            'username': 'PES1UG23CS205',
            'password': 'password123'
        })
        
        response = client.get('/api/bunk-allowance/course/CS304/students')
        assert response.status_code == 403

    def test_get_critical_students_as_faculty(self, client, app):
        """Test faculty getting critical students."""
        with app.app_context():
            # Create faculty
            faculty = User(
                username='FAC002',
                name='Test Faculty',
                is_faculty=True,
                role='teacher'
            )
            faculty.set_password('password123')
            db.session.add(faculty)
            
            # Create course
            config = CourseConfig(
                course_id='CS305',
                course_name='Critical Course',
                total_classes=60,
                min_attendance_percentage=75.0
            )
            db.session.add(config)
            
            # Create student with critical attendance (60%)
            for i in range(10):
                status = 'present' if i < 6 else 'absent'
                record = Attendance(
                    student_srn='PES1UG23CS206',
                    course_id='CS305',
                    date=datetime.now().date(),
                    status=status
                )
                db.session.add(record)
            db.session.commit()
            
            # Update allowance to mark as critical
            from src.bunk_allowance_service import BunkAllowanceService
            BunkAllowanceService.update_student_bunk_allowance('PES1UG23CS206', 'CS305')
        
        # Login as faculty
        client.post('/login', data={
            'username': 'FAC002',
            'password': 'password123'
        })
        
        response = client.get('/api/bunk-allowance/critical?course_id=CS305')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_create_course_config_as_admin(self, client, app):
        """Test admin creating course configuration."""
        with app.app_context():
            # Create admin
            admin = User(
                username='ADMIN001',
                name='Test Admin',
                is_faculty=True,
                role='admin'
            )
            admin.set_password('password123')
            db.session.add(admin)
            db.session.commit()
        
        # Login as admin
        client.post('/login', data={
            'username': 'ADMIN001',
            'password': 'password123'
        })
        
        # Create course config
        response = client.post('/api/bunk-allowance/course',
            data=json.dumps({
                'course_id': 'CS306',
                'course_name': 'New Course',
                'total_classes': 50,
                'bunk_allowance_percentage': 20.0,
                'min_attendance_percentage': 80.0
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['course_id'] == 'CS306'

    def test_create_course_config_as_student_forbidden(self, client, app):
        """Test student cannot create course configuration."""
        with app.app_context():
            student = User(
                username='PES1UG23CS207',
                name='Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            db.session.commit()
        
        # Login as student
        client.post('/login', data={
            'username': 'PES1UG23CS207',
            'password': 'password123'
        })
        
        response = client.post('/api/bunk-allowance/course',
            data=json.dumps({
                'course_id': 'CS307',
                'course_name': 'Forbidden Course',
                'total_classes': 60
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 403

    def test_get_course_config(self, client, app):
        """Test getting course configuration."""
        with app.app_context():
            # Create course config
            config = CourseConfig(
                course_id='CS308',
                course_name='Config Test',
                total_classes=60,
                bunk_allowance_percentage=25.0
            )
            db.session.add(config)
            
            # Create student
            student = User(
                username='PES1UG23CS208',
                name='Test Student',
                is_faculty=False,
                role='student'
            )
            student.set_password('password123')
            db.session.add(student)
            db.session.commit()
        
        # Login
        client.post('/login', data={
            'username': 'PES1UG23CS208',
            'password': 'password123'
        })
        
        response = client.get('/api/bunk-allowance/course/CS308')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['course_id'] == 'CS308'

    def test_refresh_course_allowances_as_faculty(self, client, app):
        """Test faculty refreshing course allowances."""
        with app.app_context():
            # Create faculty
            faculty = User(
                username='FAC003',
                name='Test Faculty',
                is_faculty=True,
                role='teacher'
            )
            faculty.set_password('password123')
            db.session.add(faculty)
            
            # Create course and attendance
            config = CourseConfig(course_id='CS309', course_name='Refresh Test', total_classes=60)
            db.session.add(config)
            
            record = Attendance(
                student_srn='PES1UG23CS209',
                course_id='CS309',
                date=datetime.now().date(),
                status='present'
            )
            db.session.add(record)
            db.session.commit()
        
        # Login as faculty
        client.post('/login', data={
            'username': 'FAC003',
            'password': 'password123'
        })
        
        response = client.post('/api/bunk-allowance/course/CS309/refresh')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
