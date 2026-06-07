import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_db, DB_PATH, ROLES, STATES
from datetime import datetime, timedelta


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def time_ago(minutes):
    return (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')


def seed_data():
    if os.path.exists(DB_PATH):
        print(f'数据库已存在: {DB_PATH}')
        print('如需重新初始化，请先删除该文件')
        return

    print('初始化数据库...')
    init_db()

    with get_db() as conn:
        c = conn.cursor()

        print('创建用户...')
        users = [
            ('admin', 'admin', '系统管理员', time_ago(10000)),
            ('zhangsan', 'operator', '张三', time_ago(9900)),
            ('lisi', 'operator', '李四', time_ago(9800)),
            ('wangwu', 'reviewer', '王五', time_ago(9700)),
            ('zhaoliu', 'reviewer', '赵六', time_ago(9600)),
        ]
        c.executemany('INSERT INTO users (username, role, name, created_at) VALUES (?, ?, ?, ?)', users)

        print('创建样本示例数据...')

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S001', 'BATCH-2026-001', '血液样本', '常规体检样本 - 张三', 'ARCHIVED',
             2, time_ago(500), 4, time_ago(100)))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (1, None, 'REGISTERED', 2, '样本登记', 'REGISTER', 0, None, time_ago(500)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (1, 'REGISTERED', 'RECEIVED', 2, '批次接收', 'RECEIVE', 0, None, time_ago(450)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (1, 'RECEIVED', 'TESTING', 2, '开始检测', 'TEST', 0, None, time_ago(400)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (1, 'TESTING', 'REVIEWING', 2, '检测完成，提交复核', 'REVIEW', 0, None, time_ago(300)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (1, 'REVIEWING', 'ARCHIVED', 4, '复核通过，结果正常', 'ARCHIVE', 0, None, time_ago(100)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S002', 'BATCH-2026-001', '血液样本', '常规体检样本 - 李四', 'REJECTED',
             3, time_ago(480), 5, time_ago(80)))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (2, None, 'REGISTERED', 3, '样本登记', 'REGISTER', 0, None, time_ago(480)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (2, 'REGISTERED', 'RECEIVED', 3, '批次接收', 'RECEIVE', 0, None, time_ago(430)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (2, 'RECEIVED', 'TESTING', 3, '开始检测', 'TEST', 0, None, time_ago(380)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (2, 'TESTING', 'REVIEWING', 3, '检测完成，提交复核', 'REVIEW', 0, None, time_ago(280)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (2, 'REVIEWING', 'REJECTED', 5, '检测结果异常，需要重新取样检测', 'REJECT', 0, None, time_ago(80)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S003', 'BATCH-2026-001', '血液样本', '常规体检样本 - 撤销演示', 'TESTING',
             2, time_ago(460), 1, time_ago(60)))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (3, None, 'REGISTERED', 2, '样本登记', 'REGISTER', 0, None, time_ago(460)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (3, 'REGISTERED', 'RECEIVED', 2, '批次接收', 'RECEIVE', 0, None, time_ago(410)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (3, 'RECEIVED', 'TESTING', 2, '开始检测', 'TEST', 0, None, time_ago(360)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (3, 'TESTING', 'REVIEWING', 2, '检测完成，提交复核', 'REVIEW', 0, None, time_ago(260)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (3, 'REVIEWING', 'TESTING', 1, '撤销更正：复核操作有误，恢复到检测中重新检测', 'UNDO', 1, 11, time_ago(60)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S004', 'BATCH-2026-002', '尿液样本', '入职体检样本', 'REVIEWING',
             3, time_ago(200), 3, time_ago(50)))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (4, None, 'REGISTERED', 3, '样本登记', 'REGISTER', 0, None, time_ago(200)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (4, 'REGISTERED', 'RECEIVED', 3, '批次接收', 'RECEIVE', 0, None, time_ago(180)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (4, 'RECEIVED', 'TESTING', 3, '开始检测', 'TEST', 0, None, time_ago(150)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (4, 'TESTING', 'REVIEWING', 3, '检测完成，提交复核', 'REVIEW', 0, None, time_ago(50)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S005', 'BATCH-2026-002', '尿液样本', '入职体检样本', 'RECEIVED',
             3, time_ago(190), 3, time_ago(170)))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (5, None, 'REGISTERED', 3, '样本登记', 'REGISTER', 0, None, time_ago(190)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (5, 'REGISTERED', 'RECEIVED', 3, '批次接收', 'RECEIVE', 0, None, time_ago(170)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S006', 'BATCH-2026-002', '尿液样本', '入职体检样本', 'REGISTERED',
             3, time_ago(185), None, None))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (6, None, 'REGISTERED', 3, '样本登记', 'REGISTER', 0, None, time_ago(185)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S007', 'BATCH-2026-003', '粪便样本', '住院患者样本', 'CANCELLED',
             2, time_ago(300), 1, time_ago(120)))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (7, None, 'REGISTERED', 2, '样本登记', 'REGISTER', 0, None, time_ago(300)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (7, 'REGISTERED', 'RECEIVED', 2, '批次接收', 'RECEIVE', 0, None, time_ago(270)))
        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (7, 'RECEIVED', 'CANCELLED', 1, '患者已出院，样本作废', 'CANCEL', 0, None, time_ago(120)))

        c.execute('''INSERT INTO samples 
            (sample_no, batch_no, sample_type, description, current_state, 
             registered_by, registered_at, last_handler, last_handled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('S008', 'BATCH-2026-003', '粪便样本', '住院患者样本', 'REGISTERED',
             2, time_ago(290), None, None))

        c.execute('''INSERT INTO events 
            (sample_id, from_state, to_state, operator_id, reason, event_type, is_correction, corrected_event_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (8, None, 'REGISTERED', 2, '样本登记', 'REGISTER', 0, None, time_ago(290)))

    print('\n=== 初始化完成 ===')
    print(f'数据库位置: {DB_PATH}')
    print('\n用户账号（用于模拟登录）:')
    print('  ID=1  admin    系统管理员  [admin]')
    print('  ID=2  zhangsan 张三        [operator]')
    print('  ID=3  lisi     李四        [operator]')
    print('  ID=4  wangwu   王五        [reviewer]')
    print('  ID=5  zhaoliu  赵六        [reviewer]')
    print('\n示例数据说明:')
    print('  BATCH-2026-001: S001(已归档), S002(已驳回), S003(检测中-含撤销记录)')
    print('  BATCH-2026-002: S004(复核中), S005(已接收), S006(已登记)')
    print('  BATCH-2026-003: S007(已作废), S008(已登记)')
    print('\n  覆盖场景: 正常流程、驳回、撤销更正、作废')


if __name__ == '__main__':
    seed_data()
