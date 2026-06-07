const API_BASE = 'http://localhost:5000/api';

let currentUserId = 1;
let currentPermissions = {};
let currentSampleDetail = null;
let batches = [];
let users = [];

const STATUS_CLASS_MAP = {
    'REGISTERED': 'registered',
    'RECEIVED': 'received',
    'TESTING': 'testing',
    'REVIEWING': 'reviewing',
    'REJECTED': 'rejected',
    'ARCHIVED': 'archived',
    'CANCELLED': 'cancelled'
};

const EVENT_TYPE_NAMES = {
    'REGISTER': '登记',
    'RECEIVE': '接收',
    'TEST': '开始检测',
    'REVIEW': '提交复核',
    'REJECT': '驳回',
    'ARCHIVE': '归档',
    'CANCEL': '作废',
    'UNDO': '撤销更正',
    'RE_REGISTER': '重新登记'
};

const ERROR_TYPE_NAMES = {
    'MISSING_REQUIRED': '缺少必填项',
    'DUPLICATE_IN_FILE': '文件内重复',
    'DUPLICATE_IN_DB': '数据库重复',
    'DATABASE_ERROR': '数据库错误'
};

let currentImportResult = null;

async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    try {
        const response = await fetch(API_BASE + url, options);
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || '请求失败');
        }
        return result;
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function showModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

async function loadUsers() {
    try {
        users = await apiRequest('/users');
        const select = document.getElementById('currentUser');
        select.innerHTML = users.map(u => 
            `<option value="${u.id}">${u.name} (${u.role_name})</option>`
        ).join('');
        select.value = currentUserId;
        select.onchange = () => {
            currentUserId = parseInt(select.value);
            loadPermissions();
            loadSamples();
        };
    } catch (e) {
        console.error('Load users failed:', e);
    }
}

async function loadPermissions() {
    try {
        const result = await apiRequest(`/permissions/${currentUserId}`);
        currentPermissions = result.permissions;
        
        const permNames = {
            'register': '登记样本',
            'receive': '接收样本',
            'test': '开始检测',
            'review': '提交复核',
            'reject': '驳回样本',
            'archive': '归档样本',
            'cancel': '作废样本',
            'undo': '撤销更正'
        };
        
        const container = document.getElementById('permissionList');
        container.innerHTML = Object.entries(permNames).map(([key, name]) => {
            const allowed = currentPermissions[key];
            return `<div class="perm-item ${allowed ? 'allowed' : 'denied'}">
                <span>${allowed ? '✓' : '✗'}</span>
                <span>${name}</span>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Load permissions failed:', e);
    }
}

async function loadStats() {
    try {
        const stats = await apiRequest('/samples/stats');
        document.getElementById('pendingCount').textContent = stats.pending_count;
        document.getElementById('rejectedCount').textContent = stats.rejected_count;
    } catch (e) {
        console.error('Load stats failed:', e);
    }
}

async function loadBatches() {
    try {
        batches = await apiRequest('/batches');
        const select = document.getElementById('batchFilter');
        const currentValue = select.value;
        select.innerHTML = '<option value="">全部批次</option>' + 
            batches.map(b => `<option value="${b.batch_no}">${b.batch_no} (待处理: ${b.pending}/${b.total})</option>`).join('');
        select.value = currentValue;
        select.onchange = loadSamples;
    } catch (e) {
        console.error('Load batches failed:', e);
    }
}

async function loadSamples() {
    try {
        const batchFilter = document.getElementById('batchFilter').value;
        const stateFilter = document.getElementById('stateFilter').value;
        
        let url = '/samples?';
        const params = [];
        if (batchFilter) params.push(`batch_no=${encodeURIComponent(batchFilter)}`);
        if (stateFilter === 'pending') params.push('pending=1');
        else if (stateFilter) params.push(`state=${encodeURIComponent(stateFilter)}`);
        url += params.join('&');
        
        const samples = await apiRequest(url);
        renderSamplesTable(samples);
    } catch (e) {
        console.error('Load samples failed:', e);
    }
}

function getAvailableActions(sample) {
    const state = sample.current_state;
    const actions = [];
    
    if (state === 'REGISTERED') {
        if (currentPermissions.receive) {
            actions.push({ action: 'receive', label: '接收', class: 'primary', endpoint: `receive`, requiresReason: false });
        }
        if (currentPermissions.cancel) {
            actions.push({ action: 'cancel', label: '作废', class: 'danger', endpoint: `cancel`, requiresReason: true });
        }
    } else if (state === 'RECEIVED') {
        if (currentPermissions.test) {
            actions.push({ action: 'test', label: '检测', class: 'primary', endpoint: `test`, requiresReason: false });
        }
        if (currentPermissions.reject) {
            actions.push({ action: 'reject', label: '驳回', class: 'warning', endpoint: `reject`, requiresReason: true });
        }
        if (currentPermissions.cancel) {
            actions.push({ action: 'cancel', label: '作废', class: 'danger', endpoint: `cancel`, requiresReason: true });
        }
    } else if (state === 'TESTING') {
        if (currentPermissions.review) {
            actions.push({ action: 'review', label: '提交复核', class: 'primary', endpoint: `review`, requiresReason: false });
        }
        if (currentPermissions.reject) {
            actions.push({ action: 'reject', label: '驳回', class: 'warning', endpoint: `reject`, requiresReason: true });
        }
        if (currentPermissions.cancel) {
            actions.push({ action: 'cancel', label: '作废', class: 'danger', endpoint: `cancel`, requiresReason: true });
        }
    } else if (state === 'REVIEWING') {
        if (currentPermissions.archive) {
            actions.push({ action: 'archive', label: '归档', class: 'success', endpoint: `archive`, requiresReason: false });
        }
        if (currentPermissions.reject) {
            actions.push({ action: 'reject', label: '驳回', class: 'warning', endpoint: `reject`, requiresReason: true });
        }
        if (currentPermissions.cancel) {
            actions.push({ action: 'cancel', label: '作废', class: 'danger', endpoint: `cancel`, requiresReason: true });
        }
    } else if (state === 'REJECTED') {
        if (currentPermissions.register) {
            actions.push({ action: 're-register', label: '重新登记', class: 'primary', endpoint: `re-register`, requiresReason: false });
        }
    }
    
    if (state !== 'REGISTERED' && state !== 'ARCHIVED' && state !== 'CANCELLED' && currentPermissions.undo) {
        actions.push({ action: 'undo', label: '撤销', class: 'warning', endpoint: `undo`, requiresReason: true });
    }
    
    return actions;
}

function renderSamplesTable(samples) {
    const tbody = document.getElementById('samplesTableBody');
    
    if (samples.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9">
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div class="empty-state-text">暂无符合条件的样本</div>
            </div>
        </td></tr>`;
        return;
    }
    
    tbody.innerHTML = samples.map(s => {
        const statusClass = STATUS_CLASS_MAP[s.current_state] || '';
        const actions = getAvailableActions(s);
        
        let lastHandler = s.last_handler_name || '-';
        let lastHandledAt = s.last_handled_at || '-';
        
        let rejectReason = '-';
        if (s.current_state === 'REJECTED') {
            rejectReason = '<span class="reason-badge" title="点击查看详情" onclick="showRejectReason(' + s.id + ')">查看原因</span>';
        }
        
        const actionBtns = actions.map(a => 
            `<button class="action-btn ${a.class}" onclick="executeAction(${s.id}, '${a.action}', '${a.endpoint}', ${a.requiresReason}, '${a.label}')">${a.label}</button>`
        ).join('');
        
        return `<tr>
            <td><strong>${s.sample_no}</strong></td>
            <td>${s.batch_no}</td>
            <td>${s.sample_type}</td>
            <td><span class="status-badge ${statusClass}">${s.current_state_name}</span></td>
            <td>${s.registered_by_name || '-'}</td>
            <td>${lastHandler}</td>
            <td>${lastHandledAt}</td>
            <td>${rejectReason}</td>
            <td>
                <div class="operation-btns">
                    <button class="action-btn small secondary" onclick="showSampleDetail(${s.id})">详情</button>
                    ${actionBtns}
                </div>
            </td>
        </tr>`;
    }).join('');
}

async function showSampleDetail(sampleId) {
    try {
        const sample = await apiRequest(`/samples/${sampleId}`);
        currentSampleDetail = sample;
        
        document.getElementById('detailTitle').textContent = `样本详情 - ${sample.sample_no}`;
        document.getElementById('detailSampleNo').textContent = sample.sample_no;
        document.getElementById('detailBatchNo').textContent = sample.batch_no;
        document.getElementById('detailSampleType').textContent = sample.sample_type;
        document.getElementById('detailDesc').textContent = sample.description || '-';
        
        const statusClass = STATUS_CLASS_MAP[sample.current_state] || '';
        document.getElementById('detailState').innerHTML = 
            `<span class="status-badge ${statusClass}">${sample.current_state_name}</span>`;
        
        document.getElementById('detailRegBy').textContent = sample.registered_by_name || '-';
        document.getElementById('detailRegAt').textContent = sample.registered_at || '-';
        document.getElementById('detailLastBy').textContent = sample.last_handler_name || '-';
        document.getElementById('detailLastAt').textContent = sample.last_handled_at || '-';
        
        const actions = getAvailableActions(sample);
        document.getElementById('detailActions').innerHTML = actions.map(a => 
            `<button class="action-btn ${a.class}" onclick="executeAction(${sample.id}, '${a.action}', '${a.endpoint}', ${a.requiresReason}, '${a.label}')">${a.label}</button>`
        ).join('');
        
        renderTimeline(sample.events);
        
        showModal('detailModal');
    } catch (e) {
        console.error('Show detail failed:', e);
    }
}

function renderTimeline(events) {
    const container = document.getElementById('timeline');
    container.innerHTML = events.map(e => {
        const toClass = STATUS_CLASS_MAP[e.to_state] || '';
        const isCorrection = e.is_correction === 1;
        const dotClass = isCorrection ? 'correction' : 
                        e.to_state === 'REJECTED' ? 'rejected' :
                        e.to_state === 'ARCHIVED' ? 'archived' :
                        e.to_state === 'CANCELLED' ? 'cancelled' : '';
        
        let stateHtml = `<span class="status-badge ${toClass}">${e.to_state_name}</span>`;
        if (e.from_state) {
            const fromClass = STATUS_CLASS_MAP[e.from_state] || '';
            stateHtml = `<span class="status-badge ${fromClass}">${e.from_state_name}</span>
                        <span class="timeline-arrow">→</span>
                        ${stateHtml}`;
        }
        
        const reasonClass = isCorrection ? 'correction' : '';
        const contentClass = isCorrection ? 'correction' : '';
        const typeName = EVENT_TYPE_NAMES[e.event_type] || e.event_type;
        
        return `<div class="timeline-item">
            <div class="timeline-dot ${dotClass}"></div>
            <div class="timeline-content ${contentClass}">
                <div class="timeline-event-type">
                    ${isCorrection ? '⚠️ ' : ''}${typeName}
                    ${isCorrection ? '<span class="status-badge correction">更正</span>' : ''}
                </div>
                <div class="timeline-state">${stateHtml}</div>
                ${e.reason ? `<div class="timeline-reason ${reasonClass}">${e.reason}</div>` : ''}
                <div class="timeline-meta">
                    <span class="timeline-operator">
                        👤 ${e.operator_name}
                        <span class="timeline-role">${e.operator_role}</span>
                    </span>
                    <span>🕐 ${e.created_at}</span>
                </div>
                ${e.corrected_event_id ? `<div style="font-size:11px;color:#9ca3af;margin-top:4px;">更正事件 #${e.corrected_event_id}</div>` : ''}
            </div>
        </div>`;
    }).reverse().join('');
}

function executeAction(sampleId, action, endpoint, requiresReason, label) {
    if (requiresReason) {
        document.getElementById('actionTitle').textContent = `${label}确认`;
        
        let desc = '';
        let reasonLabel = '原因';
        
        if (action === 'reject') {
            desc = '确定要驳回该样本吗？驳回后样本将回到待登记状态。';
            reasonLabel = '驳回原因 *';
        } else if (action === 'cancel') {
            desc = '确定要作废该样本吗？作废后样本无法继续流转。';
            reasonLabel = '作废原因 *';
        } else if (action === 'undo') {
            desc = '确定要撤销上一步操作吗？将恢复到上一个合法状态。';
            reasonLabel = '撤销原因 *';
        }
        
        document.getElementById('actionDesc').textContent = desc;
        document.getElementById('reasonLabel').textContent = reasonLabel;
        document.getElementById('reasonGroup').style.display = 'block';
        document.getElementById('actionReason').value = '';
        
        document.getElementById('actionConfirmBtn').onclick = () => {
            const reason = document.getElementById('actionReason').value.trim();
            if (!reason) {
                showToast('请输入原因', 'warning');
                return;
            }
            doAction(sampleId, endpoint, reason);
        };
        
        showModal('actionModal');
    } else {
        doAction(sampleId, endpoint, null);
    }
}

async function doAction(sampleId, endpoint, reason) {
    try {
        closeModal('actionModal');
        const data = { operator_id: currentUserId };
        if (reason) data.reason = reason;
        
        await apiRequest(`/samples/${sampleId}/${endpoint}`, 'POST', data);
        showToast('操作成功', 'success');
        loadAllData();
        if (currentSampleDetail && currentSampleDetail.id === sampleId) {
            showSampleDetail(sampleId);
        }
    } catch (e) {
        console.error('Action failed:', e);
    }
}

function showRegisterModal() {
    if (!currentPermissions.register) {
        showToast('您没有登记样本的权限', 'error');
        return;
    }
    document.getElementById('regSampleNo').value = '';
    document.getElementById('regBatchNo').value = '';
    document.getElementById('regSampleType').value = '血液样本';
    document.getElementById('regDesc').value = '';
    document.getElementById('regSampleNoError').textContent = '';
    showModal('registerModal');
}

async function registerSample() {
    const sampleNo = document.getElementById('regSampleNo').value.trim();
    const batchNo = document.getElementById('regBatchNo').value.trim();
    const sampleType = document.getElementById('regSampleType').value;
    const description = document.getElementById('regDesc').value.trim();
    
    if (!sampleNo || !batchNo) {
        showToast('请填写样本编号和批次号', 'warning');
        return;
    }
    
    try {
        const check = await apiRequest(`/samples/${sampleNo}/exists`);
        if (check.exists) {
            document.getElementById('regSampleNoError').textContent = '样本号已存在';
            return;
        }
    } catch (e) {
        return;
    }
    
    try {
        await apiRequest('/samples', 'POST', {
            sample_no: sampleNo,
            batch_no: batchNo,
            sample_type: sampleType,
            description: description,
            operator_id: currentUserId
        });
        showToast('样本登记成功', 'success');
        closeModal('registerModal');
        loadAllData();
    } catch (e) {
        console.error('Register failed:', e);
    }
}

function showReceiveModal() {
    if (!currentPermissions.receive) {
        showToast('您没有接收样本的权限', 'error');
        return;
    }
    document.getElementById('receiveBatchNo').value = '';
    document.getElementById('receiveReason').value = '批次接收';
    showModal('receiveModal');
}

async function receiveBatch() {
    const batchNo = document.getElementById('receiveBatchNo').value.trim();
    const reason = document.getElementById('receiveReason').value.trim() || '批次接收';
    
    if (!batchNo) {
        showToast('请输入批次号', 'warning');
        return;
    }
    
    try {
        const result = await apiRequest('/batches/receive', 'POST', {
            batch_no: batchNo,
            reason: reason,
            operator_id: currentUserId
        });
        showToast(result.message, 'success');
        closeModal('receiveModal');
        loadAllData();
    } catch (e) {
        console.error('Receive batch failed:', e);
    }
}

function exportAudit(type) {
    if (!currentSampleDetail) return;
    const identifier = type === 'sample' ? currentSampleDetail.sample_no : currentSampleDetail.batch_no;
    window.open(`${API_BASE}/export/${type}/${identifier}`, '_blank');
}

async function showRejectReason(sampleId) {
    await showSampleDetail(sampleId);
}

async function loadAllData() {
    await Promise.all([
        loadStats(),
        loadBatches(),
        loadSamples()
    ]);
}

function showImportModal() {
    if (!currentPermissions.register) {
        showToast('您没有登记样本的权限', 'error');
        return;
    }
    document.getElementById('importFile').value = '';
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('importResult').style.display = 'none';
    document.getElementById('importBtn').disabled = true;
    currentImportResult = null;
    showModal('importModal');
}

function downloadTemplate() {
    const template = '样本号,批次号,样本类型,描述\n' +
                    'S100,BATCH-2026-004,血液样本,常规体检样本\n' +
                    'S101,BATCH-2026-004,尿液样本,入职体检样本\n';
    
    const blob = new Blob(['\ufeff' + template], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = '样本导入模板.csv';
    link.click();
    URL.revokeObjectURL(link.href);
    showToast('模板已下载', 'success');
}

function parseCSV(text) {
    const lines = text.split('\n').filter(line => line.trim());
    if (lines.length < 1) return { headers: [], rows: [] };
    
    const headers = lines[0].split(',').map(h => h.trim());
    const rows = [];
    
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        if (values.length >= headers.length) {
            const row = {};
            headers.forEach((header, idx) => {
                row[header] = (values[idx] || '').trim();
            });
            rows.push(row);
        }
    }
    
    return { headers, rows };
}

function previewImport() {
    const fileInput = document.getElementById('importFile');
    const file = fileInput.files[0];
    
    if (!file) {
        document.getElementById('previewSection').style.display = 'none';
        document.getElementById('importBtn').disabled = true;
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const text = e.target.result;
            const { headers, rows } = parseCSV(text);
            
            const previewTable = document.getElementById('previewTable');
            let html = '<thead><tr>';
            headers.forEach(h => html += `<th>${h}</th>`);
            html += '</tr></thead><tbody>';
            
            const previewRows = rows.slice(0, 5);
            previewRows.forEach(row => {
                html += '<tr>';
                headers.forEach(h => html += `<td>${row[h] || ''}</td>`);
                html += '</tr>';
            });
            html += '</tbody>';
            
            previewTable.innerHTML = html;
            document.getElementById('previewSection').style.display = 'block';
            document.getElementById('importBtn').disabled = rows.length === 0;
            
            if (rows.length > 5) {
                document.getElementById('previewSection').querySelector('h4').textContent = 
                    `📊 数据预览（前 5 行，共 ${rows.length} 行）`;
            } else {
                document.getElementById('previewSection').querySelector('h4').textContent = 
                    `📊 数据预览（共 ${rows.length} 行）`;
            }
        } catch (err) {
            showToast('CSV 文件解析失败: ' + err.message, 'error');
            document.getElementById('previewSection').style.display = 'none';
            document.getElementById('importBtn').disabled = true;
        }
    };
    reader.readAsText(file, 'UTF-8');
}

async function doImport() {
    const fileInput = document.getElementById('importFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('请选择 CSV 文件', 'warning');
        return;
    }
    
    const importBtn = document.getElementById('importBtn');
    importBtn.disabled = true;
    importBtn.textContent = '导入中...';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('operator_id', currentUserId);
        
        const response = await fetch(API_BASE + '/samples/import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || '导入失败');
        }
        
        currentImportResult = result;
        renderImportResult(result);
        
        showToast(result.message, result.failure_count > 0 ? 'warning' : 'success');
        loadAllData();
        
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        importBtn.disabled = false;
        importBtn.textContent = '开始导入';
    }
}

function renderImportResult(result) {
    const importResultDiv = document.getElementById('importResult');
    importResultDiv.style.display = 'block';
    
    document.getElementById('resultSummary').innerHTML = `
        <div class="summary-stats">
            <div class="stat-item success">
                <span class="stat-label">成功</span>
                <span class="stat-value">${result.success_count}</span>
            </div>
            <div class="stat-item failure">
                <span class="stat-label">失败</span>
                <span class="stat-value">${result.failure_count}</span>
            </div>
            <div class="stat-item total">
                <span class="stat-label">总计</span>
                <span class="stat-value">${result.total_count}</span>
            </div>
        </div>
        <div class="batch-info">
            <span>导入批次: <code>${result.import_batch_id}</code></span>
            <span>操作人: ${result.operator_name}</span>
        </div>
    `;
    
    if (result.success_count > 0) {
        document.getElementById('successSection').style.display = 'block';
        document.getElementById('successCount').textContent = result.success_count;
        
        const successTable = document.getElementById('successTable');
        successTable.innerHTML = `
            <thead><tr>
                <th>行号</th>
                <th>样本号</th>
                <th>批次号</th>
                <th>样本类型</th>
                <th>描述</th>
            </tr></thead><tbody>
            ${result.success_items.map(item => `
                <tr>
                    <td>${item.row_number}</td>
                    <td><strong>${item.sample_no}</strong></td>
                    <td>${item.batch_no}</td>
                    <td>${item.sample_type}</td>
                    <td>${item.description || '-'}</td>
                </tr>
            `).join('')}
            </tbody>
        `;
    } else {
        document.getElementById('successSection').style.display = 'none';
    }
    
    if (result.failure_count > 0) {
        document.getElementById('failureSection').style.display = 'block';
        document.getElementById('failureCount').textContent = result.failure_count;
        
        const failureTable = document.getElementById('failureTable');
        failureTable.innerHTML = `
            <thead><tr>
                <th>行号</th>
                <th>样本号</th>
                <th>批次号</th>
                <th>错误类型</th>
                <th>错误信息</th>
            </tr></thead><tbody>
            ${result.failure_items.map(item => `
                <tr>
                    <td>${item.row_number}</td>
                    <td>${item.sample_no || '-'}</td>
                    <td>${item.batch_no || '-'}</td>
                    <td><span class="error-badge">${ERROR_TYPE_NAMES[item.error_type] || item.error_type}</span></td>
                    <td class="error-message">${item.error_message}</td>
                </tr>
            `).join('')}
            </tbody>
        `;
    } else {
        document.getElementById('failureSection').style.display = 'none';
    }
}

function exportImportResult() {
    if (!currentImportResult) {
        showToast('没有可导出的导入结果', 'warning');
        return;
    }
    window.open(`${API_BASE}/export/import/${currentImportResult.import_batch_id}`, '_blank');
}

async function init() {
    await loadUsers();
    await loadPermissions();
    await loadAllData();
    
    console.log('🚀 实验室样本流转工作台已启动');
    console.log('📡 API 地址:', API_BASE);
}

window.onload = init;
