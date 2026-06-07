import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'samples.db')

ROLES = {
    'admin': '管理员',
    'operator': '普通操作员',
    'reviewer': '复核员'
}

STATES = {
    'REGISTERED': '已登记',
    'RECEIVED': '已接收',
    'TESTING': '检测中',
    'REVIEWING': '复核中',
    'REJECTED': '已驳回',
    'ARCHIVED': '已归档',
    'CANCELLED': '已作废'
}

STATE_TRANSITIONS = {
    'REGISTERED': ['RECEIVED', 'CANCELLED'],
    'RECEIVED': ['TESTING', 'REJECTED', 'CANCELLED'],
    'TESTING': ['REVIEWING', 'REJECTED', 'CANCELLED'],
    'REVIEWING': ['ARCHIVED', 'REJECTED', 'CANCELLED'],
    'REJECTED': ['REGISTERED'],
    'ARCHIVED': [],
    'CANCELLED': []
}

PERMISSIONS = {
    'register': ['admin', 'operator', 'reviewer'],
    'receive': ['admin', 'operator', 'reviewer'],
    'test': ['admin', 'operator', 'reviewer'],
    'review': ['admin', 'reviewer'],
    'reject': ['admin', 'reviewer'],
    'archive': ['admin', 'reviewer'],
    'cancel': ['admin'],
    'undo': ['admin']
}


@contextmanager
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_no TEXT UNIQUE NOT NULL,
            batch_no TEXT NOT NULL,
            sample_type TEXT NOT NULL,
            description TEXT,
            current_state TEXT NOT NULL DEFAULT 'REGISTERED',
            registered_by INTEGER NOT NULL,
            registered_at TEXT NOT NULL,
            last_handler INTEGER,
            last_handled_at TEXT,
            FOREIGN KEY (registered_by) REFERENCES users(id),
            FOREIGN KEY (last_handler) REFERENCES users(id)
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER NOT NULL,
            from_state TEXT,
            to_state TEXT NOT NULL,
            operator_id INTEGER NOT NULL,
            reason TEXT,
            event_type TEXT NOT NULL,
            is_correction INTEGER DEFAULT 0,
            corrected_event_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sample_id) REFERENCES samples(id),
            FOREIGN KEY (operator_id) REFERENCES users(id),
            FOREIGN KEY (corrected_event_id) REFERENCES events(id)
        )''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_samples_batch ON samples(batch_no)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_samples_state ON samples(current_state)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_events_sample ON events(sample_id)')


def get_current_user(user_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        return dict(row) if row else None


def check_permission(user_id, action):
    user = get_current_user(user_id)
    if not user:
        return False, '用户不存在'
    if user['role'] not in PERMISSIONS.get(action, []):
        return False, f"用户角色 [{ROLES.get(user['role'], user['role'])}] 无权限执行此操作"
    return True, user


def get_last_valid_event(sample_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''SELECT * FROM events 
            WHERE sample_id = ? AND is_correction = 0
            ORDER BY id DESC LIMIT 1''', (sample_id,))
        row = c.fetchone()
        return dict(row) if row else None


def get_previous_valid_state(sample_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''SELECT from_state FROM events 
            WHERE sample_id = ? AND is_correction = 0
            ORDER BY id DESC LIMIT 1''', (sample_id,))
        row = c.fetchone()
        if row and row['from_state']:
            return row['from_state']
        return 'REGISTERED'
