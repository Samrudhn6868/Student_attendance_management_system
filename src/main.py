"""Small Flask application for student/faculty attendance demo.

Provides a User model, simple login flow and dashboards for faculty and
students. Designed for local development and testing.
"""

import os
from datetime import datetime, timedelta

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
        failed_login_attempts: count of consecutive failed login attempts
        account_locked: whether the account is currently locked
        locked_at: timestamp when account was locked
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # SRN or Faculty ID
    password_hash = db.Column(db.String(120), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked = db.Column(db.Boolean, default=False)
    locked_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the given plaintext password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        """Check if account is locked.
        
        Automatically unlocks if locked for more than 30 minutes.
        """
        if not self.account_locked:
            return False
        
        # Auto-unlock after 30 minutes
        if self.locked_at:
            unlock_time = self.locked_at + timedelta(minutes=30)
            if datetime.utcnow() >= unlock_time:
                self.unlock_account()
                return False
        
        return True

    def lock_account(self):
        """Lock the account after too many failed attempts."""
        self.account_locked = True
        self.locked_at = datetime.utcnow()
        db.session.commit()

    def unlock_account(self):
        """Unlock the account and reset failed attempts."""
        self.account_locked = False
        self.locked_at = None
        self.failed_login_attempts = 0
        db.session.commit()

    def record_failed_login(self):
        """Increment failed login attempts and lock if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 3:
            self.lock_account()
        else:
            db.session.commit()

    def reset_failed_attempts(self):
        """Reset failed login attempts counter on successful login."""
        self.failed_login_attempts = 0
        db.session.commit()

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

        if user:
            # Check if account is locked
            if user.is_locked():
                minutes_locked = 30
                if user.locked_at:
                    time_remaining = timedelta(minutes=minutes_locked) - (
                        datetime.utcnow() - user.locked_at
                    )
                    minutes_left = int(time_remaining.total_seconds() / 60)
                    flash(
                        f'Account is locked due to multiple failed login attempts. '
                        f'Please try again in {minutes_left} minutes.',
                        'error'
                    )
                else:
                    flash('Account is locked. Please contact administrator.', 'error')
                return render_template('login.html')

            # Verify password
            if user.check_password(password):
                # Successful login
                user.reset_failed_attempts()
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard'))

            # Failed login attempt
            user.record_failed_login()
            remaining_attempts = 3 - user.failed_login_attempts
            
            if user.account_locked:
                flash(
                    'Account locked due to multiple failed login attempts. '
                    'Please try again after 30 minutes.',
                    'error'
                )
            elif remaining_attempts > 0:
                flash(
                    f'Invalid password. {remaining_attempts} attempts remaining before account lock.',
                    'error'
                )
            else:
                flash('Invalid username or password', 'error')
        else:
            # User not found
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
