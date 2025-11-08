from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    is_present = db.Column(db.Boolean, default=True)

# Add your User model here if not already present
