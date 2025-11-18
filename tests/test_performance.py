"""
Performance and benchmark tests for the Student Attendance System.

These tests measure the performance of critical functions and endpoints.
Run with: pytest tests/test_performance.py --benchmark-only
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from password_security import hash_password, verify_password
from encryption_utils import encrypt_data, decrypt_data, hash_value


class TestPasswordPerformance:
    """Performance benchmarks for password operations."""
    
    def test_password_hashing_performance(self, benchmark):
        """Benchmark password hashing with bcrypt."""
        password = "TestPassword123!"
        result = benchmark(hash_password, password)
        assert result is not None
        assert len(result) > 0
    
    def test_password_verification_performance(self, benchmark):
        """Benchmark password verification with bcrypt."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        result = benchmark(verify_password, password, hashed)
        assert result is True


class TestEncryptionPerformance:
    """Performance benchmarks for encryption operations."""
    
    @pytest.fixture(autouse=True)
    def setup_encryption(self, monkeypatch):
        """Set up encryption key for tests."""
        import base64
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        monkeypatch.setenv("ENCRYPTION_KEY", base64.b64encode(key).decode())
    
    def test_data_encryption_performance(self, benchmark):
        """Benchmark data encryption."""
        data = "PES1UG21CS001"
        result = benchmark(encrypt_data, data)
        assert result is not None
    
    def test_data_decryption_performance(self, benchmark):
        """Benchmark data decryption."""
        data = "PES1UG21CS001"
        encrypted = encrypt_data(data)
        result = benchmark(decrypt_data, encrypted)
        assert result == data
    
    def test_data_hashing_performance(self, benchmark):
        """Benchmark SHA-256 hashing."""
        data = "PES1UG21CS001"
        result = benchmark(hash_value, data)
        assert result is not None
        assert len(result) == 64  # SHA-256 hex digest


class TestDatabasePerformance:
    """Performance benchmarks for database operations."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db = SQLAlchemy(app)
        
        with app.app_context():
            from models import User
            db.create_all()
            
            # Create test user
            user = User(
                username='test_user',
                name='Test User',
                role='student',
                is_faculty=False
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()
        
        return app
    
    def test_user_query_performance(self, benchmark, app):
        """Benchmark user query from database."""
        from models import User
        
        def query_user():
            with app.app_context():
                return User.query.filter_by(username='test_user').first()
        
        result = benchmark(query_user)
        assert result is not None
    
    def test_user_password_check_performance(self, benchmark, app):
        """Benchmark user authentication."""
        from models import User
        
        def check_password():
            with app.app_context():
                user = User.query.filter_by(username='test_user').first()
                return user.check_password('TestPass123!')
        
        result = benchmark(check_password)
        assert result is True


class TestAPIPerformance:
    """Performance benchmarks for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app, db
        
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Create test user
            from models import User
            user = User(
                username='test_user',
                name='Test User',
                role='student',
                is_faculty=False
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()
        
        return app.test_client()
    
    @pytest.mark.skip(reason="Requires app context setup")
    def test_login_endpoint_performance(self, benchmark, client):
        """Benchmark login endpoint."""
        def login():
            return client.post('/login', data={
                'username': 'test_user',
                'password': 'TestPass123!'
            }, follow_redirects=False)
        
        response = benchmark(login)
        # Don't assert on response since we're measuring performance


class TestBulkOperations:
    """Performance benchmarks for bulk operations."""
    
    def test_bulk_password_hashing(self, benchmark):
        """Benchmark hashing multiple passwords."""
        passwords = [f"Password{i}!" for i in range(10)]
        
        def hash_all():
            return [hash_password(p) for p in passwords]
        
        results = benchmark(hash_all)
        assert len(results) == 10
    
    def test_bulk_encryption(self, benchmark, monkeypatch):
        """Benchmark encrypting multiple values."""
        import base64
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        monkeypatch.setenv("ENCRYPTION_KEY", base64.b64encode(key).decode())
        
        data_items = [f"PES1UG21CS{i:03d}" for i in range(100)]
        
        def encrypt_all():
            return [encrypt_data(item) for item in data_items]
        
        results = benchmark(encrypt_all)
        assert len(results) == 100


@pytest.mark.performance
class TestLoadSimulation:
    """Simulated load tests."""
    
    def test_concurrent_password_verifications(self):
        """Simulate concurrent password verification requests."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Simulate 10 concurrent verifications
        results = []
        for _ in range(10):
            result = verify_password(password, hashed)
            results.append(result)
        
        assert all(results)
        assert len(results) == 10
    
    def test_concurrent_encryptions(self, monkeypatch):
        """Simulate concurrent encryption operations."""
        import base64
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        monkeypatch.setenv("ENCRYPTION_KEY", base64.b64encode(key).decode())
        
        # Simulate 20 concurrent encryptions
        results = []
        for i in range(20):
            encrypted = encrypt_data(f"Student{i}")
            results.append(encrypted)
        
        assert len(results) == 20
        assert all(r is not None for r in results)
