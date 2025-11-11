from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from models import User, Attendance, db  # Adjust import as needed
from rbac import require_role

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance/mark', methods=['GET', 'POST'])
@login_required
@require_role('teacher', 'admin')
def mark_attendance():
    students = User.query.filter_by(is_faculty=False).all()
    today = date.today()

    if request.method == 'POST':
        absentees = request.form.getlist('absentees')  # list of student IDs
        for student in students:
            is_present = str(student.id) not in absentees
            attendance = Attendance(
                student_id=student.id,
                date=today,
                is_present=is_present
            )
            db.session.add(attendance)
        db.session.commit()
        flash('Attendance marked successfully!', 'success')
        return redirect(url_for('attendance.mark_attendance'))

    return render_template('mark_attendance.html', students=students, today=today)
