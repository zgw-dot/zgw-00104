"""
README 示例回归检查脚本
验证 README 文档中的所有 API 示例与真实接口行为一致
"""
import requests
import io
import sys

BASE_URL = 'http://localhost:5000/api'
TIMESTAMP = None

def get_timestamp():
    global TIMESTAMP
    if TIMESTAMP is None:
        import time
        TIMESTAMP = str(int(time.time()))
    return TIMESTAMP

def check(condition, test_name, details=""):
    """检查条件，打印结果并返回是否通过"""
    icon = "✅" if condition else "❌"
    print(f"  {icon} {test_name}: {'通过' if condition else '失败'}")
    if details and not condition:
        print(f"     详情: {details}")
    return condition

def main():
    print("=" * 80)
    print("README 示例回归检查")
    print("=" * 80)
    print()

    all_passed = True
    ts = get_timestamp()

    # =====================================================================
    # 测试 1: CSV 文件上传 - README 示例
    # =====================================================================
    print("【测试 1】POST /api/samples/import - CSV 上传（README 示例）")
    print("-" * 80)
    
    csv_content = f"""样本号,批次号,样本类型,描述
RTEST-{ts}-01,BATCH-RTEST-{ts},血液样本,常规体检
RTEST-{ts}-02,BATCH-RTEST-{ts},尿液样本,入职体检"""

    files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
    data = {'operator_id': 1}
    
    try:
        r = requests.post(f'{BASE_URL}/samples/import', data=data, files=files, timeout=10)
        resp = r.json()
        
        print(f"  状态码: {r.status_code}")
        
        t1 = check(r.status_code == 200, "状态码为 200", f"实际: {r.status_code}")
        t2 = check(resp.get('success_count') == 2, "success_count == 2", f"实际: {resp.get('success_count')}")
        t3 = check(resp.get('failure_count') == 0, "failure_count == 0", f"实际: {resp.get('failure_count')}")
        t4 = check('import_batch_id' in resp, "包含 import_batch_id 字段")
        t5 = check('success_items' in resp, "包含 success_items 字段")
        t6 = check('message' in resp, "包含 message 字段")
        
        if resp.get('success_items'):
            item = resp['success_items'][0]
            t7 = check('sample_id' in item, "success_items 包含 sample_id 字段")
            t8 = check('sample_no' in item, "success_items 包含 sample_no 字段")
            t9 = check('batch_no' in item, "success_items 包含 batch_no 字段")
            t10 = check('sample_type' in item, "success_items 包含 sample_type 字段")
            t11 = check('description' in item, "success_items 包含 description 字段")
            t12 = check(item['description'] == '常规体检', "description 字段值正确", f"实际: {item.get('description')}")
        else:
            t7 = t8 = t9 = t10 = t11 = t12 = False
            print("  ❌ success_items 为空")
        
        csv_batch_id = resp.get('import_batch_id')
        all_passed = all_passed and all([t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12])
        
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        all_passed = False
        csv_batch_id = None
    
    print()

    # =====================================================================
    # 测试 2: CSV 缺描述列 - 应失败
    # =====================================================================
    print("【测试 2】POST /api/samples/import - CSV 缺描述列（README 重要提示验证）")
    print("-" * 80)
    
    csv_no_desc = f"""样本号,批次号,样本类型
RTEST-{ts}-03,BATCH-RTEST-{ts},血液样本"""

    files = {'file': ('test.csv', io.BytesIO(csv_no_desc.encode('utf-8')), 'text/csv')}
    data = {'operator_id': 1}
    
    try:
        r = requests.post(f'{BASE_URL}/samples/import', data=data, files=files, timeout=10)
        resp = r.json()
        
        print(f"  状态码: {r.status_code}")
        print(f"  成功: {resp.get('success_count')}, 失败: {resp.get('failure_count')}")
        
        t1 = check(resp.get('success_count') == 0, "success_count == 0（缺描述不创建样本）", f"实际: {resp.get('success_count')}")
        t2 = check(resp.get('failure_count') == 1, "failure_count == 1", f"实际: {resp.get('failure_count')}")
        
        has_desc_error = False
        if resp.get('failure_items'):
            for f in resp['failure_items']:
                if '描述' in f.get('error_message', '') and f.get('error_type') == 'MISSING_REQUIRED':
                    has_desc_error = True
                    print(f"  错误信息: {f['error_message']}")
                    print(f"  错误类型: {f['error_type']}")
        
        t3 = check(has_desc_error, "包含描述缺失错误（MISSING_REQUIRED）")
        
        all_passed = all_passed and all([t1, t2, t3])
        
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        all_passed = False
    
    print()

    # =====================================================================
    # 测试 3: JSON API - README 示例
    # =====================================================================
    print("【测试 3】POST /api/samples/import - JSON API（README 示例）")
    print("-" * 80)
    
    data = {
        "operator_id": 1,
        "rows": [
            {
                "样本号": f"RTEST-{ts}-04",
                "批次号": f"BATCH-RTEST-{ts}",
                "样本类型": "血液样本",
                "描述": "常规体检"
            },
            {
                "sample_no": f"RTEST-{ts}-05",
                "batch_no": f"BATCH-RTEST-{ts}",
                "sample_type": "尿液样本",
                "Description": "入职体检"
            }
        ]
    }
    
    try:
        r = requests.post(f'{BASE_URL}/samples/import', json=data, timeout=10)
        resp = r.json()
        
        print(f"  状态码: {r.status_code}")
        print(f"  成功: {resp.get('success_count')}, 失败: {resp.get('failure_count')}")
        
        t1 = check(r.status_code == 200, "状态码为 200")
        t2 = check(resp.get('success_count') == 2, "success_count == 2", f"实际: {resp.get('success_count')}")
        t3 = check(resp.get('failure_count') == 0, "failure_count == 0", f"实际: {resp.get('failure_count')}")
        
        # 验证 Description 别名正确识别
        if resp.get('success_items'):
            desc_item = None
            for item in resp['success_items']:
                if item['sample_no'] == f"RTEST-{ts}-05":
                    desc_item = item
                    break
            if desc_item:
                t4 = check(desc_item['description'] == '入职体检', "Description 别名正确识别", f"实际: {desc_item.get('description')}")
            else:
                t4 = False
                print("  ❌ 未找到样本 RTEST-05")
        else:
            t4 = False
        
        json_batch_id = resp.get('import_batch_id')
        all_passed = all_passed and all([t1, t2, t3, t4])
        
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        all_passed = False
        json_batch_id = None
    
    print()

    # =====================================================================
    # 测试 4: JSON 缺描述值 - 应失败
    # =====================================================================
    print("【测试 4】POST /api/samples/import - JSON 缺描述值（README 重要提示验证）")
    print("-" * 80)
    
    data = {
        "operator_id": 1,
        "rows": [
            {"样本号": f"RTEST-{ts}-06", "批次号": f"BATCH-RTEST-{ts}", "样本类型": "血液样本", "描述": ""}
        ]
    }
    
    try:
        r = requests.post(f'{BASE_URL}/samples/import', json=data, timeout=10)
        resp = r.json()
        
        print(f"  状态码: {r.status_code}")
        print(f"  成功: {resp.get('success_count')}, 失败: {resp.get('failure_count')}")
        
        t1 = check(resp.get('success_count') == 0, "success_count == 0（空描述不创建样本）", f"实际: {resp.get('success_count')}")
        t2 = check(resp.get('failure_count') == 1, "failure_count == 1", f"实际: {resp.get('failure_count')}")
        
        has_desc_error = False
        if resp.get('failure_items'):
            for f in resp['failure_items']:
                if '描述' in f.get('error_message', ''):
                    has_desc_error = True
                    print(f"  错误信息: {f['error_message']}")
        
        t3 = check(has_desc_error, "包含描述缺失错误")
        
        all_passed = all_passed and all([t1, t2, t3])
        
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        all_passed = False
    
    print()

    # =====================================================================
    # 测试 5: 部分成功 - README 示例
    # =====================================================================
    print("【测试 5】POST /api/samples/import - 部分成功（README 示例验证）")
    print("-" * 80)
    
    data = {
        "operator_id": 1,
        "rows": [
            {"样本号": f"RTEST-{ts}-07", "批次号": f"BATCH-RTEST-{ts}", "样本类型": "血液样本", "描述": "常规体检"},
            {"样本号": f"RTEST-{ts}-08", "批次号": f"BATCH-RTEST-{ts}", "样本类型": "尿液样本", "描述": ""},  # 失败
            {"样本号": f"RTEST-{ts}-09", "批次号": f"BATCH-RTEST-{ts}", "样本类型": "粪便样本", "描述": "入职体检"},
        ]
    }
    
    try:
        r = requests.post(f'{BASE_URL}/samples/import', json=data, timeout=10)
        resp = r.json()
        
        print(f"  状态码: {r.status_code}")
        print(f"  成功: {resp.get('success_count')}, 失败: {resp.get('failure_count')}")
        print(f"  成功样本: {[item['sample_no'] for item in resp.get('success_items', [])]}")
        print(f"  失败样本: {[f.get('sample_no') for f in resp.get('failure_items', [])]}")
        
        t1 = check(resp.get('success_count') == 2, "success_count == 2（2个合法行成功）", f"实际: {resp.get('success_count')}")
        t2 = check(resp.get('failure_count') == 1, "failure_count == 1（1个缺描述行失败）", f"实际: {resp.get('failure_count')}")
        t3 = check(f"RTEST-{ts}-07" in [item['sample_no'] for item in resp.get('success_items', [])], "RTEST-07 成功创建")
        t4 = check(f"RTEST-{ts}-09" in [item['sample_no'] for item in resp.get('success_items', [])], "RTEST-09 成功创建")
        t5 = check(f"RTEST-{ts}-08" in [f.get('sample_no') for f in resp.get('failure_items', [])], "RTEST-08 进入失败明细")
        
        partial_batch_id = resp.get('import_batch_id')
        all_passed = all_passed and all([t1, t2, t3, t4, t5])
        
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        all_passed = False
        partial_batch_id = None
    
    print()

    # =====================================================================
    # 测试 6: GET /api/import/failures - README 示例
    # =====================================================================
    print("【测试 6】GET /api/import/failures - 查询失败记录（README 示例）")
    print("-" * 80)
    
    if partial_batch_id:
        try:
            r = requests.get(f'{BASE_URL}/import/failures', params={'batch_id': partial_batch_id}, timeout=10)
            failures = r.json()
            
            print(f"  状态码: {r.status_code}")
            print(f"  失败记录数: {len(failures) if isinstance(failures, list) else 0}")
            
            t1 = check(r.status_code == 200, "状态码为 200")
            t2 = check(isinstance(failures, list), "返回列表类型")
            t3 = check(len(failures) >= 1, "至少返回1条失败记录")
            
            if failures and isinstance(failures, list) and len(failures) > 0:
                f = failures[0]
                t4 = check('id' in f, "包含 id 字段")
                t5 = check('import_batch_id' in f, "包含 import_batch_id 字段")
                t6 = check('error_type' in f, "包含 error_type 字段")
                t7 = check('error_message' in f, "包含 error_message 字段")
                t8 = check(f['error_type'] == 'MISSING_REQUIRED', "error_type 为 MISSING_REQUIRED", f"实际: {f.get('error_type')}")
                t9 = check('描述' in f.get('error_message', ''), "error_message 包含描述", f"实际: {f.get('error_message')}")
            else:
                t4 = t5 = t6 = t7 = t8 = t9 = False
            
            all_passed = all_passed and all([t1, t2, t3, t4, t5, t6, t7, t8, t9])
            
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
            all_passed = False
    else:
        print("  ⚠️  跳过（无批次ID）")
    
    print()

    # =====================================================================
    # 测试 7: GET /api/export/import/<batch_id> - README 示例
    # =====================================================================
    print("【测试 7】GET /api/export/import/<batch_id> - 审计CSV导出（README 示例）")
    print("-" * 80)
    
    if partial_batch_id:
        try:
            r = requests.get(f'{BASE_URL}/export/import/{partial_batch_id}', timeout=10)
            csv_text = r.text
            
            print(f"  状态码: {r.status_code}")
            print(f"  CSV 预览（前300字符）: {csv_text[:300]}...")
            
            t1 = check(r.status_code == 200, "状态码为 200")
            t2 = check('批量导入结果审计' in csv_text, "CSV 包含标题")
            t3 = check(partial_batch_id in csv_text, "CSV 包含批次号")
            t4 = check('成功导入的样本' in csv_text, "CSV 包含成功区")
            t5 = check('导入失败记录' in csv_text, "CSV 包含失败区")
            
            # 验证失败样本不在成功区
            success_section = csv_text.split('成功导入的样本')[1].split('导入失败记录')[0] if '成功导入的样本' in csv_text and '导入失败记录' in csv_text else ''
            failed_in_success = f"RTEST-{ts}-08" in success_section
            t6 = check(not failed_in_success, "失败样本（RTEST-08）不在成功区（不污染审计CSV）", 
                       f"失败样本出现在成功区: {success_section[:200]}")
            
            # 验证成功样本在成功区
            success_in_success = f"RTEST-{ts}-07" in success_section and f"RTEST-{ts}-09" in success_section
            t7 = check(success_in_success, "成功样本（RTEST-07、RTEST-09）在成功区")
            
            all_passed = all_passed and all([t1, t2, t3, t4, t5, t6, t7])
            
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
            all_passed = False
    else:
        print("  ⚠️  跳过（无批次ID）")
    
    print()

    # =====================================================================
    # 测试 8: 返回示例验证 - README 返回示例
    # =====================================================================
    print("【测试 8】返回结构验证 - README 返回示例字段对比")
    print("-" * 80)
    
    data = {
        "operator_id": 1,
        "rows": [
            {"样本号": f"RTEST-{ts}-10", "批次号": f"BATCH-RTEST-{ts}", "样本类型": "血液样本", "描述": "正常样本"},
            {"样本号": f"RTEST-{ts}-11", "批次号": f"BATCH-RTEST-{ts}", "样本类型": "尿液样本", "描述": ""},
        ]
    }
    
    try:
        r = requests.post(f'{BASE_URL}/samples/import', json=data, timeout=10)
        resp = r.json()
        
        # 验证成功项字段
        success_fields = ['sample_id', 'sample_no', 'batch_no', 'sample_type', 'description']
        if resp.get('success_items'):
            item = resp['success_items'][0]
            success_field_checks = [check(field in item, f"success_items 包含 {field} 字段") for field in success_fields]
        else:
            success_field_checks = [False]
            print("  ❌ 无 success_items")
        
        # 验证失败项字段
        failure_fields = ['error_type', 'error_message', 'row_number', 'sample_no', 'batch_no', 'sample_type', 'description']
        if resp.get('failure_items'):
            f = resp['failure_items'][0]
            failure_field_checks = [check(field in f, f"failure_items 包含 {field} 字段") for field in failure_fields]
        else:
            failure_field_checks = [False]
            print("  ❌ 无 failure_items")
        
        # 验证根级字段
        root_fields = ['success_count', 'failure_count', 'import_batch_id', 'success_items', 'failure_items', 'message']
        root_field_checks = [check(field in resp, f"根级包含 {field} 字段") for field in root_fields]
        
        all_passed = all_passed and all(success_field_checks + failure_field_checks + root_field_checks)
        
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
        all_passed = False
    
    print()

    # =====================================================================
    # 总结
    # =====================================================================
    print("=" * 80)
    print("回归检查总结")
    print("=" * 80)
    
    if all_passed:
        print("✅ 所有 README 示例与真实接口行为一致！")
        print()
        print("验证证据：")
        print("  1. CSV 上传示例返回字段与文档一致")
        print("  2. CSV 缺描述列仅进入失败明细，不创建样本")
        print("  3. JSON API 示例返回字段与文档一致")
        print("  4. JSON 空描述值仅进入失败明细，不创建样本")
        print("  5. 部分成功场景：合法行成功，缺描述行失败，成功不丢失")
        print("  6. 失败查询接口返回字段与文档一致")
        print("  7. 审计CSV不包含被拒绝样本，不污染审计结果")
        print("  8. 所有返回字段（success_items、failure_items）与文档一致")
        print("  9. Description 别名正确识别")
        print("  10. 错误类型（MISSING_REQUIRED）与文档一致")
        print()
        return 0
    else:
        print("❌ 部分 README 示例与真实接口不一致，请检查！")
        return 1

if __name__ == '__main__':
    sys.exit(main())
