import sqlite3
import os
p = os.path.join(os.path.dirname(__file__), '..', 'instance', 'attendance.db')
if not os.path.exists(p):
    # try relative to current working dir
    p = os.path.join('instance', 'attendance.db')

print('Using DB path:', p)
if not os.path.exists(p):
    print('No database found at', p)
    raise SystemExit(1)

conn = sqlite3.connect(p)
cur = conn.cursor()

# Try to find users table name
possible_tables = ['user', 'users', 'User', 'Users']
rows = None
for t in possible_tables:
    try:
        cur.execute(f"SELECT id, username, is_faculty, name FROM {t}")
        rows = cur.fetchall()
        table = t
        break
    except Exception:
        continue

if rows is None:
    # list available tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print('No user table found. Tables in DB:', tables)
else:
    print(f'Found {len(rows)} users in table "{table}":')
    for r in rows:
        print(r)

conn.close()