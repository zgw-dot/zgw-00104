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

async function init() {
    await loadUsers();
    await loadPermissions();
    await loadAllData();
    
    console.log('🚀 实验室样本流转工作台已启动');
    console.log('📡 API 地址:', API_BASE);
}

window.onload = init;
