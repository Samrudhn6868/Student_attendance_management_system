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
from werkzeug.security import generate_password_hash, check_password_hash

# SAS-88: Import RBAC components
from attendance_routes import attendance_bp
from auth_middleware import create_token_response

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
    role = db.Column(db.String(20), default='student')  # SAS-88: Added role column

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

# ============================================================================
# SAS-88: RBAC Test Page
# ============================================================================

@app.route('/test-rbac')
@login_required
def test_rbac():
    """Simple HTML page to test RBAC functionality."""
    user_role = getattr(current_user, 'role', 'student' if not current_user.is_faculty else 'teacher')
    
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
