// ===== 全局状态 =====
let token = localStorage.getItem('token') || null;
let currentUser = null;
let charts = {};

// ===== API =====
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch('/api' + path, { ...options, headers });
    if (res.status === 401) { token = null; localStorage.removeItem('token'); showRolePage(); throw new Error('未登录'); }
    return res.json();
}

// ===== 角色选择 =====
async function showRolePage() {
    document.getElementById('appPage').classList.add('hidden');
    document.getElementById('rolePage').classList.remove('hidden');
    const data = await api('/auth/roles');
    const icons = { student: '🎓', worker: '💼', general: '👤' };
    const typeNames = { student: '学生', worker: '职场人', general: '自由职业' };
    document.getElementById('roleList').innerHTML = (data.data || []).map(r => `
        <div class="role-item" onclick="selectRole(${r.id})">
            <span class="avatar">${icons[r.user_type] || '👤'}</span>
            <div class="info"><div class="name">${escapeHtml(r.username)}</div><div class="type">${typeNames[r.user_type] || r.user_type}</div></div>
        </div>
    `).join('');
}

async function selectRole(userId) {
    try {
        const data = await api('/auth/select', { method: 'POST', body: JSON.stringify({ user_id: userId }) });
        if (data.code !== 0) { alert('选择失败: ' + (data.detail || '未知错误')); return; }
        token = data.data.access_token;
        currentUser = data.data.user;
        localStorage.setItem('token', token);
        await enterApp();
    } catch (e) {
        alert('选择角色出错: ' + e.message);
    }
}

function switchRole() {
    token = null;
    currentUser = null;
    localStorage.removeItem('token');
    showRolePage();
}

async function enterApp() {
    document.getElementById('rolePage').classList.add('hidden');
    document.getElementById('appPage').classList.remove('hidden');
    try {
        const me = await api('/auth/me');
        if (me.code === 0) {
            currentUser = me.data;
            document.getElementById('sidebarUsername').textContent = me.data.username;
        }
    } catch (e) { console.error('get me error:', e); }
    loadDashboard();
}

// ===== 标签切换 =====
document.querySelectorAll('.sidebar nav a').forEach(a => {
    a.addEventListener('click', e => {
        e.preventDefault();
        document.querySelectorAll('.sidebar nav a').forEach(x => x.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
        a.classList.add('active');
        const tab = a.dataset.tab;
        document.getElementById('tab-' + tab).classList.add('active');
        if (tab === 'dashboard') loadDashboard();
        if (tab === 'schedule') loadSchedules();
        if (tab === 'consume') loadConsumes();
        if (tab === 'item') loadItems();
        if (tab === 'study') loadStudies();
        if (tab === 'travel') loadTravels();
    });
});

// ===== Dashboard =====
async function loadDashboard() {
    const data = await api('/stats/dashboard');
    if (data.code !== 0) return;
    const d = data.data;
    document.getElementById('statConsume').textContent = '¥' + d.month_consume.toFixed(0);
    document.getElementById('statStudy').textContent = d.week_study_hours + 'h';
    document.getElementById('statSchedule').textContent = d.upcoming_schedules;
    document.getElementById('statExpire').textContent = d.expiring_items;
    renderCharts(d);
    loadRulesPreview();
}

function renderCharts(d) {
    Object.values(charts).forEach(c => { try { c.destroy(); } catch(e) {} });
    charts = {};
    if (typeof Chart === 'undefined') return;
    try {
        if (d.daily_consume && d.daily_consume.length) {
            charts.consume = new Chart(document.getElementById('consumeChart').getContext('2d'), {
                type: 'line',
                data: { labels: d.daily_consume.map(x => x.day.slice(5)), datasets: [{ label: '消费(元)', data: d.daily_consume.map(x => x.total), borderColor: '#667eea', backgroundColor: 'rgba(102,126,234,0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, plugins: { legend: { display: false } } },
            });
        }
        if (d.consume_categories && d.consume_categories.length) {
            const colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140'];
            charts.category = new Chart(document.getElementById('categoryChart').getContext('2d'), {
                type: 'doughnut',
                data: { labels: d.consume_categories.map(x => x.category), datasets: [{ data: d.consume_categories.map(x => x.total), backgroundColor: colors }] },
                options: { responsive: true },
            });
        }
        if (d.study_subjects && d.study_subjects.length) {
            const colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];
            charts.study = new Chart(document.getElementById('studyChart').getContext('2d'), {
                type: 'bar',
                data: { labels: d.study_subjects.map(x => x.subject), datasets: [{ label: '分钟', data: d.study_subjects.map(x => x.minutes), backgroundColor: colors }] },
                options: { responsive: true, plugins: { legend: { display: false } } },
            });
        }
    } catch (e) { console.error('chart error:', e); }
}

async function loadRulesPreview() {
    const data = await api('/evolution/rules');
    const box = document.getElementById('rulesPreview');
    box.innerHTML = (data.data && data.data.length)
        ? data.data.slice(0, 5).map(r => `<div class="rule-item">${escapeHtml(r.name)} <span class="confidence">${(r.confidence * 100).toFixed(0)}%</span></div>`).join('')
        : '<p style="color:#999;font-size:13px;">暂无规则，先积累一些数据吧~</p>';
}

// ===== 聊天 =====
async function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;
    appendChat('user', msg);
    input.value = '';
    try {
        const data = await api('/agent/chat', { method: 'POST', body: JSON.stringify({ message: msg }) });
        appendChat('bot', data.data?.response || '抱歉，暂无回复');
    } catch (e) { appendChat('bot', '请求失败：' + e.message); }
}

function appendChat(role, text) {
    const box = document.getElementById('chatBox');
    box.innerHTML += `<div class="msg ${role}"><div class="bubble">${escapeHtml(text)}</div></div>`;
    box.scrollTop = box.scrollHeight;
}

// ===== CRUD =====
async function addSchedule() {
    await api('/schedules', { method: 'POST', body: JSON.stringify({ title: val('scTitle'), category: val('scCategory'), start_time: val('scStart'), end_time: val('scEnd') }) });
    loadSchedules();
}
async function loadSchedules() {
    const data = await api('/schedules');
    document.getElementById('scheduleList').innerHTML = (data.data || []).map(s =>
        `<div class="list-item"><span>${escapeHtml(s.title)}</span><span>${s.category} · ${s.is_completed ? '✅' : '⏳'}</span></div>`
    ).join('') || '<p style="color:#999">暂无日程</p>';
}

async function addConsume() {
    await api('/consumes', { method: 'POST', body: JSON.stringify({ amount: parseFloat(val('cAmount')), category: val('cCategory'), merchant: val('cMerchant') || null }) });
    loadConsumes();
}
async function loadConsumes() {
    const data = await api('/consumes');
    const icons = { food: '🍜', shopping: '🛒', transport: '🚗', entertainment: '🎮', study: '📚', rent: '🏠' };
    document.getElementById('consumeList').innerHTML = (data.data || []).slice(0, 20).map(c =>
        `<div class="list-item"><span>${icons[c.category] || '📌'} ${escapeHtml(c.merchant || c.category)}</span><span>¥${c.amount.toFixed(2)}</span></div>`
    ).join('') || '<p style="color:#999">暂无记录</p>';
}

async function addItem() {
    await api('/items', { method: 'POST', body: JSON.stringify({ name: val('iName'), location: val('iLocation'), category: val('iCategory'), expire_at: val('iExpire') || null }) });
    loadItems();
}
async function loadItems() {
    const data = await api('/items');
    document.getElementById('itemList').innerHTML = (data.data || []).map(i =>
        `<div class="list-item"><span>${escapeHtml(i.name)} · 📍${escapeHtml(i.location)}</span><span>${i.expire_at ? '⏰' + i.expire_at.slice(0, 10) : i.category}</span></div>`
    ).join('') || '<p style="color:#999">暂无物品</p>';
}

async function addStudy() {
    await api('/studies/records', { method: 'POST', body: JSON.stringify({ subject: val('stSubject'), duration_minutes: parseInt(val('stDuration')), efficiency: parseFloat(val('stEfficiency')) || null, is_delayed: document.getElementById('stDelayed').checked }) });
    loadStudies();
}
async function loadStudies() {
    const data = await api('/studies/stats');
    document.getElementById('studyList').innerHTML = (data.data || []).map(s =>
        `<div class="list-item"><span>📚 ${escapeHtml(s.subject)}</span><span>${s.total_minutes}分钟 · ${s.sessions}次</span></div>`
    ).join('') || '<p style="color:#999">暂无记录</p>';
}

async function addTravel() {
    await api('/travels', { method: 'POST', body: JSON.stringify({ title: val('tTitle'), destination: val('tDest'), travel_type: val('tType'), depart_time: val('tDepart') }) });
    loadTravels();
}
async function loadTravels() {
    const data = await api('/travels');
    document.getElementById('travelList').innerHTML = (data.data || []).map(t =>
        `<div class="list-item"><span>🚗 ${escapeHtml(t.title)} → ${escapeHtml(t.destination || '')}</span><span>${t.type}</span></div>`
    ).join('') || '<p style="color:#999">暂无出行</p>';
}

async function runEvolution(mode) {
    const btn = event.target;
    btn.textContent = '演化中...';
    btn.disabled = true;
    try {
        const data = await api('/evolution/run?mode=' + mode, { method: 'POST' });
        if (data.code === 0) {
            alert(`演化完成！模式: ${data.data.mode}, 规则数: ${data.data.rules_count || data.data.rules_updated || 0}`);
            loadRules();
        }
    } finally {
        btn.textContent = mode === 'full' ? '🔬 全量深度演化' : '🌙 增量演化';
        btn.disabled = false;
    }
}

async function loadRules() {
    const data = await api('/evolution/rules');
    if (data.code !== 0) return;
    const dimNames = { time: '时间', consume: '消费', study: '学习', item: '物品', travel: '出行' };
    const prioLabels = { 1: '低', 2: '中', 3: '高' };
    document.getElementById('rulesList').innerHTML = (data.data || []).map(r => `
        <div class="rule-card ${r.is_active ? '' : 'inactive'}">
            <div class="rule-header">
                <span class="rule-name">${r.is_active ? '🟢' : '⚪'} ${escapeHtml(r.name)}</span>
                <span class="rule-meta">v${r.version} · 置信度${(r.confidence*100).toFixed(0)}% · 样本${r.sample_count}</span>
            </div>
            <div class="rule-meta">${dimNames[r.dimension] || r.dimension} · 优先级: ${prioLabels[r.priority] || r.priority} · ${escapeHtml(r.description)}</div>
            <div class="rule-actions">
                <button onclick="toggleRule(${r.id}, ${r.is_active ? 'false' : 'true'})"
                    class="btn-toggle ${r.is_active ? 'disable' : ''}">${r.is_active ? '禁用' : '启用'}</button>
                <button onclick="pinRule(${r.id}, ${Math.min(r.priority + 1, 3)})" class="btn-pin">置顶</button>
                <button onclick="rollbackRule(${r.id})" class="btn-rollback">回滚</button>
                <button onclick="deleteRule(${r.id})" class="btn-delete">删除</button>
            </div>
        </div>
    `).join('') || '<p style="color:#999">暂无规则，先积累至少15条行为数据后触发演化</p>';
}

async function toggleRule(id, active) {
    await api(`/evolution/rules/${id}/toggle?active=${active}`, { method: 'POST' });
    loadRules();
}
async function pinRule(id, prio) {
    await api(`/evolution/rules/${id}/pin?priority=${prio}`, { method: 'POST' });
    loadRules();
}
async function rollbackRule(id) {
    if (!confirm('确定回滚到上一版本？')) return;
    await api(`/evolution/rules/${id}/rollback`, { method: 'POST' });
    loadRules();
}
async function deleteRule(id) {
    if (!confirm('确定删除此规则？')) return;
    await api(`/evolution/rules/${id}`, { method: 'DELETE' });
    loadRules();
}

// ===== 工具 =====
function val(id) { return document.getElementById(id).value; }
function escapeHtml(s) { if (!s) return ''; return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

// ===== 初始化 =====
if (token) { enterApp().catch(() => showRolePage()); } else { showRolePage(); }
