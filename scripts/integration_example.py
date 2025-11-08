"""Integration example for SAS-88 RBAC.

This file shows how to integrate the RBAC system with the existing main.py
without modifying the original authentication code.

INSTRUCTIONS:
1. Add these imports to main.py
2. Register the attendance blueprint
3. Optionally add the JWT login endpoint for API access
"""

# ============================================================================
# STEP 1: Add these imports to the top of main.py
# ============================================================================
"""
from attendance_routes import attendance_bp
from auth_middleware import generate_jwt_token, create_token_response
"""

# ============================================================================
# STEP 2: Update the User model to include the role field
# ============================================================================
"""
# In the User class definition, add the role column:
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='student')  # ← ADD THIS LINE
    
    # Rest of the model remains the same...
"""

# ============================================================================
# STEP 3: Register the attendance blueprint (add before if __name__ == '__main__')
# ============================================================================
"""
# Register attendance routes with RBAC
app.register_blueprint(attendance_bp)
"""

# ============================================================================
# STEP 4: (Optional) Add JWT login endpoint for API access
# ============================================================================
"""
@app.route('/api/login', methods=['POST'])
def api_login():
    '''API login endpoint that returns JWT token for API authentication.
    
    This is an alternative to the session-based login, useful for:
    - Mobile apps
    - Third-party integrations
    - Automated testing
    - API clients
    
    Expected JSON body:
    {
        "username": "PES1UG23CS001",
        "password": "password123"
    }
    
    Returns JWT token on success.
    '''
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


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    '''Refresh an existing JWT token.
    
    Headers:
        Authorization: Bearer <old_token>
    
    Returns new JWT token with extended expiration.
    '''
    from auth_middleware import get_token_from_header, refresh_jwt_token
    
    old_token = get_token_from_header()
    
    if not old_token:
        return jsonify({
            'error': 'No token provided',
            'message': 'Authorization header with Bearer token is required'
        }), 401
    
    new_token = refresh_jwt_token(old_token)
    
    if not new_token:
        return jsonify({
            'error': 'Invalid token',
            'message': 'Token is invalid or has expired'
        }), 401
    
    return jsonify({
        'access_token': new_token,
        'token_type': 'Bearer',
        'expires_in': 86400
    }), 200
"""

# ============================================================================
# COMPLETE INTEGRATED main.py EXAMPLE
# ============================================================================

COMPLETE_EXAMPLE = """
'''Small Flask application for student/faculty attendance demo.

Provides a User model, simple login flow and dashboards for faculty and
students. Designed for local development and testing.

SAS-88 RBAC features integrated without modifying existing SAS-83/SAS-84 code.
'''

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

# SAS-88: Import attendance routes and JWT utilities
from attendance_routes import attendance_bp
from auth_middleware import create_token_response, get_token_from_header, refresh_jwt_token

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
    '''A user of the attendance system.

    Attributes:
        id: primary key
        username: SRN for students or faculty ID
        password_hash: hashed password
        is_faculty: whether the user is a faculty member
        name: full name for display
        role: user role (student, teacher, admin) - SAS-88
    '''

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_faculty = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='student')  # SAS-88: Added role column

    def set_password(self, password):
        '''Hash and set the user's password.'''
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        '''Return True if the given plaintext password matches the stored hash.'''
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    '''Flask-Login user loader callback.'''
    return User.query.get(int(user_id))

@app.route('/')
def home():
    '''Redirect to the login page.'''
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    '''Render login form and authenticate users on POST.'''
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    '''Log out the current user and redirect to login.'''
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    '''Show faculty or student dashboard depending on role.'''
    if current_user.is_faculty:
        return render_template('faculty_dashboard.html')

    return render_template('student_dashboard.html')

# ============================================================================
# SAS-88: JWT API Endpoints
# ============================================================================

@app.route('/api/login', methods=['POST'])
def api_login():
    '''API login endpoint that returns JWT token for API authentication.'''
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

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    '''Refresh an existing JWT token.'''
    old_token = get_token_from_header()
    
    if not old_token:
        return jsonify({
            'error': 'No token provided',
            'message': 'Authorization header with Bearer token is required'
        }), 401
    
    new_token = refresh_jwt_token(old_token)
    
    if not new_token:
        return jsonify({
            'error': 'Invalid token',
            'message': 'Token is invalid or has expired'
        }), 401
    
    return jsonify({
        'access_token': new_token,
        'token_type': 'Bearer',
        'expires_in': 86400
    }), 200

# ============================================================================
# SAS-88: Register attendance routes blueprint
# ============================================================================
app.register_blueprint(attendance_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
"""

# Save the complete example to a file
if __name__ == '__main__':
    with open('main_integrated_example.py', 'w') as f:
        f.write(COMPLETE_EXAMPLE)
    print("✅ Complete integration example saved to: main_integrated_example.py")
    print("\nTo use:")
    print("1. Review the file to understand the changes")
    print("2. Apply the changes to your src/main.py")
    print("3. Run the database migration: python scripts/add_role_column.py")
    print("4. Start the application: python src/main.py")
