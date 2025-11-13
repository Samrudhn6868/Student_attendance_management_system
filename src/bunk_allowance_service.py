"""SAS-96: Bunk Allowance Service Layer.

This module provides business logic for calculating and managing student
bunk allowances and remaining classes. It integrates with the existing
attendance system.
"""

from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from models import db, Attendance
from bunk_allowance_models import CourseConfig, StudentBunkAllowance


class BunkAllowanceService:
    """Service class for bunk allowance calculations and management."""

    @staticmethod
    def get_or_create_course_config(course_id, course_name=None, 
                                    total_classes=60, 
                                    bunk_allowance_percentage=25.0,
                                    min_attendance_percentage=75.0):
        """Get existing course config or create a new one.
        
        Args:
            course_id (str): Course identifier
            course_name (str): Course name (optional)
            total_classes (int): Total classes in course
            bunk_allowance_percentage (float): Bunk allowance percentage
            min_attendance_percentage (float): Minimum attendance percentage
            
        Returns:
            CourseConfig: Course configuration object
        """
        config = db.session.execute(
            db.select(CourseConfig).filter_by(course_id=course_id)
        ).scalar_one_or_none()
        
        if not config:
            config = CourseConfig(
                course_id=course_id,
                course_name=course_name or course_id,
                total_classes=total_classes,
                bunk_allowance_percentage=bunk_allowance_percentage,
                min_attendance_percentage=min_attendance_percentage
            )
            db.session.add(config)
            db.session.commit()
        
        return config

    @staticmethod
    def calculate_student_attendance_stats(student_srn, course_id):
        """Calculate attendance statistics from attendance records.
        
        Args:
            student_srn (str): Student SRN
            course_id (str): Course ID
            
        Returns:
            dict: Dictionary with attendance statistics
        """
        # Query all attendance records for this student-course combination
        records = db.session.execute(
            db.select(Attendance).filter(
                and_(
                    Attendance.student_srn == student_srn,
                    Attendance.course_id == course_id
                )
            )
        ).scalars().all()
        
        total_classes = len(records)
        classes_attended = sum(1 for r in records if r.status == 'present')
        classes_missed = sum(1 for r in records if r.status == 'absent')
        
        attendance_percentage = 100.0
        if total_classes > 0:
            attendance_percentage = (classes_attended / total_classes) * 100.0
        
        return {
            'total_classes_held': total_classes,
            'classes_attended': classes_attended,
            'classes_missed': classes_missed,
            'attendance_percentage': attendance_percentage
        }

    @staticmethod
    def update_student_bunk_allowance(student_srn, course_id):
        """Update or create student bunk allowance record.
        
        Args:
            student_srn (str): Student SRN
            course_id (str): Course ID
            
        Returns:
            StudentBunkAllowance: Updated bunk allowance record
        """
        # Get course config
        course_config = BunkAllowanceService.get_or_create_course_config(course_id)
        
        # Calculate stats from attendance records
        stats = BunkAllowanceService.calculate_student_attendance_stats(
            student_srn, course_id
        )
        
        # Get or create student bunk allowance record
        allowance = db.session.execute(
            db.select(StudentBunkAllowance).filter_by(
                student_srn=student_srn,
                course_id=course_id
            )
        ).scalar_one_or_none()
        
        if not allowance:
            allowance = StudentBunkAllowance(
                student_srn=student_srn,
                course_id=course_id
            )
            db.session.add(allowance)
        
        # Update statistics
        allowance.total_classes_held = stats['total_classes_held']
        allowance.classes_attended = stats['classes_attended']
        allowance.classes_missed = stats['classes_missed']
        allowance.current_attendance_percentage = stats['attendance_percentage']
        
        # Update bunk allowance and critical status
        allowance.update_from_attendance_records(course_config)
        
        db.session.commit()
        
        return allowance

    @staticmethod
    def get_student_bunk_allowance(student_srn, course_id=None):
        """Get bunk allowance information for a student.
        
        Args:
            student_srn (str): Student SRN
            course_id (str): Course ID (optional, None for all courses)
            
        Returns:
            list or dict: List of allowances or single allowance dict
        """
        if course_id:
            # Update and return single course
            allowance = BunkAllowanceService.update_student_bunk_allowance(
                student_srn, course_id
            )
            return allowance.to_dict()
        
        # Get all courses for student
        courses = db.session.query(Attendance.course_id).filter(
            Attendance.student_srn == student_srn
        ).distinct().all()
        
        allowances = []
        for (cid,) in courses:
            allowance = BunkAllowanceService.update_student_bunk_allowance(
                student_srn, cid
            )
            allowances.append(allowance.to_dict())
        
        return allowances

    @staticmethod
    def get_remaining_classes_breakdown(student_srn, course_id):
        """Get detailed breakdown of remaining classes and projections.
        
        Args:
            student_srn (str): Student SRN
            course_id (str): Course ID
            
        Returns:
            dict: Detailed breakdown of remaining classes
        """
        allowance = BunkAllowanceService.update_student_bunk_allowance(
            student_srn, course_id
        )
        course_config = db.session.execute(
            db.select(CourseConfig).filter_by(course_id=course_id)
        ).scalar_one_or_none()
        
        if not course_config:
            course_config = BunkAllowanceService.get_or_create_course_config(course_id)
        
        # Calculate projections
        total_classes = course_config.total_classes
        classes_remaining = total_classes - allowance.total_classes_held
        min_classes_required = course_config.get_min_classes_required()
        classes_needed_to_maintain = max(0, min_classes_required - allowance.classes_attended)
        
        # Safe bunk calculation
        safe_bunks_remaining = allowance.remaining_bunk_allowance
        if allowance.current_attendance_percentage < course_config.min_attendance_percentage:
            # Already below threshold - need to attend all remaining to recover
            safe_bunks_remaining = 0
        
        return {
            'student_srn': student_srn,
            'course_id': course_id,
            'course_name': course_config.course_name,
            'current_stats': {
                'total_classes_held': allowance.total_classes_held,
                'classes_attended': allowance.classes_attended,
                'classes_missed': allowance.classes_missed,
                'attendance_percentage': round(allowance.current_attendance_percentage, 2)
            },
            'course_policy': {
                'total_classes': total_classes,
                'min_attendance_percentage': course_config.min_attendance_percentage,
                'bunk_allowance_percentage': course_config.bunk_allowance_percentage,
                'max_bunk_allowed': course_config.get_max_bunk_allowed(),
                'min_classes_required': min_classes_required
            },
            'remaining_classes': {
                'classes_remaining': classes_remaining,
                'safe_bunks_remaining': safe_bunks_remaining,
                'classes_needed_to_maintain': classes_needed_to_maintain,
                'is_attendance_critical': allowance.is_attendance_critical
            },
            'projections': {
                'if_attend_all_remaining': round(
                    ((allowance.classes_attended + classes_remaining) / total_classes) * 100, 2
                ) if total_classes > 0 else 100.0,
                'if_use_all_bunks': round(
                    ((allowance.classes_attended) / total_classes) * 100, 2
                ) if total_classes > 0 else 100.0
            },
            'last_updated': allowance.last_updated.isoformat() if allowance.last_updated else None
        }

    @staticmethod
    def get_all_students_bunk_status(course_id=None):
        """Get bunk allowance status for all students.
        
        Args:
            course_id (str): Filter by course ID (optional)
            
        Returns:
            list: List of student bunk allowance records
        """
        query = StudentBunkAllowance.query
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        allowances = query.all()
        
        # Update all records
        result = []
        for allowance in allowances:
            try:
                updated = BunkAllowanceService.update_student_bunk_allowance(
                    allowance.student_srn,
                    allowance.course_id
                )
                result.append(updated.to_dict())
            except SQLAlchemyError:
                # If update fails, return stale data
                result.append(allowance.to_dict())
        
        return result

    @staticmethod
    def get_critical_students(course_id=None):
        """Get list of students with critical attendance.
        
        Args:
            course_id (str): Filter by course ID (optional)
            
        Returns:
            list: List of students with critical attendance
        """
        stmt = db.select(StudentBunkAllowance).filter_by(is_attendance_critical=True)
        
        if course_id:
            stmt = stmt.filter_by(course_id=course_id)
        
        critical_students = db.session.execute(stmt).scalars().all()
        
        return [student.to_dict() for student in critical_students]

    @staticmethod
    def bulk_update_course_allowances(course_id):
        """Update bunk allowance for all students in a course.
        
        Args:
            course_id (str): Course ID
            
        Returns:
            dict: Summary of update operation
        """
        # Get all unique students in this course
        students = db.session.query(Attendance.student_srn).filter(
            Attendance.course_id == course_id
        ).distinct().all()
        
        updated_count = 0
        errors = []
        
        for (student_srn,) in students:
            try:
                BunkAllowanceService.update_student_bunk_allowance(
                    student_srn, course_id
                )
                updated_count += 1
            except Exception as e:
                errors.append({
                    'student_srn': student_srn,
                    'error': str(e)
                })
        
        return {
            'course_id': course_id,
            'total_students': len(students),
            'updated_count': updated_count,
            'errors': errors
        }
