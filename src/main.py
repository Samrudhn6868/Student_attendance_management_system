"""Small Flask application for student/faculty attendance demo.

Provides a User model, simple login flow and dashboards for faculty and
students. Designed for local development and testing.
"""

import os

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    """A user of the attendance system.

    Attributes:
        id: primary key
        username: SRN for students or faculty ID
        password_hash: hashed password
        is_faculty: whether the user is a faculty member
        name: full name for display
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # SRN or Faculty ID
    password_hash = db.Column(db.String(120), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=False)

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the given plaintext password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return User.query.get(int(user_id))

@app.route('/')
def home():
    """Redirect to the login page."""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render login form and authenticate users on POST."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')  # SRN or Faculty ID
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))

        # fall through and show error message for invalid credentials
        flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Log out the current user and redirect to login."""
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Show faculty or student dashboard depending on role."""
    if current_user.is_faculty:
        return render_template('faculty_dashboard.html')

    return render_template('student_dashboard.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
