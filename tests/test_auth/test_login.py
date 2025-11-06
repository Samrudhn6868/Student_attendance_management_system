import os
import sys

# ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import main


def setup_test_app(app):
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })


def test_login_page_renders():
    app = main.app
    setup_test_app(app)
    client = app.test_client()
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b'SRN/Faculty ID' in resp.data or b'Password' in resp.data


def test_login_with_valid_credentials_shows_dashboard():
    app = main.app
    db = main.db
    User = main.User
    setup_test_app(app)

    with app.app_context():
        db.create_all()
        u = User(username='student1', name='Student One', is_faculty=False)
        u.set_password('testpass')
        db.session.add(u)
        db.session.commit()

        client = app.test_client()
        resp = client.post('/login', data={'username': 'student1', 'password': 'testpass'}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Student Dashboard' in resp.data
