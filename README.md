# 实验室样本流转工作台

一个完整的实验室样本全生命周期管理系统，包含前端界面、后端 API 和 SQLite 持久化存储。

## ✨ 功能特性

### 主流程
- **样本登记**：录入样本编号、批次号、样本类型和描述信息
- **批次接收**：按批次批量接收已登记的样本
- **检测**：将已接收样本推进到检测状态
- **复核**：检测完成后提交复核
- **归档**：复核通过后完成归档
- **驳回**：复核不通过可驳回，样本可重新登记

### 失败路径拦截
- ✅ **重复样本号拦截**：样本号唯一约束，数据库层面 + 业务层面双重校验
- ✅ **跳级归档拦截**：只有复核中的样本才能归档，直接调用 API 也无法绕过
- ✅ **空原因驳回拦截**：驳回必须填写原因
- ✅ **越权作废拦截**：只有管理员可以作废样本
- ✅ **越权撤销拦截**：只有管理员可以撤销操作
- ✅ **状态流转校验**：严格遵循状态机，非法状态转换自动拦截

### 持久化与审计
- ✅ **重启状态保留**：SQLite 持久化，服务重启后状态完整保留
- ✅ **事件溯源**：所有操作都记录事件，永不删除
- ✅ **撤销不删除**：撤销操作新增更正事件，旧事件完整保留，可追溯
- ✅ **审计导出**：支持按样本号或批次号导出 CSV 格式审计文件
- ✅ **导出一致性**：导出文件与界面时间线完全一致

### 批量导入
- ✅ **批量导入样本**：支持 CSV 文件上传和 JSON API 两种方式批量导入待登记样本
- ✅ **统一必填校验**：样本号、批次号、样本类型、描述均为必填列，缺描述行仅进入失败明细，不创建样本
- ✅ **冲突处理**：同一文件内重复样本号、数据库已存在样本号、缺少必填列都给出清楚的失败明细
- ✅ **原子性保证**：成功记录不因其他行失败而丢失，每行独立处理
- ✅ **权限控制**：只有有登记权限的用户能导入，越权请求被后端拦截
- ✅ **失败持久化**：所有失败记录持久化存储，可按批次查询核对
- ✅ **审计导出**：导入结果可导出 CSV 审计文件，不包含被拒绝样本

### 界面特性
- 📊 **待处理统计**：实时显示待处理总数和异常驳回数量
- 🔍 **多维度筛选**：按批次号、状态筛选待处理样本
- ⏱️ **时间线展示**：完整展示每次操作的操作者、角色、原因和状态变化
- 👤 **角色操作对照**：切换不同角色账号，可操作按钮动态变化
- ⚠️ **异常原因入口**：已驳回样本直接显示异常原因查看入口
- 📝 **处理清单**：完整的样本列表，显示最近处理人、处理时间

### 撤销机制
- 撤销操作**不会删除旧事件**
- 新增一条标记为"更正"的事件
- 关联被撤销的事件 ID
- 样本状态恢复到上一个合法状态
- 更正事件在时间线中特殊标记显示

## 🏗️ 项目结构

```
zgw-00104/
├── backend/
│   ├── app.py              # Flask API 主程序
│   ├── database.py         # 数据库配置和核心函数
│   ├── init_db.py          # 数据库初始化和示例数据
│   └── requirements.txt    # Python 依赖
├── frontend/
│   ├── index.html          # 主页面
│   ├── css/
│   │   └── style.css       # 样式文件
│   └── js/
│       └── app.js          # 前端逻辑
├── data/
│   └── samples.db          # SQLite 数据库（运行时创建）
└── README.md               # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

这将创建数据库、用户表、样本表、事件表，并插入示例数据。

### 3. 启动后端服务

```bash
python app.py
```

后端服务将在 `http://localhost:5000` 启动。

### 4. 打开前端界面

直接用浏览器打开 `frontend/index.html` 文件。

## 👥 测试账号

初始化后包含以下用户（通过页面右上角切换模拟登录）：

| ID  | 用户名   | 姓名   | 角色     | 权限说明               |
|-----|----------|--------|----------|------------------------|
| 1   | admin    | 系统管理员 | admin    | 所有操作权限，包括撤销 |
| 2   | zhangsan | 张三   | operator | 登记、接收、检测       |
| 3   | lisi     | 李四   | operator | 登记、接收、检测       |
| 4   | wangwu   | 王五   | reviewer | 登记、接收、检测、复核、驳回、归档 |
| 5   | zhaoliu  | 赵六   | reviewer | 登记、接收、检测、复核、驳回、归档 |

## 🔄 状态流转图

```
已登记(REGISTERED)
    ↓
已接收(RECEIVED) → 驳回(REJECTED) → 重新登记 → 已登记
    ↓
检测中(TESTING) → 驳回(REJECTED)
    ↓
复核中(REVIEWING) → 驳回(REJECTED)
    ↓
已归档(ARCHIVED)

* 所有非终态都可被管理员作废(CANCELLED)
* 所有非初态/终态都可被管理员撤销(UNDO)
```

## 📡 API 文档

### 基础路径
`http://localhost:5000/api`

### 用户接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/users` | 获取所有用户列表 |
| GET | `/users/<id>` | 获取单个用户信息 |
| GET | `/permissions/<user_id>` | 获取用户权限 |

### 样本接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/samples` | 获取样本列表（支持 batch_no/state/pending 参数筛选） |
| GET | `/samples/stats` | 获取统计信息 |
| GET | `/samples/<id>` | 获取样本详情（含事件列表） |
| GET | `/samples/<sample_no>/exists` | 检查样本号是否存在 |
| POST | `/samples` | 登记新样本 |
| POST | `/samples/<id>/test` | 开始检测 |
| POST | `/samples/<id>/review` | 提交复核 |
| POST | `/samples/<id>/reject` | 驳回 |
| POST | `/samples/<id>/archive` | 归档 |
| POST | `/samples/<id>/cancel` | 作废 |
| POST | `/samples/<id>/undo` | 撤销上一步 |
| POST | `/samples/<id>/re-register` | 重新登记 |

### 批量导入接口
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/samples/import` | 批量导入待登记样本（支持CSV上传和JSON） |
| GET | `/import/failures` | 查询导入失败记录（按批次筛选） |
| GET | `/export/import/<batch_id>` | 导出导入结果审计 CSV |

### 批次接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/batches` | 获取所有批次列表 |
| POST | `/batches/receive` | 按批次接收 |

### 导出接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/export/sample/<sample_no>` | 导出样本审计 CSV |
| GET | `/export/batch/<batch_no>` | 导出批次审计 CSV |

### 元数据接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/roles` | 获取角色列表 |
| GET | `/states` | 获取状态列表 |
| GET | `/transitions` | 获取状态流转规则 |

## 📦 批量导入 API 详解

### 概述
批量导入功能支持两种方式：**CSV 文件上传** 和 **JSON API 调用**。导入成功后样本进入「已登记」状态，并自动写入登记事件（含导入批次号）。

> **重要提示**：样本号、批次号、样本类型、描述**均为必填列**。缺描述或缺列的行只会进入失败明细，不会创建样本，也不会污染审计 CSV。同批次中其他合法行仍会正常成功。

---

### 1. POST `/api/samples/import` - 批量导入样本

**用途**：批量导入待登记样本，支持 CSV 文件上传和 JSON 数据两种方式。

**权限**：需要 `register` 权限（admin / operator / reviewer）

#### 方式一：CSV 文件上传

**Content-Type**：`multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | CSV 文件 |
| `operator_id` | Integer | ✅ | 操作员用户ID |

**CSV 格式要求**：
```csv
样本号,批次号,样本类型,描述
S100,BATCH-2026-004,血液样本,常规体检样本
S101,BATCH-2026-004,尿液样本,入职体检样本
```

**支持的列名别名**（大小写不敏感）：
| 列名 | 别名 |
|------|------|
| 样本号 | `sample_no`, `sampleNo` |
| 批次号 | `batch_no`, `batchNo` |
| 样本类型 | `sample_type`, `sampleType` |
| 描述 | `description`, `Description` |

**Curl 示例**：
```bash
curl -X POST http://localhost:5000/api/samples/import \
  -F "operator_id=1" \
  -F "file=@samples.csv"
```

**Python requests 示例**：
```python
import requests
import io

csv_content = '''样本号,批次号,样本类型,描述
TEST-001,BATCH-TEST-001,血液样本,常规体检
TEST-002,BATCH-TEST-001,尿液样本,入职体检'''

files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
data = {'operator_id': 1}
r = requests.post('http://localhost:5000/api/samples/import', data=data, files=files)
print(r.json())
```

#### 方式二：JSON API

**Content-Type**：`application/json`

**请求体**：
```json
{
  "operator_id": 1,
  "rows": [
    {
      "样本号": "TEST-001",
      "批次号": "BATCH-TEST-001",
      "样本类型": "血液样本",
      "描述": "常规体检"
    },
    {
      "sample_no": "TEST-002",
      "batch_no": "BATCH-TEST-001",
      "sample_type": "尿液样本",
      "Description": "入职体检"
    }
  ]
}
```

**Curl 示例**：
```bash
curl -X POST http://localhost:5000/api/samples/import \
  -H "Content-Type: application/json" \
  -d '{
    "operator_id": 1,
    "rows": [
      {"样本号": "TEST-001", "批次号": "BATCH-TEST-001", "样本类型": "血液样本", "描述": "常规体检"},
      {"样本号": "TEST-002", "批次号": "BATCH-TEST-001", "样本类型": "尿液样本", "描述": ""}
    ]
  }'
```

**Python requests 示例**：
```python
import requests

data = {
    "operator_id": 1,
    "rows": [
        {"样本号": "TEST-001", "批次号": "BATCH-TEST-001", "样本类型": "血液样本", "描述": "常规体检"},
        {"样本号": "TEST-002", "批次号": "BATCH-TEST-001", "样本类型": "尿液样本", "描述": ""}
    ]
}
r = requests.post('http://localhost:5000/api/samples/import', json=data)
print(r.json())
```

#### 返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `success_count` | Integer | 成功导入的样本数量 |
| `failure_count` | Integer | 失败的行数量 |
| `import_batch_id` | String | 导入批次号（用于后续查询和导出） |
| `success_items` | Array | 成功导入的样本列表 |
| `success_items[].sample_id` | Integer | 样本ID |
| `success_items[].sample_no` | String | 样本号 |
| `success_items[].batch_no` | String | 批次号 |
| `success_items[].sample_type` | String | 样本类型 |
| `success_items[].description` | String | 描述 |
| `failure_items` | Array | 失败记录列表 |
| `failure_items[].error_type` | String | 错误类型 |
| `failure_items[].error_message` | String | 错误详情 |
| `failure_items[].row_number` | Integer | 行号（从2开始，第1行为表头） |
| `failure_items[].sample_no` | String | 样本号（如果有） |
| `message` | String | 结果摘要 |

#### 失败明细错误类型

| `error_type` | 说明 |
|--------------|------|
| `MISSING_REQUIRED` | 缺少必填列或值为空（包括空样本号、空批次号、空样本类型、空描述） |
| `DUPLICATE_IN_FILE` | 同一文件内重复样本号（第一条成功，后续重复的失败） |
| `DUPLICATE_IN_DB` | 数据库中已存在该样本号 |

#### 返回示例（部分成功）

```json
{
  "success_count": 1,
  "failure_count": 1,
  "import_batch_id": "IMP-20260607210445-ABC123",
  "success_items": [
    {
      "sample_id": 16,
      "sample_no": "TEST-001",
      "batch_no": "BATCH-TEST-001",
      "sample_type": "血液样本",
      "description": "常规体检"
    }
  ],
  "failure_items": [
    {
      "error_type": "MISSING_REQUIRED",
      "error_message": "缺少必填列或值为空: 描述",
      "row_number": 3,
      "sample_no": "TEST-002",
      "batch_no": "BATCH-TEST-001",
      "sample_type": "尿液样本",
      "description": ""
    }
  ],
  "message": "导入完成：成功 1 条，失败 1 条"
}
```

---

### 2. GET `/api/import/failures` - 查询导入失败记录

**用途**：按批次查询导入失败记录，用于核对和后续处理。

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `batch_id` | String | ❌ | 导入批次号（不传则返回所有失败记录） |

**Curl 示例**：
```bash
curl "http://localhost:5000/api/import/failures?batch_id=IMP-20260607210445-ABC123"
```

**Python requests 示例**：
```python
import requests
r = requests.get('http://localhost:5000/api/import/failures', 
                 params={'batch_id': 'IMP-20260607210445-ABC123'})
print(r.json())
```

**返回字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 失败记录ID |
| `import_batch_id` | String | 导入批次号 |
| `row_number` | Integer | 行号 |
| `sample_no` | String | 样本号 |
| `batch_no` | String | 批次号 |
| `sample_type` | String | 样本类型 |
| `description` | String | 描述 |
| `error_type` | String | 错误类型 |
| `error_message` | String | 错误详情 |
| `operator_id` | Integer | 操作员ID |
| `created_at` | String | 创建时间 |

---

### 3. GET `/api/export/import/<batch_id>` - 导出导入结果审计 CSV

**用途**：导出指定批次的导入结果审计文件，包含成功导入的样本和失败记录。

> **重要**：审计 CSV 的「成功导入的样本」区域**仅包含实际创建成功的样本**，因缺描述等原因被拒绝的样本不会出现在成功区，不会污染审计结果。

**路径参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `batch_id` | String | ✅ | 导入批次号 |

**Curl 示例**：
```bash
curl "http://localhost:5000/api/export/import/IMP-20260607210445-ABC123" \
  -o import_audit.csv
```

**Python requests 示例**：
```python
import requests
r = requests.get('http://localhost:5000/api/export/import/IMP-20260607210445-ABC123')
with open('import_audit.csv', 'w', encoding='utf-8-sig') as f:
    f.write(r.text)
```

**导出文件格式**：
```csv
批量导入结果审计
导入批次号,IMP-20260607210445-ABC123
导入时间,2026-06-07 21:04:45
操作员,系统管理员

=== 成功导入的样本 ===
样本ID,样本号,批次号,样本类型,描述,登记人,登记时间
16,TEST-001,BATCH-TEST-001,血液样本,常规体检,系统管理员,2026-06-07 21:04:45

=== 导入失败记录 ===
行号,样本号,批次号,样本类型,描述,错误类型,错误信息
3,TEST-002,BATCH-TEST-001,尿液样本,,MISSING_REQUIRED,缺少必填列或值为空: 描述
```

---

## 📊 示例数据说明

初始化后包含 8 个样本，覆盖所有主要场景：

| 样本号 | 批次号 | 当前状态 | 说明 |
|--------|--------|----------|------|
| S001 | BATCH-2026-001 | 已归档 | 完整正常流程示例 |
| S002 | BATCH-2026-001 | 已驳回 | 驳回场景示例，原因：检测结果异常 |
| S003 | BATCH-2026-001 | 检测中 | 撤销更正示例（复核→撤销→回到检测中） |
| S004 | BATCH-2026-002 | 复核中 | 待归档 |
| S005 | BATCH-2026-002 | 已接收 | 待检测 |
| S006 | BATCH-2026-002 | 已登记 | 待接收 |
| S007 | BATCH-2026-003 | 已作废 | 作废场景示例 |
| S008 | BATCH-2026-003 | 已登记 | 待接收 |

## 🔒 权限矩阵

| 操作 | admin | operator | reviewer |
|------|-------|----------|----------|
| 登记样本 | ✅ | ✅ | ✅ |
| 接收样本 | ✅ | ✅ | ✅ |
| 开始检测 | ✅ | ✅ | ✅ |
| 提交复核 | ✅ | ❌ | ✅ |
| 驳回样本 | ✅ | ❌ | ✅ |
| 归档样本 | ✅ | ❌ | ✅ |
| 作废样本 | ✅ | ❌ | ❌ |
| 撤销更正 | ✅ | ❌ | ❌ |

## 🧪 测试场景建议

### 基础功能测试
1. **重复样本号测试**：尝试登记 S001，应被拦截
2. **跳级归档测试**：用普通操作员账号尝试归档，或直接调用 API 对非复核中样本归档
3. **空原因驳回测试**：尝试不填原因驳回
4. **越权测试**：用普通操作员账号尝试作废/撤销
5. **角色切换测试**：切换不同账号，观察可用按钮变化
6. **撤销测试**：用管理员对 S004 撤销，观察时间线新增更正事件
7. **审计导出测试**：导出 S003 审计文件，验证与界面时间线一致
8. **重启验证**：停止服务后重启，验证状态完整保留
9. **直接调 API 测试**：使用 curl/postman 尝试越权操作，验证后端拦截

### 批量导入测试
10. **缺描述 CSV 导入测试**：上传缺描述列或空描述的 CSV，验证仅进入失败明细，不创建样本
11. **缺描述 JSON 导入测试**：调用 JSON API 传入缺描述的 rows，验证被拦截
12. **部分成功测试**：同时导入合法行和缺描述行，验证合法行成功、缺描述行失败
13. **失败查询测试**：按批次查询导入失败记录，验证持久化存储
14. **审计 CSV 纯净性测试**：导出导入结果审计，验证失败样本不出现在成功区
15. **越权导入测试**：用无 register 权限的用户尝试导入，验证被拦截
16. **列名别名测试**：使用 Description、description 等别名，验证正确识别

## 🛠️ 技术栈

- **后端**：Python 3 + Flask + Flask-CORS
- **数据库**：SQLite 3（文件型，无需额外服务）
- **前端**：原生 HTML5 + CSS3 + JavaScript（ES6+）
- **数据格式**：JSON（API）、CSV（导出）

## 📝 数据库设计

### users 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 用户ID |
| username | TEXT UNIQUE | 用户名 |
| role | TEXT | 角色：admin/operator/reviewer |
| name | TEXT | 真实姓名 |
| created_at | TEXT | 创建时间 |

### samples 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 样本ID |
| sample_no | TEXT UNIQUE | 样本编号（唯一） |
| batch_no | TEXT | 批次号 |
| sample_type | TEXT | 样本类型 |
| description | TEXT | 描述 |
| current_state | TEXT | 当前状态 |
| registered_by | INTEGER FK | 登记人ID |
| registered_at | TEXT | 登记时间 |
| last_handler | INTEGER FK | 最近处理人ID |
| last_handled_at | TEXT | 最近处理时间 |

### events 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 事件ID |
| sample_id | INTEGER FK | 样本ID |
| from_state | TEXT | 原状态 |
| to_state | TEXT | 新状态 |
| operator_id | INTEGER FK | 操作者ID |
| reason | TEXT | 操作原因 |
| event_type | TEXT | 事件类型 |
| is_correction | INTEGER | 是否更正事件（0/1） |
| corrected_event_id | INTEGER FK | 被更正的事件ID |
| created_at | TEXT | 创建时间 |

### import_failures 表（批量导入失败记录）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 失败记录ID |
| import_batch_id | TEXT | 导入批次号 |
| row_number | INTEGER | 行号 |
| sample_no | TEXT | 样本号 |
| batch_no | TEXT | 批次号 |
| sample_type | TEXT | 样本类型 |
| description | TEXT | 描述 |
| error_type | TEXT | 错误类型 |
| error_message | TEXT | 错误详情 |
| operator_id | INTEGER FK | 操作者ID |
| created_at | TEXT | 创建时间 |

## ✅ 文档回归检查

为了防止接口行为与文档示例不一致，提供了自动化回归检查脚本：

```bash
# 运行回归检查，验证所有 README 示例与真实接口一致
python validate_readme_examples.py
```

**检查内容**：
- CSV 上传示例的返回字段与文档一致
- CSV 缺描述列仅进入失败明细，不创建样本
- JSON API 示例的返回字段与文档一致
- JSON 空描述值仅进入失败明细，不创建样本
- 部分成功场景：合法行成功，缺描述行失败，成功不丢失
- 失败查询接口返回字段与文档一致
- 审计CSV不包含被拒绝样本，不污染审计结果
- 所有返回字段（success_items、failure_items）与文档一致
- `Description` 别名正确识别
- 错误类型（MISSING_REQUIRED）与文档一致

## 📄 许可证

内部项目
