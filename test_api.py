"""
API 拦截测试脚本
验证所有失败路径拦截：重复样本号、跳级归档、空原因驳回、越权作废/撤销
"""
import requests
import json
import sys

BASE_URL = 'http://localhost:5000/api'

def req(method, path, data=None):
    url = BASE_URL + path
    try:
        if method == 'GET':
            r = requests.get(url, params=data)
        else:
            r = requests.post(url, json=data)
        return r.status_code, r.json()
    except Exception as e:
        print(f'  ❌ 请求失败: {e}')
        return None, None

def test_case(name, expected_status, method, path, data, desc):
    print(f'\n📋 {name}')
    print(f'   描述: {desc}')
    status, resp = req(method, path, data)
    if status is None:
        return False
    success = status == expected_status
    icon = '✅' if success else '❌'
    print(f'   期望状态码: {expected_status}, 实际: {status}')
    if resp:
        if 'error' in resp:
            print(f'   返回错误: {resp["error"]}')
        elif 'message' in resp:
            print(f'   返回消息: {resp["message"]}')
        else:
            print(f'   返回: {json.dumps(resp, ensure_ascii=False)[:100]}')
    print(f'   结果: {icon} {"通过" if success else "失败"}')
    return success

def main():
    print('=' * 70)
    print('实验室样本流转工作台 - API 拦截功能测试')
    print('=' * 70)
    
    try:
        status, _ = req('GET', '/users')
        if status != 200:
            print('❌ 后端服务未启动，请先启动后端服务')
            sys.exit(1)
    except:
        print('❌ 无法连接到后端服务，请先启动后端服务')
        sys.exit(1)
    
    print('\n✅ 后端服务连接成功')
    
    results = []
    
    print('\n' + '=' * 70)
    print('一、重复样本号拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '重复样本号拦截',
        400, 'POST', '/samples',
        {
            'sample_no': 'S001',
            'batch_no': 'BATCH-TEST',
            'sample_type': '血液样本',
            'description': '测试重复',
            'operator_id': 1
        },
        '尝试登记已存在的样本号 S001，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('二、跳级归档拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '对已登记样本直接归档',
        400, 'POST', '/samples/8/archive',
        {'operator_id': 1},
        'S008 是已登记状态，直接归档应被拦截'
    ))
    
    results.append(test_case(
        '对已接收样本直接归档',
        400, 'POST', '/samples/5/archive',
        {'operator_id': 1},
        'S005 是已接收状态，直接归档应被拦截'
    ))
    
    results.append(test_case(
        '对检测中样本直接归档',
        400, 'POST', '/samples/3/archive',
        {'operator_id': 1},
        'S003 是检测中状态，直接归档应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('三、空原因驳回拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '空原因驳回',
        400, 'POST', '/samples/4/reject',
        {'operator_id': 4, 'reason': ''},
        '驳回原因不能为空，应被拦截'
    ))
    
    results.append(test_case(
        '正常驳回（有原因）',
        200, 'POST', '/samples/4/reject',
        {'operator_id': 4, 'reason': 'API测试驳回'},
        '有原因的驳回应该成功，先测试这个以便后续恢复'
    ))
    
    results.append(test_case(
        '恢复S004到复核中',
        200, 'POST', '/samples/4/undo',
        {'operator_id': 1, 'reason': 'API测试恢复'},
        '撤销刚才的驳回，恢复样本状态'
    ))
    
    print('\n' + '=' * 70)
    print('四、越权作废拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '普通操作员作废样本',
        403, 'POST', '/samples/6/cancel',
        {'operator_id': 2, 'reason': '越权测试作废'},
        '张三(operator)无权限作废，应被拦截'
    ))
    
    results.append(test_case(
        '复核员作废样本',
        403, 'POST', '/samples/6/cancel',
        {'operator_id': 4, 'reason': '越权测试作废'},
        '王五(reviewer)无权限作废，应被拦截'
    ))
    
    results.append(test_case(
        '管理员作废样本',
        200, 'POST', '/samples/8/cancel',
        {'operator_id': 1, 'reason': 'API测试作废'},
        'admin有权限作废，应该成功'
    ))
    
    print('\n' + '=' * 70)
    print('五、越权撤销拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '普通操作员撤销操作',
        403, 'POST', '/samples/3/undo',
        {'operator_id': 2, 'reason': '越权测试撤销'},
        '张三(operator)无权限撤销，应被拦截'
    ))
    
    results.append(test_case(
        '复核员撤销操作',
        403, 'POST', '/samples/3/undo',
        {'operator_id': 4, 'reason': '越权测试撤销'},
        '王五(reviewer)无权限撤销，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('六、越权归档拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '普通操作员归档样本',
        403, 'POST', '/samples/4/archive',
        {'operator_id': 2},
        '张三(operator)无权限归档，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('七、越权驳回拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '普通操作员驳回样本',
        403, 'POST', '/samples/4/reject',
        {'operator_id': 2, 'reason': '越权测试驳回'},
        '张三(operator)无权限驳回，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('八、非法状态流转测试')
    print('=' * 70)
    
    results.append(test_case(
        '已归档样本尝试检测',
        400, 'POST', '/samples/1/test',
        {'operator_id': 1},
        'S001 已归档，不能再检测，应被拦截'
    ))
    
    results.append(test_case(
        '已作废样本尝试检测',
        400, 'POST', '/samples/8/test',
        {'operator_id': 1},
        'S008 已作废，不能再检测，应被拦截'
    ))
    
    results.append(test_case(
        '已驳回样本尝试检测（不经过重新登记）',
        400, 'POST', '/samples/2/test',
        {'operator_id': 1},
        'S002 已驳回，必须先重新登记，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('九、空原因作废拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '空原因作废',
        400, 'POST', '/samples/6/cancel',
        {'operator_id': 1, 'reason': ''},
        '作废原因不能为空，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('十、空原因撤销拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '空原因撤销',
        400, 'POST', '/samples/4/undo',
        {'operator_id': 1, 'reason': ''},
        '撤销原因不能为空，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('十一、撤销初始状态拦截测试')
    print('=' * 70)
    
    results.append(test_case(
        '已登记状态撤销',
        400, 'POST', '/samples/6/undo',
        {'operator_id': 1, 'reason': '测试撤销初始状态'},
        '初始登记状态无法撤销，应被拦截'
    ))
    
    print('\n' + '=' * 70)
    print('十二、审计导出测试')
    print('=' * 70)
    
    try:
        r = requests.get(BASE_URL + '/export/sample/S003')
        success = r.status_code == 200 and 'S003' in r.text
        print(f'\n📋 样本审计导出')
        print(f'   描述: 导出 S003 的审计记录')
        print(f'   期望状态码: 200, 实际: {r.status_code}')
        print(f'   结果: {"✅ 通过" if success else "❌ 失败"}')
        results.append(success)
    except Exception as e:
        print(f'   ❌ 导出失败: {e}')
        results.append(False)
    
    try:
        r = requests.get(BASE_URL + '/export/batch/BATCH-2026-001')
        success = r.status_code == 200 and 'BATCH-2026-001' in r.text
        print(f'\n📋 批次审计导出')
        print(f'   描述: 导出 BATCH-2026-001 的审计记录')
        print(f'   期望状态码: 200, 实际: {r.status_code}')
        print(f'   结果: {"✅ 通过" if success else "❌ 失败"}')
        results.append(success)
    except Exception as e:
        print(f'   ❌ 导出失败: {e}')
        results.append(False)
    
    print('\n' + '=' * 70)
    print('十三、撤销不删除旧事件验证')
    print('=' * 70)
    
    status, resp = req('GET', '/samples/3')
    if status == 200 and resp.get('events'):
        events = resp['events']
        has_correction = any(e.get('is_correction') == 1 for e in events)
        old_events_count = sum(1 for e in events if e.get('is_correction') == 0)
        print(f'\n📋 S003 事件记录验证')
        print(f'   总事件数: {len(events)}')
        print(f'   正常事件数: {old_events_count}')
        print(f'   更正事件数: {len(events) - old_events_count}')
        print(f'   存在更正事件: {has_correction}')
        success = has_correction and len(events) >= 5
        print(f'   结果: {"✅ 通过" if success else "❌ 失败"}')
        results.append(success)
    
    print('\n' + '=' * 70)
    print('测试总结')
    print('=' * 70)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'总测试用例: {total}')
    print(f'通过: {passed}')
    print(f'失败: {total - passed}')
    print(f'通过率: {passed/total*100:.1f}%')
    
    if passed == total:
        print('\n🎉 所有测试通过！API 拦截功能正常工作。')
    else:
        print(f'\n⚠️  {total - passed} 个测试失败，请检查。')
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
