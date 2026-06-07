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

        c.execute('''CREATE TABLE IF NOT EXISTS import_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id TEXT NOT NULL,
            row_number INTEGER,
            sample_no TEXT,
            batch_no TEXT,
            sample_type TEXT,
            description TEXT,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            operator_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (operator_id) REFERENCES users(id)
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_import_failures_batch ON import_failures(import_batch_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_import_failures_sample ON import_failures(sample_no)')


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


def add_import_failure(import_batch_id, row_number, sample_no, batch_no, sample_type,
                       description, error_type, error_message, operator_id, conn=None):
    from datetime import datetime
    def _do_insert(db_conn):
        c = db_conn.cursor()
        c.execute('''INSERT INTO import_failures 
            (import_batch_id, row_number, sample_no, batch_no, sample_type, description,
             error_type, error_message, operator_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (import_batch_id, row_number, sample_no, batch_no, sample_type, description,
             error_type, error_message, operator_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    if conn is not None:
        _do_insert(conn)
    else:
        with get_db() as db_conn:
            _do_insert(db_conn)


def get_import_failures(import_batch_id=None):
    with get_db() as conn:
        c = conn.cursor()
        query = '''
            SELECT f.*, u.name as operator_name, u.username as operator_username
            FROM import_failures f
            LEFT JOIN users u ON f.operator_id = u.id
        '''
        params = []
        if import_batch_id:
            query += ' WHERE f.import_batch_id = ?'
            params.append(import_batch_id)
        query += ' ORDER BY f.id DESC'
        c.execute(query, params)
        rows = c.fetchall()
        return [dict(row) for row in rows]
