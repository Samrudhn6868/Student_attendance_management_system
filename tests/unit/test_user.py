import os
import sys

# ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

import main


def test_user_password_hash_and_check():
    User = main.User
    u = User(username='u1', name='U One')
    u.set_password('s3cret')
    assert u.check_password('s3cret') is True
    assert u.check_password('wrong') is False
