"""Small Flask application for student/faculty attendance demo.

Provides a User model, simple login flow and dashboards for faculty and
students. Designed for local development and testing.
"""

import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
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

# SAS-86: Import password security module for bcrypt support
# Ensure local package imports work whether run as `python src/main.py` or `import src.main`
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from password_security import hash_password, verify_password

# SAS-88: Import RBAC components
from attendance_routes import attendance_bp
from auth_middleware import create_token_response

# SAS-93: Import attendance API
from attendance_api import attendance_api_bp

# SAS-94: Import audit trail API
from audit_api import audit_api

# Load environment variables
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SITE_NAME'] = os.getenv('SITE_NAME', 'PESU Attendance')
basedir = os.path.abspath(os.path.dirname(__file__))
# Ensure instance directory exists for SQLite DB path
instance_dir = os.path.join(basedir, "instance")
os.makedirs(instance_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    f'sqlite:///{os.path.join(instance_dir, "attendance.db")}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.context_processor
def inject_site_name():
    """Expose site_name into all templates for consistent branding and titles."""
    return {"site_name": app.config.get('SITE_NAME', 'PESU Attendance')}

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

    # Account locking fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked = db.Column(db.Boolean, default=False)
    locked_at = db.Column(db.DateTime, nullable=True)

    # Role (RBAC) - keep for compatibility with RBAC feature
    role = db.Column(db.String(20), default='student')  # SAS-88: Added role column

    def set_password(self, password):
        """Hash and set the user's password using bcrypt (SAS-86)."""
        self.password_hash = hash_password(password)

    def check_password(self, password):
        """Return True if the given plaintext password matches the stored hash (SAS-86)."""
        if password is None:
            return False
        return verify_password(password, self.password_hash)

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


class LeaveRequest(db.Model):
    """Leave request submitted by a student.

    Fields:
        id: Primary key
        user_id: Foreign key to User.id
        start_date: First day of leave (inclusive)
        end_date: Last day of leave (inclusive)
        reason: Free-text reason entered by student
        status: 'pending' | 'approved' | 'rejected'
        created_at: Submission timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<LeaveRequest id={self.id} user={self.user_id} {self.start_date}..{self.end_date} status={self.status}>"

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return db.session.get(User, int(user_id))

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


@app.route('/leave/request', methods=['GET', 'POST'])
@login_required
def request_leave():
    """Allow students to request leave via a simple form.

    GET: Render leave request form and list of own requests.
    POST: Validate and create a LeaveRequest, then redirect back with a flash.
    """
    # Only students should request leave (teachers/admins typically approve)
    if current_user.is_faculty:
        flash('Only students can request leave.', 'error')
        return redirect(url_for('dashboard'))

    # Handle submission
    if request.method == 'POST':
        start_str = request.form.get('start_date')
        end_str = request.form.get('end_date')
        reason = (request.form.get('reason') or '').strip()

        # Basic validation
        if not start_str or not end_str or not reason:
            flash('All fields are required.', 'error')
            return redirect(url_for('request_leave'))

        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')
            return redirect(url_for('request_leave'))

        if end_date < start_date:
            flash('End date cannot be before start date.', 'error')
            return redirect(url_for('request_leave'))

        # Persist
        lr = LeaveRequest(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status='pending',
        )
        db.session.add(lr)
        db.session.commit()

        flash('Leave request submitted for approval.', 'success')
        return redirect(url_for('request_leave'))

    # GET: show form + user's recent requests
    my_requests = (
        db.session.query(LeaveRequest)
        .filter(LeaveRequest.user_id == current_user.id)
        .order_by(LeaveRequest.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template('request_leave.html', my_requests=my_requests)

# ============================================================================
# SAS-88: RBAC Test Page
# ============================================================================

@app.route('/test-rbac')
@login_required
def test_rbac():
    """Simple HTML page to test RBAC functionality."""
    user_role = getattr(
        current_user,
        'role',
        'student' if not current_user.is_faculty else 'teacher'
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SAS-88 RBAC Test Page</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }}
            .user-info {{
                background-color: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .role-badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                margin-left: 10px;
            }}
            .role-student {{ background-color: #90caf9; color: white; }}
            .role-teacher {{ background-color: #81c784; color: white; }}
            .role-admin {{ background-color: #e57373; color: white; }}
            .test-links {{
                margin: 30px 0;
            }}
            .test-link {{
                display: block;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                text-decoration: none;
                color: white;
                font-weight: bold;
                text-align: center;
                transition: transform 0.2s;
            }}
            .test-link:hover {{
                transform: scale(1.02);
            }}
            .link-allowed {{ background-color: #4caf50; }}
            .link-denied {{ background-color: #f44336; }}
            .link-maybe {{ background-color: #ff9800; }}
            .info {{
                background-color: #fff3cd;
                padding: 15px;
                border-left: 4px solid #ffc107;
                margin: 20px 0;
            }}
            .logout {{
                display: inline-block;
                padding: 10px 20px;
                background-color: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            }}
            .logout:hover {{
                background-color: #5a6268;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 SAS-88 RBAC Test Page</h1>

            <div class="user-info">
                <strong>👤 Logged in as:</strong> {current_user.name} ({current_user.username})
                <span class="role-badge role-{user_role}">{user_role.upper()}</span>
            </div>

            <div class="info">
                <strong>ℹ️ Instructions:</strong> Click the links below to test role-based access control.
                You should see JSON responses or 403 Forbidden errors based on your role.
            </div>

            <div class="test-links">
                <h3>📋 Test Attendance Endpoints:</h3>

                <a href="/attendance/view" class="test-link link-allowed">
                    ✅ View Attendance (All roles can access)
                </a>

                <a href="/attendance/mark" class="test-link {'link-maybe' if user_role in ['teacher', 'admin'] else 'link-denied'}">
                    {'✅' if user_role in ['teacher', 'admin'] else '❌'} Mark Attendance
                    (Teacher & Admin only)
                </a>

                <a href="/attendance/override" class="test-link {'link-allowed' if user_role == 'admin' else 'link-denied'}">
                    {'✅' if user_role == 'admin' else '❌'} Override Attendance
                    (Admin only)
                </a>
            </div>

            <div class="info">
                <strong>Expected Results:</strong><br>
                • <strong>Student</strong>: Can only access "View Attendance"<br>
                • <strong>Teacher</strong>: Can access "View" and "Mark"<br>
                • <strong>Admin</strong>: Can access all three endpoints<br>
                • Unauthorized access returns 403 Forbidden error
            </div>

            <a href="/logout" class="logout">← Logout</a>
            <a href="/dashboard" class="logout" style="background-color: #007bff;">Dashboard</a>
        </div>
    </body>
    </html>
    """
    return html

# ============================================================================
# SAS-88: JWT API Endpoints
# ============================================================================

@app.route('/api/login', methods=['POST'])
def api_login():
    """API login endpoint that returns JWT token for API authentication."""
    data = request.get_json()

    if not data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Request body must be JSON'
        }), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({
            'error': 'Missing credentials',
            'message': 'Both username and password are required'
        }), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return jsonify(create_token_response(user)), 200

    return jsonify({
        'error': 'Invalid credentials',
        'message': 'Username or password is incorrect'
    }), 401

# SAS-88: Register attendance routes with RBAC
app.register_blueprint(attendance_bp)

# SAS-93: Register attendance API routes
app.register_blueprint(attendance_api_bp)

# SAS-94: Register audit trail API (admin-only)
app.register_blueprint(audit_api)

# Create DB tables on import to support integration tests and local dev.
# In production deployments, migrations should be used instead.
with app.app_context():
    db.create_all()

    # Development convenience: auto-seed demo users if DB is empty.
    # This runs only when not explicitly disabled and when there are no users yet.
    # Credentials (for local dev only):
    #  - student1 / student123
    #  - teacher1 / teacher123
    #  - admin1   / admin123
    try:
        if not os.getenv('DISABLE_DEMO_SEED'):
            # Only seed in non-production environments
            if os.getenv('FLASK_ENV', 'development') != 'production':
                reset_pw = bool(os.getenv('RESET_DEMO_PASSWORDS'))

                def ensure_user(username, name, is_faculty, role, password):
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        user = User(
                            username=username,
                            name=name,
                            is_faculty=is_faculty,
                            role=role,
                        )
                        user.set_password(password)
                        db.session.add(user)
                        return True
                    # Optionally refresh default passwords
                    if reset_pw:
                        user.set_password(password)
                    # Keep role/name in sync for demo users
                    user.name = name
                    user.is_faculty = is_faculty
                    user.role = role
                    return False

                created_any = False
                created_any |= ensure_user('student1', 'John Doe', False, 'student', 'student123')
                created_any |= ensure_user('teacher1', 'Prof. Smith', True, 'teacher', 'teacher123')
                created_any |= ensure_user('admin1', 'Admin User', True, 'admin', 'admin123')
                if created_any or reset_pw:
                    db.session.commit()
    except Exception as seed_err:  # pylint: disable=broad-except
        # Non-fatal in dev; avoid breaking app start due to seeding issues.
        # You can disable this block by setting DISABLE_DEMO_SEED=1 in the environment.
        print(f"[seed] Skipped demo user seeding due to: {seed_err}")

if __name__ == '__main__':
    app.run(debug=True)
