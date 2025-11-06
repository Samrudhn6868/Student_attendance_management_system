import sqlite3
import os
from werkzeug.security import check_password_hash

def db_path():
    p = os.path.join(os.path.dirname(__file__), '..', 'instance', 'attendance.db')
    if not os.path.exists(p):
        p = os.path.join('instance', 'attendance.db')
    return p

p = db_path()
print('Using DB path:', p)
if not os.path.exists(p):
    print('No database found at', p)
    raise SystemExit(1)

conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("SELECT id, username, password_hash, is_faculty, name FROM user")
users = cur.fetchall()
print(f'Found {len(users)} users')

common = ['password','Password','test','test123','admin','123456','password123','faculty','student','pass','qwerty']

for u in users:
    id, username, pw_hash, is_faculty, name = u
    print('\nUser:', username, '(', name, ')', 'faculty=' , is_faculty)
    print('hash:', pw_hash)
    for g in common:
        try:
            if check_password_hash(pw_hash, g):
                print('  -> matches guess:', g)
                break
        except Exception as e:
            # some hashes (if stored as bytes) may error
            pass
    else:
        print('  -> no common guess matched')

conn.close()