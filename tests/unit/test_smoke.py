import os
import sys

# ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import main


def test_home_redirects_to_login():
    app = main.app
    client = app.test_client()
    resp = client.get('/')
    # home redirects to login
    assert resp.status_code in (302, 308) or b'Login' in resp.data
