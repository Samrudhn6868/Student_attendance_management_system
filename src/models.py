from flask_sqlalchemy import SQLAlchemy
from datetime import date
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), nullable=False)

    def __init__(self, id, name, is_faculty):
        self.id = id
        self.name = name
        self.is_faculty = is_faculty
        self.role = 'teacher' if is_faculty else 'student'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    is_present = db.Column(db.Boolean, default=True)
