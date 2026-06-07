from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import io
import csv
from database import (
    get_db, init_db, ROLES, STATES, STATE_TRANSITIONS,
    check_permission, get_current_user, get_previous_valid_state
)

app = Flask(__name__)
CORS(app)


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_sample_by_no(sample_no):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM samples WHERE sample_no = ?', (sample_no,))
        row = c.fetchone()
        return dict(row) if row else None


def get_sample(sample_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM samples WHERE id = ?', (sample_id,))
        row = c.fetchone()
        return dict(row) if row else None


def add_event(sample_id, from_state, to_state, operator_id, reason, event_type,
              is_correction=0, corrected_event_id=None, conn=None):
    def _do_event(db_conn):
        c = db_conn.cursor()
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type,
             is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (sample_id, from_state, to_state, operator_id, reason, event_type,
             is_correction, corrected_event_id, now()))
        event_id = c.lastrowid

        c.execute('''UPDATE samples 
            SET current_state = ?, last_handler = ?, last_handled_at = ?
            WHERE id = ?''',
            (to_state, operator_id, now(), sample_id))

        return event_id

    if conn is not None:
        return _do_event(conn)
    with get_db() as db_conn:
        return _do_event(db_conn)


def sample_to_dict(row):
    d = dict(row)
    d['current_state_name'] = STATES.get(d['current_state'], d['current_state'])
    return d


def event_to_dict(row):
    d = dict(row)
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT name, username, role FROM users WHERE id = ?', (row['operator_id'],))
        user = c.fetchone()
        if user:
            d['operator_name'] = user['name']
            d['operator_username'] = user['username']
            d['operator_role'] = ROLES.get(user['role'], user['role'])
    if d.get('from_state'):
        d['from_state_name'] = STATES.get(d['from_state'], d['from_state'])
    d['to_state_name'] = STATES.get(d['to_state'], d['to_state'])
    return d


@app.route('/api/users', methods=['GET'])
def list_users():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users ORDER BY id')
        rows = c.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['role_name'] = ROLES.get(d['role'], d['role'])
            result.append(d)
        return jsonify(result)


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_api(user_id):
    user = get_current_user(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    user['role_name'] = ROLES.get(user['role'], user['role'])
    return jsonify(user)


@app.route('/api/samples', methods=['GET'])
def list_samples():
    batch_no = request.args.get('batch_no')
    state = request.args.get('state')
    pending = request.args.get('pending')

    query = '''
        SELECT s.*, 
               u1.name as registered_by_name,
               u2.name as last_handler_name
        FROM samples s
        LEFT JOIN users u1 ON s.registered_by = u1.id
        LEFT JOIN users u2 ON s.last_handler = u2.id
        WHERE 1=1
    '''
    params = []

    if batch_no:
        query += ' AND s.batch_no = ?'
        params.append(batch_no)
    if state:
        query += ' AND s.current_state = ?'
        params.append(state)
    if pending == '1':
        query += " AND s.current_state NOT IN ('ARCHIVED', 'CANCELLED')"

    query += ' ORDER BY s.id DESC'

    with get_db() as conn:
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['current_state_name'] = STATES.get(d['current_state'], d['current_state'])
            result.append(d)
        return jsonify(result)


@app.route('/api/samples/stats', methods=['GET'])
def get_stats():
    with get_db() as conn:
        c = conn.cursor()
        stats = {}

        c.execute("SELECT COUNT(*) as cnt FROM samples WHERE current_state NOT IN ('ARCHIVED', 'CANCELLED')")
        stats['pending_count'] = c.fetchone()['cnt']

        c.execute('''SELECT current_state, COUNT(*) as cnt 
            FROM samples 
            WHERE current_state NOT IN ('ARCHIVED', 'CANCELLED')
            GROUP BY current_state''')
        rows = c.fetchall()
        stats['by_state'] = {}
        for row in rows:
            stats['by_state'][STATES.get(row['current_state'], row['current_state'])] = row['cnt']

        c.execute('''SELECT batch_no, COUNT(*) as cnt 
            FROM samples 
            WHERE current_state NOT IN ('ARCHIVED', 'CANCELLED')
            GROUP BY batch_no''')
        rows = c.fetchall()
        stats['by_batch'] = {}
        for row in rows:
            stats['by_batch'][row['batch_no']] = row['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM samples WHERE current_state = 'REJECTED'")
        stats['rejected_count'] = c.fetchone()['cnt']

        return jsonify(stats)


@app.route('/api/samples/<int:sample_id>', methods=['GET'])
def get_sample_api(sample_id):
    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT name FROM users WHERE id = ?', (sample['registered_by'],))
        reg_user = c.fetchone()
        sample['registered_by_name'] = reg_user['name'] if reg_user else None

        if sample.get('last_handler'):
            c.execute('SELECT name FROM users WHERE id = ?', (sample['last_handler'],))
            last_user = c.fetchone()
            sample['last_handler_name'] = last_user['name'] if last_user else None

        c.execute('SELECT * FROM events WHERE sample_id = ? ORDER BY id', (sample_id,))
        events = c.fetchall()
        sample['events'] = [event_to_dict(e) for e in events]

    sample['current_state_name'] = STATES.get(sample['current_state'], sample['current_state'])

    return jsonify(sample)


@app.route('/api/samples/<sample_no>/exists', methods=['GET'])
def check_sample_exists(sample_no):
    sample = get_sample_by_no(sample_no)
    return jsonify({'exists': sample is not None})


@app.route('/api/samples', methods=['POST'])
def register_sample():
    data = request.get_json()
    sample_no = data.get('sample_no', '').strip()
    batch_no = data.get('batch_no', '').strip()
    sample_type = data.get('sample_type', '').strip()
    description = data.get('description', '').strip()
    operator_id = data.get('operator_id')

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'register')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    if not sample_no or not batch_no or not sample_type:
        return jsonify({'error': '样本编号、批次号和样本类型不能为空'}), 400

    existing = get_sample_by_no(sample_no)
    if existing:
        return jsonify({'error': f'样本号 [{sample_no}] 已存在，不能重复登记'}), 400

    with get_db() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, registered_by, registered_at)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (sample_no, batch_no, sample_type, description, operator_id, now()))
        sample_id = c.lastrowid

        add_event(sample_id, None, 'REGISTERED', operator_id, '样本登记', 'REGISTER', conn=conn)

    return jsonify({
        'success': True,
        'sample_id': sample_id,
        'message': f'样本 {sample_no} 登记成功'
    })


@app.route('/api/batches/receive', methods=['POST'])
def receive_batch():
    data = request.get_json()
    batch_no = data.get('batch_no', '').strip()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '批次接收').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'receive')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    if not batch_no:
        return jsonify({'error': '批次号不能为空'}), 400

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM samples WHERE batch_no = ? AND current_state = 'REGISTERED'",
                  (batch_no,))
        samples = c.fetchall()

        if not samples:
            return jsonify({'error': f'批次 [{batch_no}] 没有待接收的样本'}), 400

        count = 0
        for s in samples:
            add_event(s['id'], 'REGISTERED', 'RECEIVED', operator_id, reason, 'RECEIVE', conn=conn)
            count += 1

    return jsonify({
        'success': True,
        'count': count,
        'message': f'批次 {batch_no} 接收成功，共 {count} 个样本'
    })


@app.route('/api/samples/<int:sample_id>/receive', methods=['POST'])
def receive_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '样本接收').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'receive')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] != 'REGISTERED':
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，只有已登记的样本才能接收'
        }), 400

    add_event(sample_id, 'REGISTERED', 'RECEIVED', operator_id, reason, 'RECEIVE')

    return jsonify({
        'success': True,
        'message': f'样本接收成功'
    })


@app.route('/api/samples/<int:sample_id>/test', methods=['POST'])
def test_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '开始检测').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'test')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] != 'RECEIVED':
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，只有已接收的样本才能开始检测'
        }), 400

    add_event(sample_id, 'RECEIVED', 'TESTING', operator_id, reason, 'TEST')

    return jsonify({
        'success': True,
        'message': f'样本进入检测状态'
    })


@app.route('/api/samples/<int:sample_id>/review', methods=['POST'])
def review_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '检测完成，提交复核').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'review')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] != 'TESTING':
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，只有检测中的样本才能提交复核'
        }), 400

    add_event(sample_id, 'TESTING', 'REVIEWING', operator_id, reason, 'REVIEW')

    return jsonify({
        'success': True,
        'message': f'样本进入复核状态'
    })


@app.route('/api/samples/<int:sample_id>/reject', methods=['POST'])
def reject_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'reject')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    if not reason:
        return jsonify({'error': '驳回原因不能为空'}), 400

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] not in ['RECEIVED', 'TESTING', 'REVIEWING']:
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，不能驳回'
        }), 400

    from_state = sample['current_state']
    add_event(sample_id, from_state, 'REJECTED', operator_id, reason, 'REJECT')

    return jsonify({
        'success': True,
        'message': f'样本已驳回，原因：{reason}'
    })


@app.route('/api/samples/<int:sample_id>/archive', methods=['POST'])
def archive_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '复核通过，归档').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'archive')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] != 'REVIEWING':
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，只有复核中的样本才能归档。禁止跳级归档！'
        }), 400

    add_event(sample_id, 'REVIEWING', 'ARCHIVED', operator_id, reason, 'ARCHIVE')

    return jsonify({
        'success': True,
        'message': f'样本已归档'
    })


@app.route('/api/samples/<int:sample_id>/cancel', methods=['POST'])
def cancel_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'cancel')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    if not reason:
        return jsonify({'error': '作废原因不能为空'}), 400

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] in ['ARCHIVED', 'CANCELLED']:
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，不能作废'
        }), 400

    from_state = sample['current_state']
    add_event(sample_id, from_state, 'CANCELLED', operator_id, reason, 'CANCEL')

    return jsonify({
        'success': True,
        'message': f'样本已作废，原因：{reason}'
    })


@app.route('/api/samples/<int:sample_id>/undo', methods=['POST'])
def undo_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'undo')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    if not reason:
        return jsonify({'error': '撤销原因不能为空'}), 400

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] == 'REGISTERED':
        return jsonify({'error': '样本处于初始登记状态，无法撤销'}), 400

    prev_state = get_previous_valid_state(sample_id)
    from_state = sample['current_state']

    with get_db() as conn:
        c = conn.cursor()
        c.execute('''SELECT id FROM events 
            WHERE sample_id = ? AND is_correction = 0
            ORDER BY id DESC LIMIT 1''', (sample_id,))
        last_event = c.fetchone()

        add_event(
            sample_id, from_state, prev_state, operator_id,
            f"撤销更正：{reason}", 'UNDO',
            is_correction=1, corrected_event_id=last_event['id'] if last_event else None,
            conn=conn
        )

    return jsonify({
        'success': True,
        'message': f'已撤销，样本恢复到 [{STATES[prev_state]}] 状态'
    })


@app.route('/api/samples/<int:sample_id>/re-register', methods=['POST'])
def re_register_sample(sample_id):
    data = request.get_json()
    operator_id = data.get('operator_id')
    reason = data.get('reason', '重新登记').strip()

    if not operator_id:
        return jsonify({'error': '请指定操作员'}), 400

    ok, result = check_permission(operator_id, 'register')
    if not ok:
        return jsonify({'error': result}), 403
    user = result

    sample = get_sample(sample_id)
    if not sample:
        return jsonify({'error': '样本不存在'}), 404

    if sample['current_state'] != 'REJECTED':
        return jsonify({
            'error': f'样本当前状态为 [{STATES[sample["current_state"]]}]，只有已驳回的样本才能重新登记'
        }), 400

    add_event(sample_id, 'REJECTED', 'REGISTERED', operator_id, reason, 'RE_REGISTER')

    return jsonify({
        'success': True,
        'message': f'样本已重新登记'
    })


@app.route('/api/export/<export_type>/<identifier>', methods=['GET'])
def export_audit(export_type, identifier):
    if export_type not in ['sample', 'batch']:
        return jsonify({'error': '导出类型必须是 sample 或 batch'}), 400

    with get_db() as conn:
        c = conn.cursor()

        if export_type == 'sample':
            sample = get_sample_by_no(identifier)
            if not sample:
                return jsonify({'error': f'样本号 [{identifier}] 不存在'}), 404
            sample_ids = [sample['id']]
            filename = f'sample_{identifier}_audit.csv'
            title = f'样本 {identifier} 审计记录'
        else:
            c.execute('SELECT id FROM samples WHERE batch_no = ?', (identifier,))
            rows = c.fetchall()
            if not rows:
                return jsonify({'error': f'批次 [{identifier}] 不存在'}), 404
            sample_ids = [r['id'] for r in rows]
            filename = f'batch_{identifier}_audit.csv'
            title = f'批次 {identifier} 审计记录'

        placeholders = ','.join(['?'] * len(sample_ids))
        c.execute(f'''
            SELECT e.*, s.sample_no, s.batch_no,
                   u.name as operator_name, u.username as operator_username, u.role as operator_role
            FROM events e
            JOIN samples s ON e.sample_id = s.id
            JOIN users u ON e.operator_id = u.id
            WHERE e.sample_id IN ({placeholders})
            ORDER BY s.sample_no, e.id
        ''', sample_ids)

        events = c.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([title])
    writer.writerow([f'导出时间: {now()}'])
    writer.writerow([])
    writer.writerow([
        '样本编号', '批次号', '事件ID', '事件类型',
        '原状态', '新状态', '操作者', '用户名', '角色',
        '原因', '是否更正', '关联事件ID', '操作时间'
    ])

    for e in events:
        writer.writerow([
            e['sample_no'],
            e['batch_no'],
            e['id'],
            e['event_type'],
            STATES.get(e['from_state'], e['from_state'] or ''),
            STATES.get(e['to_state'], e['to_state']),
            e['operator_name'],
            e['operator_username'],
            ROLES.get(e['operator_role'], e['operator_role']),
            e['reason'] or '',
            '是' if e['is_correction'] else '否',
            e['corrected_event_id'] or '',
            e['created_at']
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/events', methods=['GET'])
def list_events():
    sample_id = request.args.get('sample_id', type=int)
    with get_db() as conn:
        c = conn.cursor()
        query = 'SELECT * FROM events'
        params = []
        if sample_id:
            query += ' WHERE sample_id = ?'
            params.append(sample_id)
        query += ' ORDER BY id DESC'
        c.execute(query, params)
        rows = c.fetchall()
        return jsonify([event_to_dict(r) for r in rows])


@app.route('/api/batches', methods=['GET'])
def list_batches():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT batch_no, 
                   COUNT(*) as total,
                   SUM(CASE WHEN current_state NOT IN ('ARCHIVED', 'CANCELLED') THEN 1 ELSE 0 END) as pending
            FROM samples 
            GROUP BY batch_no
            ORDER BY batch_no
        ''')
        rows = c.fetchall()
        return jsonify([dict(r) for r in rows])


@app.route('/api/permissions/<int:user_id>', methods=['GET'])
def get_user_permissions(user_id):
    user = get_current_user(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    from database import PERMISSIONS
    allowed = {}
    for action, roles in PERMISSIONS.items():
        allowed[action] = user['role'] in roles

    return jsonify({
        'user': {**user, 'role_name': ROLES.get(user['role'], user['role'])},
        'permissions': allowed
    })


@app.route('/api/roles', methods=['GET'])
def get_roles():
    return jsonify(ROLES)


@app.route('/api/states', methods=['GET'])
def get_states():
    return jsonify(STATES)


@app.route('/api/transitions', methods=['GET'])
def get_transitions():
    result = {}
    for k, v in STATE_TRANSITIONS.items():
        result[STATES[k]] = [STATES[s] for s in v]
    return jsonify(result)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
