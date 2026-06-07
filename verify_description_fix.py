import requests
import io

BASE_URL = 'http://localhost:5000/api'

print('=== 验证描述必填修复效果 ===\n')

all_passed = True

# 测试1: CSV缺描述列
print('测试1: CSV缺少描述列')
csv_content = '样本号,批次号,样本类型\nTEST-DESC-001,BATCH-TEST-001,血液样本\n'
files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
r = requests.post(BASE_URL + '/samples/import', data={'operator_id': 1}, files=files)
resp = r.json()
print(f'  状态码: {r.status_code}')
print(f'  成功: {resp.get("success_count")}, 失败: {resp.get("failure_count")}')
if resp.get('failure_items'):
    for f in resp['failure_items'][:2]:
        print(f'  错误: {f["error_message"]}')
test1_pass = resp.get('failure_count') == 1
print(f'  ✅ 描述缺失被正确拦截: {test1_pass}\n')
all_passed = all_passed and test1_pass

# 测试2: CSV空描述值
print('测试2: CSV空描述值')
csv_content = '样本号,批次号,样本类型,描述\nTEST-DESC-002,BATCH-TEST-002,血液样本,\n'
files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
r = requests.post(BASE_URL + '/samples/import', data={'operator_id': 1}, files=files)
resp = r.json()
print(f'  状态码: {r.status_code}')
print(f'  成功: {resp.get("success_count")}, 失败: {resp.get("failure_count")}')
if resp.get('failure_items'):
    for f in resp['failure_items'][:2]:
        print(f'  错误: {f["error_message"]}')
test2_pass = resp.get('failure_count') == 1
print(f'  ✅ 空描述被正确拦截: {test2_pass}\n')
all_passed = all_passed and test2_pass

# 测试3: JSON缺描述值
print('测试3: JSON缺描述值')
data = {
    'operator_id': 1,
    'rows': [
        {'样本号': 'TEST-DESC-003', '批次号': 'BATCH-TEST-003', '样本类型': '血液样本', '描述': ''}
    ]
}
r = requests.post(BASE_URL + '/samples/import', json=data)
resp = r.json()
print(f'  状态码: {r.status_code}')
print(f'  成功: {resp.get("success_count")}, 失败: {resp.get("failure_count")}')
if resp.get('failure_items'):
    for f in resp['failure_items'][:2]:
        print(f'  错误: {f["error_message"]}')
test3_pass = resp.get('failure_count') == 1
print(f'  ✅ JSON空描述被正确拦截: {test3_pass}\n')
all_passed = all_passed and test3_pass

# 测试4: JSON Description别名（大写D）
print('测试4: JSON使用Description别名（大写D）')
data = {
    'operator_id': 1,
    'rows': [
        {'sample_no': 'TEST-DESC-004', 'batch_no': 'BATCH-TEST-004', 'sample_type': '血液样本', 'Description': '正常样本带描述'}
    ]
}
r = requests.post(BASE_URL + '/samples/import', json=data)
resp = r.json()
print(f'  状态码: {r.status_code}')
print(f'  成功: {resp.get("success_count")}, 失败: {resp.get("failure_count")}')
test4_pass = resp.get('success_count') == 1
print(f'  ✅ Description别名正常识别: {test4_pass}\n')
all_passed = all_passed and test4_pass

# 测试5: 部分成功（缺描述不影响其他合法行）
print('测试5: 部分成功（缺描述不影响其他合法行）')
data = {
    'operator_id': 1,
    'rows': [
        {'样本号': 'TEST-DESC-005', '批次号': 'BATCH-TEST-005', '样本类型': '血液样本', '描述': '成功样本1'},
        {'样本号': 'TEST-DESC-006', '批次号': 'BATCH-TEST-005', '样本类型': '尿液样本', '描述': ''},  # 失败
        {'样本号': 'TEST-DESC-007', '批次号': 'BATCH-TEST-005', '样本类型': '粪便样本', '描述': '成功样本2'},
    ]
}
r = requests.post(BASE_URL + '/samples/import', json=data)
resp = r.json()
print(f'  状态码: {r.status_code}')
print(f'  成功: {resp.get("success_count")}, 失败: {resp.get("failure_count")}')
success_count = resp.get('success_count', 0)
failure_count = resp.get('failure_count', 0)
test5_pass = success_count == 2 and failure_count == 1
print(f'  ✅ 部分成功验证（2成功1失败）: {test5_pass}')

success_nos = [item['sample_no'] for item in resp.get('success_items', [])]
failed_nos = [f.get('sample_no') for f in resp.get('failure_items', [])]
print(f'  成功样本: {success_nos}')
print(f'  失败样本: {failed_nos}')

# 验证审计CSV不包含被拒绝样本
print(f'\n  验证审计CSV不包含被拒绝样本...')
batch_id = resp.get('import_batch_id')
test6_pass = False
if batch_id:
    r_export = requests.get(BASE_URL + f'/export/import/{batch_id}')
    csv_text = r_export.text
    success_section = csv_text.split('成功导入的样本')[1].split('导入失败记录')[0] if '成功导入的样本' in csv_text and '导入失败记录' in csv_text else ''
    failed_in_success = 'TEST-DESC-006' in success_section
    test6_pass = not failed_in_success
    print(f'  审计CSV成功区不含失败样本(TEST-DESC-006): {test6_pass}')
    if failed_in_success:
        print(f'  成功区内容预览: {success_section[:200]}')

all_passed = all_passed and test5_pass and test6_pass

print(f'\n=== 验证结果 ===')
print(f'  测试1 (CSV缺描述列): {"✅ 通过" if test1_pass else "❌ 失败"}')
print(f'  测试2 (CSV空描述值): {"✅ 通过" if test2_pass else "❌ 失败"}')
print(f'  测试3 (JSON空描述值): {"✅ 通过" if test3_pass else "❌ 失败"}')
print(f'  测试4 (Description别名): {"✅ 通过" if test4_pass else "❌ 失败"}')
print(f'  测试5 (部分成功原子性): {"✅ 通过" if test5_pass else "❌ 失败"}')
print(f'  测试6 (审计CSV不包含被拒绝样本): {"✅ 通过" if test6_pass else "❌ 失败"}')
print(f'\n  综合结果: {"🎉 所有验证测试通过！" if all_passed else "⚠️  部分测试失败"}')
