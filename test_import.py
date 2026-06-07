"""
批量导入功能测试脚本
覆盖场景：成功导入、部分失败、越权导入、重启后查询、导出一致性
"""
import requests
import json
import sys
import os
import io
import csv
import time

BASE_URL = 'http://localhost:5000/api'

def req(method, path, data=None, parse_json=True, files=None):
    url = BASE_URL + path
    try:
        if method == 'GET':
            r = requests.get(url, params=data)
        elif files:
            r = requests.post(url, data=data, files=files)
        else:
            r = requests.post(url, json=data)
        if parse_json:
            return r.status_code, r.json()
        else:
            return r.status_code, r.text
    except Exception as e:
        print(f'  ❌ 请求失败: {e}')
        return None, None

def test_case(name, expected_status, method, path, data=None, files=None, desc=''):
    print(f'\n📋 {name}')
    print(f'   描述: {desc}')
    status, resp = req(method, path, data, files=files)
    if status is None:
        return False, None
    success = status == expected_status
    icon = '✅' if success else '❌'
    print(f'   期望状态码: {expected_status}, 实际: {status}')
    if resp and isinstance(resp, dict):
        if 'error' in resp:
            print(f'   返回错误: {resp["error"]}')
        elif 'message' in resp:
            print(f'   返回消息: {resp["message"]}')
        if 'success_count' in resp or 'failure_count' in resp:
            print(f'   成功: {resp.get("success_count")}, 失败: {resp.get("failure_count")}')
    print(f'   结果: {icon} {"通过" if success else "失败"}')
    return success, resp

def create_csv_content(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode('utf-8-sig')

def main():
    print('=' * 80)
    print('实验室样本流转工作台 - 批量导入功能测试')
    print('=' * 80)
    
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
    timestamp = str(int(time.time()))
    
    # ========== 一、越权导入测试 ==========
    print('\n' + '=' * 80)
    print('一、越权导入拦截测试')
    print('=' * 80)
    
    csv_data = create_csv_content([
        ['样本号', '批次号', '样本类型', '描述'],
        ['IMP-AUTH-001', 'BATCH-AUTH', '血液样本', '越权测试样本'],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    data = {'operator_id': 999}
    
    success, resp = test_case(
        '不存在的用户导入',
        403, 'POST', '/samples/import',
        data=data, files=files,
        desc='使用不存在的用户ID导入，应被拦截'
    )
    results.append(success)
    
    success, resp = test_case(
        '未指定操作员导入',
        400, 'POST', '/samples/import',
        data={'rows': [{'样本号': 'IMP-AUTH-002', '批次号': 'BATCH-AUTH', '样本类型': '血液样本'}]},
        desc='不指定operator_id导入，应被拦截（权限校验前置）'
    )
    results.append(success)
    
    # ========== 二、CSV格式错误测试 ==========
    print('\n' + '=' * 80)
    print('二、CSV格式与必填项校验测试')
    print('=' * 80)
    
    csv_data = create_csv_content([
        ['样本号', '批次号', '样本类型', '描述'],
        ['', 'BATCH-EMPTY', '血液样本', '空样本号'],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    
    success, resp = test_case(
        '空样本号拦截',
        200, 'POST', '/samples/import',
        data={'operator_id': 1}, files=files,
        desc='CSV包含空样本号，应该记录为失败，整体请求成功但failure_count>0'
    )
    if success and resp:
        has_empty_error = any(f['error_type'] == 'MISSING_REQUIRED' and '样本号不能为空' in f['error_message'] 
                            for f in resp.get('failure_items', []))
        results.append(has_empty_error)
        print(f'   包含空样本号错误: {"✅ 通过" if has_empty_error else "❌ 失败"}')
    else:
        results.append(False)
    
    csv_data = create_csv_content([
        ['样本号', '样本类型', '描述'],
        ['IMP-MISS-001', '血液样本', '缺少批次号列'],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    
    success, resp = test_case(
        '缺少必填列拦截',
        200, 'POST', '/samples/import',
        data={'operator_id': 1}, files=files,
        desc='CSV缺少批次号列，应该记录为失败'
    )
    if success and resp:
        has_missing_col = any(f['error_type'] == 'MISSING_REQUIRED' for f in resp.get('failure_items', []))
        results.append(has_missing_col)
        print(f'   包含缺少必填列错误: {"✅ 通过" if has_missing_col else "❌ 失败"}')
    else:
        results.append(False)
    
    # ========== 二-新增：描述必填校验 ==========
    print('\n' + '=' * 80)
    print('二-新增：描述必填校验测试')
    print('=' * 80)
    
    # 测试1: 空描述值（CSV）
    csv_data = create_csv_content([
        ['样本号', '批次号', '样本类型', '描述'],
        ['IMP-DESC-EMPTY-001', 'BATCH-DESC-001', '血液样本', ''],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    
    success, resp = test_case(
        '空描述值拦截（CSV）',
        200, 'POST', '/samples/import',
        data={'operator_id': 1}, files=files,
        desc='CSV包含空描述值，应该记录为失败'
    )
    if success and resp:
        has_empty_desc = any(f['error_type'] == 'MISSING_REQUIRED' and '描述' in f['error_message'] 
                        for f in resp.get('failure_items', []))
        results.append(has_empty_desc)
        print(f'   包含空描述错误: {"✅ 通过" if has_empty_desc else "❌ 失败"}')
    else:
        results.append(False)
    
    # 测试2: 缺少描述列（CSV）
    csv_data = create_csv_content([
        ['样本号', '批次号', '样本类型'],
        ['IMP-DESC-MISSCOL-001', 'BATCH-DESC-002', '血液样本'],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    
    success, resp = test_case(
        '缺少描述列拦截（CSV）',
        200, 'POST', '/samples/import',
        data={'operator_id': 1}, files=files,
        desc='CSV缺少描述列，应该记录为失败'
    )
    if success and resp:
        has_missing_desc = any(f['error_type'] == 'MISSING_REQUIRED' and '描述' in f['error_message'] 
                        for f in resp.get('failure_items', []))
        results.append(has_missing_desc)
        print(f'   包含缺描述列错误: {"✅ 通过" if has_missing_desc else "❌ 失败"}')
    else:
        results.append(False)
    
    # 测试3: JSON缺描述值
    json_rows = [
        {'样本号': 'IMP-DESC-JSON-001', '批次号': 'BATCH-DESC-003', '样本类型': '血液样本', '描述': ''},
    ]
    
    success, resp = test_case(
        '空描述值拦截（JSON）',
        200, 'POST', '/samples/import',
        data={'operator_id': 1, 'rows': json_rows},
        desc='JSON包含空描述值，应该记录为失败'
    )
    if success and resp:
        has_empty_desc_json = any(f['error_type'] == 'MISSING_REQUIRED' and '描述' in f['error_message'] 
                        for f in resp.get('failure_items', []))
        results.append(has_empty_desc_json)
        print(f'   包含空描述错误: {"✅ 通过" if has_empty_desc_json else "❌ 失败"}')
    else:
        results.append(False)
    
    # 测试4: JSON缺Description别名（带大写D）
    json_rows_desc = [
        {'sample_no': 'IMP-DESC-ALIAS-001', 'batch_no': 'BATCH-DESC-004', 'sample_type': '血液样本', 'Description': '正常样本带描述'},
    ]
    
    success, resp = test_case(
        'Description别名支持（JSON）',
        200, 'POST', '/samples/import',
        data={'operator_id': 1, 'rows': json_rows_desc},
        desc='使用Description别名（大写D），应该成功'
    )
    if success and resp:
        desc_alias_ok = resp.get('success_count') == 1
        results.append(desc_alias_ok)
        print(f'   Description别名识别成功: {"✅ 通过" if desc_alias_ok else "❌ 失败"}')
    else:
        results.append(False)
    
    # ========== 三、重复样本号测试 ==========
    print('\n' + '=' * 80)
    print('三、重复样本号检测测试')
    print('=' * 80)
    
    csv_data = create_csv_content([
        ['样本号', '批次号', '样本类型', '描述'],
        [f'IMP-DUP-{timestamp}-01', f'BATCH-DUP-{timestamp}', '血液样本', '重复样本1'],
        [f'IMP-DUP-{timestamp}-01', f'BATCH-DUP-{timestamp}', '血液样本', '重复样本2'],
        [f'IMP-DUP-{timestamp}-02', f'BATCH-DUP-{timestamp}', '尿液样本', '正常样本'],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    
    success, resp = test_case(
        '文件内重复样本号检测',
        200, 'POST', '/samples/import',
        data={'operator_id': 1}, files=files,
        desc='CSV包含重复样本号，应该成功2条，失败1条（第二个重复的）'
    )
    if success and resp:
        correct_counts = resp.get('success_count') == 2 and resp.get('failure_count') == 1
        has_dup_error = any(f['error_type'] == 'DUPLICATE_IN_FILE' for f in resp.get('failure_items', []))
        file_dup_ok = correct_counts and has_dup_error
        results.append(file_dup_ok)
        print(f'   计数正确: {"✅" if correct_counts else "❌"}, 错误类型正确: {"✅" if has_dup_error else "❌"}')
        print(f'   结果: {"✅ 通过" if file_dup_ok else "❌ 失败"}')
        file_dup_batch_id = resp.get('import_batch_id') if file_dup_ok else None
    else:
        results.append(False)
        file_dup_batch_id = None
    
    csv_data = create_csv_content([
        ['样本号', '批次号', '样本类型', '描述'],
        ['S001', f'BATCH-EXIST-{timestamp}', '血液样本', '数据库已存在'],
        [f'IMP-NEW-{timestamp}-01', f'BATCH-NEW-{timestamp}', '血液样本', '新样本'],
    ])
    files = {'file': ('test.csv', io.BytesIO(csv_data), 'text/csv')}
    
    success, resp = test_case(
        '数据库重复样本号检测',
        200, 'POST', '/samples/import',
        data={'operator_id': 1}, files=files,
        desc='CSV包含数据库已存在的S001，应该成功1条，失败1条'
    )
    if success and resp:
        correct_counts = resp.get('success_count') == 1 and resp.get('failure_count') == 1
        has_db_dup = any(f['error_type'] == 'DUPLICATE_IN_DB' for f in resp.get('failure_items', []))
        db_dup_ok = correct_counts and has_db_dup
        results.append(db_dup_ok)
        print(f'   计数正确: {"✅" if correct_counts else "❌"}, 错误类型正确: {"✅" if has_db_dup else "❌"}')
        print(f'   结果: {"✅ 通过" if db_dup_ok else "❌ 失败"}')
        db_dup_batch_id = resp.get('import_batch_id') if db_dup_ok else None
        imported_sample_id = resp.get('success_items', [{}])[0].get('sample_id') if db_dup_ok else None
        imported_sample_no = resp.get('success_items', [{}])[0].get('sample_no') if db_dup_ok else None
    else:
        results.append(False)
        db_dup_batch_id = None
        imported_sample_id = None
        imported_sample_no = None
    
    # ========== 四、成功导入测试 ==========
    print('\n' + '=' * 80)
    print('四、成功导入测试（JSON API方式）')
    print('=' * 80)
    
    import_rows = [
        {'样本号': f'IMP-SUCCESS-{timestamp}-01', '批次号': f'BATCH-IMP-{timestamp}', '样本类型': '血液样本', '描述': '成功样本1'},
        {'样本号': f'IMP-SUCCESS-{timestamp}-02', '批次号': f'BATCH-IMP-{timestamp}', '样本类型': '尿液样本', '描述': '成功样本2'},
        {'样本号': f'IMP-SUCCESS-{timestamp}-03', '批次号': f'BATCH-IMP-{timestamp}', '样本类型': '粪便样本', '描述': '成功样本3'},
    ]
    
    success, resp = test_case(
        'JSON API批量导入成功',
        200, 'POST', '/samples/import',
        data={'operator_id': 1, 'rows': import_rows},
        desc='通过JSON API批量导入3条样本，全部成功'
    )
    if success and resp:
        import_batch_id = resp.get('import_batch_id')
        success_count = resp.get('success_count')
        success_items = resp.get('success_items', [])
        
        all_success = success_count == 3 and len(success_items) == 3
        results.append(all_success)
        print(f'   全部成功: {"✅ 通过" if all_success else "❌ 失败"}')
        
        # 验证样本状态为已登记
        sample_ids = [item['sample_id'] for item in success_items]
        all_registered = True
        has_import_events = True
        for item in success_items:
            status, sample = req('GET', f"/samples/{item['sample_id']}")
            if sample and sample.get('current_state') != 'REGISTERED':
                all_registered = False
            events = sample.get('events', []) if sample else []
            has_import_event = any('批量导入' in e.get('reason', '') for e in events)
            if not has_import_event:
                has_import_events = False
        
        results.append(all_registered)
        print(f'   状态均为已登记: {"✅ 通过" if all_registered else "❌ 失败"}')
        results.append(has_import_events)
        print(f'   均含批量导入事件: {"✅ 通过" if has_import_events else "❌ 失败"}')
        
        # 保存成功导入的样本供重启后验证
        test_samples_for_restart = [(item['sample_no'], item['sample_id']) for item in success_items]
    else:
        results.append(False)
        results.append(False)
        results.append(False)
        import_batch_id = None
        test_samples_for_restart = []
    
    # ========== 五、时间线与导出一致性测试 ==========
    print('\n' + '=' * 80)
    print('五、时间线与导出一致性测试')
    print('=' * 80)
    
    if imported_sample_id and imported_sample_no:
        status, sample = req('GET', f"/samples/{imported_sample_id}")
        if status == 200 and sample:
            events = sample.get('events', [])
            has_register_event = any(e['event_type'] == 'REGISTER' for e in events)
            results.append(has_register_event)
            print(f'   样本时间线含登记事件: {"✅ 通过" if has_register_event else "❌ 失败"}')
            
            event_count = len(events)
            status, csv_text = req('GET', f"/export/sample/{imported_sample_no}", parse_json=False)
            if status == 200 and csv_text:
                csv_lines = csv_text.strip().split('\n')
                data_start = None
                for i, line in enumerate(csv_lines):
                    if '事件类型' in line:
                        data_start = i + 1
                        break
                data_lines = csv_lines[data_start:] if data_start else []
                csv_matches = len(data_lines) == event_count
                results.append(csv_matches)
                print(f'   时间线事件数({event_count})与CSV行数({len(data_lines)})一致: {"✅ 通过" if csv_matches else "❌ 失败"}')
            else:
                results.append(False)
                print('   ❌ 导出CSV失败')
        else:
            results.append(False)
            results.append(False)
            print('   ❌ 获取样本详情失败')
    else:
        results.append(False)
        results.append(False)
        print('   ⚠️  跳过，无导入样本ID')
    
    # ========== 六、失败记录持久化测试 ==========
    print('\n' + '=' * 80)
    print('六、失败记录持久化查询测试')
    print('=' * 80)
    
    if file_dup_batch_id:
        status, failures = req('GET', '/import/failures', {'batch_id': file_dup_batch_id})
        if status == 200 and isinstance(failures, list):
            has_failures = len(failures) >= 1
            has_correct_type = any(f.get('error_type') == 'DUPLICATE_IN_FILE' for f in failures)
            failure_persisted = has_failures and has_correct_type
            results.append(failure_persisted)
            print(f'   查询到失败记录: {"✅" if has_failures else "❌"}, 类型正确: {"✅" if has_correct_type else "❌"}')
            print(f'   结果: {"✅ 通过" if failure_persisted else "❌ 失败"}')
        else:
            results.append(False)
            print('   ❌ 查询失败记录失败')
    else:
        results.append(False)
        print('   ⚠️  跳过，无导入批次ID')
    
    # ========== 七、导入结果导出测试 ==========
    print('\n' + '=' * 80)
    print('七、导入结果审计CSV导出测试')
    print('=' * 80)
    
    if import_batch_id:
        status, csv_text = req('GET', f"/export/import/{import_batch_id}", parse_json=False)
        if status == 200 and csv_text:
            has_title = '批量导入结果审计' in csv_text
            has_success_section = '成功导入的样本' in csv_text
            has_failure_section = '导入失败记录' in csv_text
            has_batch_id = import_batch_id in csv_text
            
            # 验证成功样本的描述不为空
            success_items_for_export = success_items  # 来自第四节成功导入
            success_desc_ok = all(item.get('description', '').strip() for item in success_items_for_export)
            
            export_ok = has_title and has_success_section and has_failure_section and has_batch_id and success_desc_ok
            results.append(export_ok)
            print(f'   包含标题: {"✅" if has_title else "❌"}')
            print(f'   包含成功区: {"✅" if has_success_section else "❌"}')
            print(f'   包含失败区: {"✅" if has_failure_section else "❌"}')
            print(f'   包含批次号: {"✅" if has_batch_id else "❌"}')
            print(f'   成功样本描述均非空: {"✅" if success_desc_ok else "❌"}')
            print(f'   结果: {"✅ 通过" if export_ok else "❌ 失败"}')
        else:
            results.append(False)
            print('   ❌ 导出导入审计失败')
    else:
        results.append(False)
        print('   ⚠️  跳过，无导入批次ID')
    
    # ========== 八、部分成功原子性测试 ==========
    print('\n' + '=' * 80)
    print('八、部分成功原子性测试')
    print('=' * 80)
    
    mix_rows = [
        {'样本号': f'IMP-MIX-{timestamp}-01', '批次号': f'BATCH-MIX-{timestamp}', '样本类型': '血液样本', '描述': '成功1'},
        {'样本号': '', '批次号': f'BATCH-MIX-{timestamp}', '样本类型': '尿液样本', '描述': '空样本号失败'},
        {'样本号': f'IMP-MIX-{timestamp}-02', '批次号': f'BATCH-MIX-{timestamp}', '样本类型': '粪便样本', '描述': '成功2'},
        {'样本号': f'IMP-MIX-{timestamp}-01', '批次号': f'BATCH-MIX-{timestamp}', '样本类型': '血液样本', '描述': '文件内重复失败'},
        {'样本号': 'S001', '批次号': f'BATCH-MIX-{timestamp}', '样本类型': '血液样本', '描述': 'DB重复失败'},
        {'样本号': f'IMP-MIX-{timestamp}-03', '批次号': '', '样本类型': '唾液样本', '描述': '空批次号失败'},
        {'样本号': f'IMP-MIX-{timestamp}-04', '批次号': f'BATCH-MIX-{timestamp}', '样本类型': '精液样本', '描述': ''},  # 空描述失败
    ]
    
    success, resp = test_case(
        '部分成功测试（2成功5失败）',
        200, 'POST', '/samples/import',
        data={'operator_id': 1, 'rows': mix_rows},
        desc='混合成功和失败场景，验证成功的不丢失（2成功：IMP-MIX-01、IMP-MIX-02；5失败：空样本号、重复、DB重复、空批次号、空描述）'
    )
    if success and resp:
        correct_counts = resp.get('success_count') == 2 and resp.get('failure_count') == 5
        error_types = [f['error_type'] for f in resp.get('failure_items', [])]
        has_all_types = ('MISSING_REQUIRED' in error_types and 
                        'DUPLICATE_IN_FILE' in error_types and 
                        'DUPLICATE_IN_DB' in error_types)
        
        # 验证失败记录包含空描述错误
        has_empty_desc = any('描述' in f.get('error_message', '') for f in resp.get('failure_items', []))
        
        # 验证成功的样本确实存在于数据库
        success_items = resp.get('success_items', [])
        all_exist = True
        for item in success_items:
            status, sample = req('GET', f"/samples/{item['sample_id']}")
            if not sample or sample.get('sample_no') != item['sample_no']:
                all_exist = False
                break
        
        atomic_ok = correct_counts and has_all_types and all_exist and has_empty_desc
        results.append(atomic_ok)
        print(f'   计数正确(2成5败): {"✅" if correct_counts else "❌"}')
        print(f'   错误类型齐全: {"✅" if has_all_types else "❌"} {error_types}')
        print(f'   包含空描述错误: {"✅" if has_empty_desc else "❌"}')
        print(f'   成功样本均存在: {"✅" if all_exist else "❌"}')
        print(f'   结果: {"✅ 通过" if atomic_ok else "❌ 失败"}')
        
        mix_batch_id = resp.get('import_batch_id')
        mix_success_samples = [item['sample_no'] for item in success_items]
        mix_failed_samples = [f.get('sample_no', '') for f in resp.get('failure_items', []) if f.get('sample_no', '')]
    else:
        results.append(False)
        mix_batch_id = None
        mix_success_samples = []
        mix_failed_samples = []
    
    # ========== 八-新增：审计CSV不包含被拒绝样本 ==========
    print('\n' + '=' * 80)
    print('八-新增：审计CSV不包含被拒绝样本测试')
    print('=' * 80)
    
    if mix_batch_id and mix_success_samples and mix_failed_samples:
        status, audit_csv = req('GET', f"/export/import/{mix_batch_id}", parse_json=False)
        if status == 200 and audit_csv:
            # 成功样本应该在审计CSV中
            has_success = all(s in audit_csv for s in mix_success_samples)
            # 仅在失败列表中、不在成功列表中的样本（即完全被拒绝的样本）不应该出现在成功导入区
            # 注意：有些样本号可能同时在成功和失败列表中（如文件内重复：第一行成功，第二行失败）
            only_failed_samples = [s for s in mix_failed_samples if s and s not in mix_success_samples]
            # 先找到成功区的内容
            success_section = audit_csv.split('成功导入的样本')[1].split('导入失败记录')[0] if '成功导入的样本' in audit_csv and '导入失败记录' in audit_csv else ''
            no_rejected_in_success = all(s not in success_section for s in only_failed_samples)
            
            audit_clean_ok = has_success and no_rejected_in_success
            results.append(audit_clean_ok)
            print(f'   成功样本在审计CSV中: {"✅" if has_success else "❌"}')
            print(f'   仅失败样本不在成功区: {"✅" if no_rejected_in_success else "❌"}')
            print(f'   仅失败样本: {only_failed_samples}')
            print(f'   结果: {"✅ 通过" if audit_clean_ok else "❌ 失败"}')
            
            if not no_rejected_in_success:
                print(f'   所有失败样本: {mix_failed_samples}')
                print(f'   成功样本: {mix_success_samples}')
                print(f'   成功区内容: {success_section[:200]}...')
        else:
            results.append(False)
            print('   ❌ 导出导入审计失败')
    else:
        results.append(False)
        print('   ⚠️  跳过，无部分成功测试批次ID')
    
    # ========== 九、重启后一致性测试 ==========
    print('\n' + '=' * 80)
    print('九、重启后数据一致性测试')
    print('=' * 80)
    print('   请按以下步骤操作验证重启一致性：')
    print('   1. 记录上面测试中成功导入的样本号')
    print('   2. 重启后端服务（Ctrl+C 再重新运行）')
    print('   3. 重新运行本脚本，会自动检查这些样本是否存在')
    print()
    
    # 保存测试样本号供重启后验证（使用成功导入测试的样本）
    test_samples = test_samples_for_restart
    
    if os.path.exists('.import_test_samples.json'):
        print('   检测到之前的测试记录，进行重启后验证...')
        try:
            with open('.import_test_samples.json', 'r') as f:
                saved_samples = json.load(f)
            
            all_exist_after_restart = True
            all_registered_after_restart = True
            for sample_no, sample_id in saved_samples:
                status, sample = req('GET', f"/samples/{sample_id}")
                if not sample or sample.get('sample_no') != sample_no:
                    all_exist_after_restart = False
                    print(f'   ❌ 样本 {sample_no} 不存在')
                elif sample.get('current_state') != 'REGISTERED':
                    all_registered_after_restart = False
                    print(f'   ❌ 样本 {sample_no} 状态不是已登记')
                else:
                    print(f'   ✅ 样本 {sample_no} 存在，状态: {sample.get("current_state_name")}')
            
            restart_ok = all_exist_after_restart and all_registered_after_restart
            results.append(restart_ok)
            print(f'   重启后一致性: {"✅ 通过" if restart_ok else "❌ 失败"}')
            
            os.remove('.import_test_samples.json')
        except Exception as e:
            print(f'   ❌ 读取测试记录失败: {e}')
            results.append(False)
    else:
        if test_samples:
            with open('.import_test_samples.json', 'w') as f:
                json.dump(test_samples, f)
            print(f'   已保存 {len(test_samples)} 个测试样本到 .import_test_samples.json')
            print('   请重启后端服务后重新运行本脚本验证重启一致性')
        print('   本次跳过重启后验证（首次运行）')
    
    # ========== 十、列名别名支持测试 ==========
    print('\n' + '=' * 80)
    print('十、列名别名支持测试')
    print('=' * 80)
    
    alias_rows = [
        {'sample_no': f'IMP-ALIAS-{timestamp}-01', 'batch_no': f'BATCH-ALIAS-{timestamp}', 'sample_type': '血液样本', 'description': '英文字段名'},
        {'SampleNo': f'IMP-ALIAS-{timestamp}-02', 'BatchNo': f'BATCH-ALIAS-{timestamp}', 'SampleType': '尿液样本', 'Description': '驼峰字段名'},
    ]
    
    success, resp = test_case(
        '列名别名支持测试',
        200, 'POST', '/samples/import',
        data={'operator_id': 1, 'rows': alias_rows},
        desc='测试不同列名格式（中文、英文、驼峰）都能正确识别'
    )
    if success and resp:
        alias_ok = resp.get('success_count') == 2 and resp.get('failure_count') == 0
        results.append(alias_ok)
        print(f'   别名识别正确(2成功): {"✅ 通过" if alias_ok else "❌ 失败"}')
    else:
        results.append(False)
    
    # ========== 测试总结 ==========
    print('\n' + '=' * 80)
    print('测试总结')
    print('=' * 80)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'总测试用例: {total}')
    print(f'通过: {passed}')
    print(f'失败: {total - passed}')
    print(f'通过率: {passed/total*100:.1f}%')
    
    if passed == total:
        print('\n🎉 所有批量导入测试通过！')
    else:
        print(f'\n⚠️  {total - passed} 个测试失败，请检查。')
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
