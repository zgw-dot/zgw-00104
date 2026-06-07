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

1. **重复样本号测试**：尝试登记 S001，应被拦截
2. **跳级归档测试**：用普通操作员账号尝试归档，或直接调用 API 对非复核中样本归档
3. **空原因驳回测试**：尝试不填原因驳回
4. **越权测试**：用普通操作员账号尝试作废/撤销
5. **角色切换测试**：切换不同账号，观察可用按钮变化
6. **撤销测试**：用管理员对 S004 撤销，观察时间线新增更正事件
7. **审计导出测试**：导出 S003 审计文件，验证与界面时间线一致
8. **重启验证**：停止服务后重启，验证状态完整保留
9. **直接调 API 测试**：使用 curl/postman 尝试越权操作，验证后端拦截

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

## 📄 许可证

内部项目
