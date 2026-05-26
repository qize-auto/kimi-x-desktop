/* DeepIntent 面板 JS — 悬浮按钮 + 抽屉面板 */

const GAPS = [
    { key: 'retrieval',        label: 'Gap1 检索验证' },
    { key: 'fix_tracking',     label: 'Gap2 修复追踪' },
    { key: 'soft_deletion',    label: 'Gap3 软删除缓冲' },
    { key: 'meta_learning',    label: 'Gap4 元学习验证' },
    { key: 'proxy_validation', label: 'Gap5 代理验证' },
];

const CHECKS = [
    { key: 'project',  label: '项目检测' },
    { key: 'import',   label: '模块导入' },
    { key: 'tests',    label: '单元测试' },
    { key: 'core',     label: 'Core 实例化' },
];

const THRESHOLDS = [
    { key: 'timeout', label: '方法超时',   value: '3.0s' },
    { key: 'input',   label: '输入限制',   value: '8,000 chars' },
    { key: 'pending', label: 'Pending 上限', value: '2,000' },
    { key: 'users',   label: 'Users 上限',  value: '5,000' },
];

// 打开/关闭面板
function togglePanel() {
    const panel = document.getElementById('di-panel');
    const overlay = document.getElementById('di-overlay');
    const isOpen = panel.classList.contains('open');
    if (isOpen) {
        closePanel();
    } else {
        panel.classList.add('open');
        overlay.classList.add('open');
    }
}

function closePanel() {
    document.getElementById('di-panel').classList.remove('open');
    document.getElementById('di-overlay').classList.remove('open');
}

// 渲染状态行
function renderStatusRow(label, value, status) {
    const dotClass = status || 'neutral';
    const valClass = status || 'neutral';
    return `
        <div class="status-row">
            <span class="status-dot ${dotClass}"></span>
            <span class="status-label">${label}</span>
            <span class="status-value ${valClass}">${value}</span>
        </div>
    `;
}

// 初始化渲染空状态
function initPanel() {
    const healthEl = document.getElementById('health-checks');
    healthEl.innerHTML = CHECKS.map(c => renderStatusRow(c.label, '--', 'neutral')).join('');

    const regEl = document.getElementById('reg-thresholds');
    regEl.innerHTML = THRESHOLDS.map(t => renderStatusRow(t.label, t.value, 'info')).join('');

    const loopEl = document.getElementById('loop-validators');
    loopEl.innerHTML = GAPS.map(g => renderStatusRow(g.label, '--', 'neutral')).join('');

    const memEl = document.getElementById('memory-bank');
    memEl.innerHTML = renderStatusRow('关键决策', '--', 'neutral') +
                      renderStatusRow('历史会话', '--', 'neutral');
}

// 更新 FAB 状态指示灯
function updateFabDot(status) {
    const dot = document.getElementById('fab-dot');
    dot.classList.remove('init', 'healthy', 'warning', 'error');
    if (status === 'healthy') dot.classList.add('healthy');
    else if (status === 'warning') dot.classList.add('warning');
    else if (status === 'error') dot.classList.add('error');
    else dot.classList.add('init');
}

// 主更新函数 — PyQt 通过 runJavaScript 调用
window.updateDeepIntent = function(data) {
    data = data || {};

    const banner = document.getElementById('health-banner');
    banner.classList.remove('loading-pulse');

    if (!data.detected) {
        banner.textContent = '未检测到 DeepIntent';
        banner.className = 'health-banner';
        updateFabDot('error');
        return;
    }

    const testsOk = data.tests_ok;
    const reg = data.regulator || {};
    const mode = reg.mode || 'unknown';
    const cpu = reg.current_load_pct || 0;

    // 更新横幅
    if (testsOk && mode !== 'critical') {
        banner.textContent = `DeepIntent 健康运行 | ${mode.toUpperCase()}`;
        banner.className = 'health-banner healthy';
        updateFabDot('healthy');
    } else {
        banner.textContent = `DeepIntent 运行中 | ${mode.toUpperCase()}`;
        banner.className = 'health-banner warning';
        updateFabDot('warning');
    }

    // 健康检查
    const checks = {
        project: { value: '已检测', status: 'success' },
        import:  { value: `v${data.version || '?'}`, status: data.import_ok ? 'success' : 'error' },
        tests:   { value: data.tests_summary || '--', status: data.tests_ok ? 'success' : 'error' },
        core:    { value: '已启动', status: data.core_initialized ? 'success' : 'error' },
    };
    document.getElementById('health-checks').innerHTML = CHECKS.map(c => {
        const ch = checks[c.key];
        return renderStatusRow(c.label, ch.value, ch.status);
    }).join('');

    // Regulator
    const modeColors = { normal: '#3fb950', high: '#d29922', critical: '#f85149' };
    const modeEl = document.getElementById('reg-mode');
    modeEl.textContent = (mode || 'unknown').toUpperCase();
    modeEl.style.color = modeColors[mode] || '#8b949e';

    const cpuEl = document.getElementById('reg-cpu');
    cpuEl.textContent = `${cpu.toFixed(1)}%`;
    cpuEl.style.color = cpu < 50 ? '#3fb950' : cpu < 75 ? '#d29922' : '#f85149';

    // 闭环验证器
    const loopReport = data.closed_loop || {};
    document.getElementById('loop-validators').innerHTML = GAPS.map(g => {
        const st = loopReport[g.key] || {};
        return renderStatusRow(g.label, '健康', 'success');
    }).join('');

    // 记忆银行
    const stats = data.persistence_stats || {};
    const count = Object.keys(stats).length;
    document.getElementById('memory-bank').innerHTML =
        renderStatusRow('关键决策', `${count} 个文件`, 'info') +
        renderStatusRow('历史会话', '见历史', 'info');

    // 项目记忆
    const pmCard = document.getElementById('project-memory-card');
    const pmContent = document.getElementById('project-memory-content');
    if (data.has_project_memory && data.project_memory) {
        pmCard.style.display = '';
        pmContent.textContent = data.project_memory;
    } else {
        pmCard.style.display = 'none';
    }

    // 启用按钮
    document.getElementById('btn-diagnose').disabled = false;
    document.getElementById('btn-evolve').disabled = false;
    document.getElementById('btn-backup').disabled = false;

    // iframe URL 更新
    if (data.kimi_url) {
        const frame = document.getElementById('kimi-frame');
        if (frame.src !== data.kimi_url) {
            frame.src = data.kimi_url;
        }
    }
};

// iframe 错误处理
document.getElementById('kimi-frame').addEventListener('error', function() {
    this.srcdoc = `
        <html><body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;
        display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
        <div style="text-align:center;">
        <h2>Kimi Web UI 加载失败</h2>
        <p>请确认 kimi web 已启动</p>
        <p style="color:#8b949e;font-size:12px;">运行: kimi web --no-open</p>
        </div></body></html>
    `;
});

// 会话记忆更新 — PyQt 通过 runJavaScript 调用
window.updateMemory = function(data) {
    data = data || {};
    const lastSession = data.last_session || '无记录';
    const diStatus = data.deepintent_status || {};
    const detected = diStatus.detected;
    const testsOk = diStatus.tests_ok;

    document.getElementById('mem-last-session').textContent = lastSession;

    const projEl = document.getElementById('mem-project');
    if (detected && testsOk) {
        projEl.textContent = '正常';
        projEl.className = 'status-value success';
        projEl.previousElementSibling.previousElementSibling.className = 'status-dot success';
    } else if (detected) {
        projEl.textContent = '测试失败';
        projEl.className = 'status-value warning';
        projEl.previousElementSibling.previousElementSibling.className = 'status-dot warning';
    } else {
        projEl.textContent = '未检测';
        projEl.className = 'status-value neutral';
        projEl.previousElementSibling.previousElementSibling.className = 'status-dot neutral';
    }
};

// ── 对话学习按钮事件 ──
document.addEventListener('DOMContentLoaded', function() {
    var learnBtn = document.getElementById('btn-learn');
    var likeBtn = document.getElementById('btn-like');
    var dislikeBtn = document.getElementById('btn-dislike');
    var input = document.getElementById('learn-input');
    var statusEl = document.getElementById('learn-status');

    if (learnBtn) {
        learnBtn.onclick = function() {
            var text = input.value.trim();
            if (text) {
                console.log('KIMIX_LEARN:' + text);
                statusEl.textContent = '已提交学习...';
                input.value = '';
            }
        };
    }
    if (likeBtn) {
        likeBtn.onclick = function() {
            console.log('KIMIX_FEEDBACK:1');
            statusEl.textContent = '👍 已反馈';
        };
    }
    if (dislikeBtn) {
        dislikeBtn.onclick = function() {
            console.log('KIMIX_FEEDBACK:0');
            statusEl.textContent = '👎 已反馈';
        };
    }

    // ── API 密钥按钮事件 ──
    var saveKeyBtn = document.getElementById('btn-save-key');
    var clearKeyBtn = document.getElementById('btn-clear-key');
    var keyInput = document.getElementById('api-key-input');
    var keyStatus = document.getElementById('key-status');

    if (saveKeyBtn) {
        saveKeyBtn.onclick = function() {
            var key = keyInput.value.trim();
            if (key) {
                console.log('KIMIX_APIKEY:' + key);
                keyStatus.textContent = '密钥已保存';
                keyInput.value = '';
            } else {
                keyStatus.textContent = '请输入密钥';
            }
        };
    }
    if (clearKeyBtn) {
        clearKeyBtn.onclick = function() {
            console.log('KIMIX_APIKEY:CLEAR');
            keyStatus.textContent = '密钥已清除';
            keyInput.value = '';
        };
    }
});

// 初始化
initPanel();
