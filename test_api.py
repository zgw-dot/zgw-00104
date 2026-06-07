"""
API 拦截测试脚本
验证所有失败路径拦截：重复样本号、跳级归档、空原因驳回、越权作废/撤销
"""
import requests
import json
import sys

BASE_URL = 'http://localhost:5000/api'

def req(method, path, data=None, parse_json=True):
    url = BASE_URL + path
    try:
        if method == 'GET':
            r = requests.get(url, params=data)
        else:
            r = requests.post(url, json=data)
        if parse_json:
            return r.status_code, r.json()
        else:
            return r.status_code, r.text
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
        400, 'POST', '/samples/6/archive',
        {'operator_id': 4},
        'S006 是已登记状态，直接归档应被拦截'
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
        200, 'POST', '/samples/6/cancel',
        {'operator_id': 1, 'reason': 'API测试作废'},
        'admin有权限作废，应该成功'
    ))
    
    results.append(test_case(
        '恢复S006到已登记',
        200, 'POST', '/samples/6/undo',
        {'operator_id': 1, 'reason': '恢复测试样本'},
        '撤销刚才的作废，恢复样本状态'
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
        400, 'POST', '/samples/7/test',
        {'operator_id': 1},
        'S007 已作废，不能再检测，应被拦截'
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
        400, 'POST', '/samples/8/undo',
        {'operator_id': 1, 'reason': '测试撤销'},
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
        print('\n🎉 拦截测试通过！')
    else:
        print(f'\n⚠️  {total - passed} 个拦截测试失败。')
    
    # ========== 回归测试：新样本主流程 ==========
    print('\n' + '=' * 70)
    print('回归测试：新样本主流程全链路验证')
    print('=' * 70)
    
    NEW_SAMPLE_NO = 'TESTREG-' + str(int(__import__('time').time()))
    NEW_BATCH_NO = 'REGTEST-001'
    sample_id = None
    event_count_before = 0
    
    # 测试1: 新样本登记成功
    print('\n📋 回归测试1: 新样本登记成功并生成事件')
    print('   描述: 验证新样本登记不触发数据库锁定，且生成时间线事件')
    status, resp = req('POST', '/samples', {
        'sample_no': NEW_SAMPLE_NO,
        'batch_no': NEW_BATCH_NO,
        'sample_type': '血液样本',
        'description': '回归测试样本',
        'operator_id': 1
    })
    success1 = status == 200 and resp.get('success')
    if success1:
        sample_id = resp['sample_id']
        print(f'   ✅ 登记成功，样本ID: {sample_id}')
        # 验证事件已生成
        status, events = req('GET', f'/events', {'sample_id': sample_id})
        event_count_before = len(events) if events else 0
        has_register_event = events and any(e['event_type'] == 'REGISTER' for e in events)
        print(f'   ✅ 事件数: {event_count_before}, 含登记事件: {has_register_event}')
        success1 = has_register_event
    else:
        print(f'   ❌ 登记失败: {resp}')
    print(f'   结果: {"✅ 通过" if success1 else "❌ 失败"}')
    results.append(success1)
    
    # 测试2: 重复样本号仍被拦截
    print('\n📋 回归测试2: 重复样本号拦截')
    print('   描述: 验证重复样本号仍被拦截，不触发500')
    status, resp = req('POST', '/samples', {
        'sample_no': NEW_SAMPLE_NO,
        'batch_no': NEW_BATCH_NO,
        'sample_type': '血液样本',
        'operator_id': 1
    })
    success2 = status == 400 and resp and '已存在' in resp.get('error', '')
    print(f'   期望: 400, 实际: {status}, 错误: {resp.get("error", "") if resp else "无响应"}')
    print(f'   结果: {"✅ 通过" if success2 else "❌ 失败"}')
    results.append(success2)
    
    # 测试3: 单样本接收（新接口）
    print('\n📋 回归测试3: 单样本接收（新接口 /receive）')
    print('   描述: 验证已登记样本可通过单样本接收接口推进')
    status, resp = req('POST', f'/samples/{sample_id}/receive', {
        'operator_id': 1,
        'reason': '回归测试接收'
    })
    success3 = status == 200 and resp.get('success')
    print(f'   期望: 200, 实际: {status}, 消息: {resp.get("message", "")}')
    if success3:
        # 验证状态变为 RECEIVED
        status, sample = req('GET', f'/samples/{sample_id}')
        success3 = sample['current_state'] == 'RECEIVED'
        print(f'   ✅ 状态更新为: {sample["current_state"]}')
    print(f'   结果: {"✅ 通过" if success3 else "❌ 失败"}')
    results.append(success3)
    
    # 测试4: 推进到检测
    print('\n📋 回归测试4: 推进到检测')
    status, resp = req('POST', f'/samples/{sample_id}/test', {
        'operator_id': 1,
        'reason': '回归测试开始检测'
    })
    success4 = status == 200
    if success4:
        status, sample = req('GET', f'/samples/{sample_id}')
        success4 = sample['current_state'] == 'TESTING'
        print(f'   ✅ 状态: {sample["current_state"]}')
    print(f'   结果: {"✅ 通过" if success4 else "❌ 失败"}')
    results.append(success4)
    
    # 测试5: 推进到复核
    print('\n📋 回归测试5: 推进到复核')
    status, resp = req('POST', f'/samples/{sample_id}/review', {
        'operator_id': 4,
        'reason': '检测完成，提交复核'
    })
    success5 = status == 200
    if success5:
        status, sample = req('GET', f'/samples/{sample_id}')
        success5 = sample['current_state'] == 'REVIEWING'
        print(f'   ✅ 状态: {sample["current_state"]}')
    print(f'   结果: {"✅ 通过" if success5 else "❌ 失败"}')
    results.append(success5)
    
    # 测试6: 空原因驳回仍不落事件
    print('\n📋 回归测试6: 空原因驳回拦截（不写入事件）')
    status, events_before = req('GET', f'/events', {'sample_id': sample_id})
    count_before = len(events_before) if events_before else 0
    status, resp = req('POST', f'/samples/{sample_id}/reject', {
        'operator_id': 4,
        'reason': ''
    })
    success6 = status == 400
    if success6:
        status, events_after = req('GET', f'/events', {'sample_id': sample_id})
        success6 = events_after and len(events_after) == count_before
        print(f'   ✅ 事件数未增加: {count_before} -> {len(events_after)}')
    print(f'   结果: {"✅ 通过" if success6 else "❌ 失败"}')
    results.append(success6)
    
    # 测试7: 正常驳回（有原因）
    print('\n📋 回归测试7: 有原因驳回成功')
    status, resp = req('POST', f'/samples/{sample_id}/reject', {
        'operator_id': 4,
        'reason': '回归测试-检测结果异常，需要复检'
    })
    success7 = status == 200
    if success7:
        status, sample = req('GET', f'/samples/{sample_id}')
        success7 = sample['current_state'] == 'REJECTED'
        print(f'   ✅ 状态: {sample["current_state"]}')
    print(f'   结果: {"✅ 通过" if success7 else "❌ 失败"}')
    results.append(success7)
    
    # 测试8: 撤销操作（不删除旧事件，新增更正事件）
    print('\n📋 回归测试8: 撤销操作验证（事件溯源）')
    status, events_before = req('GET', f'/events', {'sample_id': sample_id})
    count_before = len(events_before) if events_before else 0
    status, resp = req('POST', f'/samples/{sample_id}/undo', {
        'operator_id': 1,
        'reason': '回归测试-撤销驳回'
    })
    success8 = status == 200
    if success8:
        status, sample = req('GET', f'/samples/{sample_id}')
        success8 = sample and sample['current_state'] == 'REVIEWING'
        print(f'   ✅ 撤销后状态: {sample["current_state"]}')
        status, events_after = req('GET', f'/events', {'sample_id': sample_id})
        has_correction = events_after and any(e.get('is_correction') == 1 for e in events_after)
        print(f'   ✅ 事件数: {count_before} -> {len(events_after) if events_after else 0}, 含更正事件: {has_correction}')
        success8 = success8 and has_correction and events_after and len(events_after) == count_before + 1
    print(f'   结果: {"✅ 通过" if success8 else "❌ 失败"}')
    results.append(success8)
    
    # 测试9: 归档
    print('\n📋 回归测试9: 归档')
    status, resp = req('POST', f'/samples/{sample_id}/archive', {
        'operator_id': 4,
        'reason': '复核通过，归档'
    })
    success9 = status == 200
    if success9:
        status, sample = req('GET', f'/samples/{sample_id}')
        success9 = sample['current_state'] == 'ARCHIVED'
        print(f'   ✅ 状态: {sample["current_state"]}')
    print(f'   结果: {"✅ 通过" if success9 else "❌ 失败"}')
    results.append(success9)
    
    # 测试10: 导出审计与时间线一致
    print('\n📋 回归测试10: 导出审计与时间线一致')
    status, events = req('GET', f'/events', {'sample_id': sample_id})
    status, export_resp = req('GET', f'/export/sample/{NEW_SAMPLE_NO}', parse_json=False)
    event_count = len(events) if events else 0
    csv_lines = export_resp.strip().split('\n') if export_resp else []
    # CSV 格式：标题行 + 导出时间行 + 空行 + 表头行 + N行数据
    # 找到表头行（包含"事件类型"），之后的行是数据行
    data_start = None
    for i, line in enumerate(csv_lines):
        if '事件类型' in line:
            data_start = i + 1
            break
    data_lines = csv_lines[data_start:] if data_start else []
    success10 = len(data_lines) == event_count
    print(f'   ✅ 时间线事件数: {event_count}, CSV 数据行数: {len(data_lines)}')
    # 验证 CSV 内容包含操作者和状态变化
    has_operator = any('系统管理员' in line for line in csv_lines)
    has_states = any('已登记' in line for line in csv_lines)
    success10 = success10 and has_operator and has_states
    print(f'   ✅ CSV 包含操作者: {has_operator}, 包含状态: {has_states}')
    print(f'   结果: {"✅ 通过" if success10 else "❌ 失败"}')
    results.append(success10)
    
    # 测试11: 批次接收后推进
    print('\n📋 回归测试11: 按批次接收后推进完整流程')
    BATCH_SAMPLE = 'BATCH-REG-' + str(int(__import__('time').time()))
    # 登记一个新样本
    status, resp = req('POST', '/samples', {
        'sample_no': BATCH_SAMPLE,
        'batch_no': 'BATCH-REGRESSION',
        'sample_type': '尿液样本',
        'description': '批次接收回归测试',
        'operator_id': 2
    })
    if status == 200:
        batch_sample_id = resp['sample_id']
        # 批次接收
        status, resp = req('POST', '/batches/receive', {
            'batch_no': 'BATCH-REGRESSION',
            'operator_id': 2
        })
        success11 = status == 200
        if success11:
            # 推进到检测
            status, _ = req('POST', f'/samples/{batch_sample_id}/test', {'operator_id': 2})
            # 推进到复核
            status, _ = req('POST', f'/samples/{batch_sample_id}/review', {'operator_id': 4})
            # 归档
            status, _ = req('POST', f'/samples/{batch_sample_id}/archive', {'operator_id': 4})
            status, sample = req('GET', f'/samples/{batch_sample_id}')
            success11 = sample['current_state'] == 'ARCHIVED'
            print(f'   ✅ 批次样本最终状态: {sample["current_state"]}')
    else:
        success11 = False
    print(f'   结果: {"✅ 通过" if success11 else "❌ 失败"}')
    results.append(success11)
    
    print('\n' + '=' * 70)
    print('最终测试总结')
    print('=' * 70)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'总测试用例: {total}')
    print(f'通过: {passed}')
    print(f'失败: {total - passed}')
    print(f'通过率: {passed/total*100:.1f}%')
    
    if passed == total:
        print('\n🎉 所有测试通过！修复成功！')
    else:
        print(f'\n⚠️  {total - passed} 个测试失败，请检查。')
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
