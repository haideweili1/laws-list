// 腾讯云云函数 SCF（Web 函数版）代理
// ⚠️ 这是「Web 函数」专用代码（不是事件函数！）
// 部署方式：腾讯云控制台 → 云函数 → 选中函数 → 函数代码 → 把本文件全部内容粘贴进 src/app.js（覆盖原内容）
//       函数配置里环境变量 GITHUB_TOKEN 需要：
//         - contents:write        （团队协同同步 user-edits.json 用）
//         - Actions: read and write（触发自动检索 + 读取运行状态用）
//         - Pages: read and write  （读取 GitHub Pages 部署状态用）
//       函数 URL 已开启公网访问
//
// 提供的接口：
//   GET/PUT  /                 团队协同同步 user-edits.json
//   POST     /trigger-update   触发 GitHub Actions 自动检索（草稿模式，只出提案不动数据）
//   GET      /check-status     查询本次检索运行状态
//   POST     /apply-proposed   把网页上「待确认更新」里你勾选的提案写回 data.json（唯一写数据入口）

const http = require('http');
const REPO = 'haideweili1/laws-list';
const FILE_PATH = 'user-edits.json';
const WORKFLOW_FILE = 'update.yml';
const PORT = process.env.SCF_LOCAL_PORT || process.env.PORT || 9000;

function corsHeaders() {
  return {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, PUT, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept, Authorization'
  };
}

const GH_HEADERS = (token) => ({
  'Authorization': `Bearer ${token}`,
  'Accept': 'application/vnd.github+json',
  'Content-Type': 'application/json',
  'User-Agent': 'laws-sync-proxy'
});

// 处理团队协同同步（user-edits.json 的 GET/PUT）
async function proxyUserEdits(method, bodyStr, token) {
  const target = `https://api.github.com/repos/${REPO}/contents/${FILE_PATH}`;
  try {
    if (method === 'GET') {
      const res = await fetch(target, { headers: GH_HEADERS(token) });
      const text = await res.text();
      return { status: res.status, body: text };
    }
    // 写：先取现有文件的 sha（更新需要；文件不存在则创建，无需 sha）
    let sha = null;
    const getRes = await fetch(target, { headers: GH_HEADERS(token) });
    if (getRes.ok) {
      try { const j = await getRes.json(); sha = j.sha || null; } catch (e) {}
    }
    // GitHub contents API 要求 content 为 base64、且需 message（更新还需 sha）
    const content = Buffer.from(bodyStr || '{}', 'utf8').toString('base64');
    const putBody = JSON.stringify({
      message: 'sync: update user-edits.json',
      content: content,
      ...(sha ? { sha } : {})
    });
    const res = await fetch(target, { method: 'PUT', headers: GH_HEADERS(token), body: putBody });
    const text = await res.text();
    return { status: res.status, body: text };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '代理请求失败: ' + e.message }) };
  }
}

// ===== 通用 GitHub 文件读写工具（供「确认应用提案」使用）=====
async function ghGetSha(token, path) {
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  try {
    const res = await fetch(url, { headers: GH_HEADERS(token) });
    if (!res.ok) return null;
    const j = await res.json();
    return j.sha || null;
  } catch (e) { return null; }
}

async function ghPutFile(token, path, contentStr, message) {
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  const sha = await ghGetSha(token, path);
  const body = JSON.stringify({
    message: message,
    content: Buffer.from(contentStr, 'utf8').toString('base64'),
    ...(sha ? { sha } : {})
  });
  const res = await fetch(url, { method: 'PUT', headers: GH_HEADERS(token), body });
  const text = await res.text();
  return { ok: res.status >= 200 && res.status < 300, status: res.status, body: text };
}

async function ghDeleteFile(token, path, message) {
  const sha = await ghGetSha(token, path);
  if (!sha) return { ok: true, skipped: true }; // 文件不存在，视为已清理
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  const body = JSON.stringify({ message: message, sha: sha });
  const res = await fetch(url, { method: 'DELETE', headers: GH_HEADERS(token), body });
  return { ok: res.status >= 200 && res.status < 300, status: res.status };
}

// 应用「待确认更新」中被勾选的提案：写回 data.json + 变更记录，并清理提案文件
async function applyProposed(bodyStr, token) {
  let payload;
  try {
    payload = JSON.parse(bodyStr || '{}');
  } catch (e) {
    return { status: 400, body: JSON.stringify({ message: '请求体不是合法 JSON' }) };
  }
  // 「全部忽略」：只清理提案文件，绝不碰 data.json
  if (payload.discardOnly === true) {
    try {
      await ghDeleteFile(token, 'proposed-changes.json', 'chore: 丢弃本次检索提案（人工判定不采纳）');
      await ghDeleteFile(token, 'proposed-data.json', 'chore: 清理提案数据快照');
      const st0 = JSON.stringify({ status: 'idle', updatedAt: new Date().toISOString(), note: '提案已丢弃' }, null, 2) + '\n';
      await ghPutFile(token, 'retrieval-status.json', st0, 'chore: 检索状态复位 idle');
      return { status: 200, body: JSON.stringify({ message: '已丢弃本次提案，清单数据未改动', discarded: true }) };
    } catch (e) {
      return { status: 502, body: JSON.stringify({ message: '清理失败: ' + e.message }) };
    }
  }
  const data = payload.data;
  const summary = payload.summary;
  const remaining = payload.remaining; // 未被采纳、需保留待下次再看的提案（可为空数组=全部清空）
  if (!data || typeof data !== 'object' || !Array.isArray(data.laws) || !Array.isArray(data.standards)) {
    return { status: 400, body: JSON.stringify({ message: '缺少合法的 data（需含 laws/standards 数组）' }) };
  }
  if (data.laws.length === 0 && data.standards.length === 0) {
    return { status: 400, body: JSON.stringify({ message: '拒绝写入空数据，已中止' }) };
  }
  try {
    // 1) 写回 data.json
    const dataStr = JSON.stringify(data, null, 2) + '\n';
    const r1 = await ghPutFile(token, 'data.json', dataStr, 'chore: 应用已确认的检索提案（人工逐条确认）');
    if (!r1.ok) {
      let msg = '写入 data.json 失败';
      try { const j = JSON.parse(r1.body); if (j && j.message) msg += '：' + j.message; } catch (e) {}
      return { status: 502, body: JSON.stringify({ message: msg }) };
    }
    // 2) 写变更记录（网页「最近更新」面板读取）
    if (summary && typeof summary === 'object') {
      const sumStr = JSON.stringify(summary, null, 2) + '\n';
      await ghPutFile(token, 'update-summary.json', sumStr, 'chore: 更新变更记录（已确认提案）');
    }
    // 3) 处理提案文件：还有保留项就改写，否则删除
    if (Array.isArray(remaining) && remaining.length > 0) {
      const keepStr = JSON.stringify({
        generatedAt: (payload.generatedAt || new Date().toISOString().slice(0, 10)),
        pending: remaining.length,
        changes: remaining
      }, null, 2) + '\n';
      await ghPutFile(token, 'proposed-changes.json', keepStr, 'chore: 保留未确认的检索提案');
    } else {
      await ghDeleteFile(token, 'proposed-changes.json', 'chore: 清理已处理的检索提案');
    }
    await ghDeleteFile(token, 'proposed-data.json', 'chore: 清理提案数据快照');
    // 4) 复位检索状态
    const st = JSON.stringify({
      status: 'idle',
      appliedAt: new Date().toISOString(),
      note: '提案已人工确认并应用'
    }, null, 2) + '\n';
    await ghPutFile(token, 'retrieval-status.json', st, 'chore: 检索状态复位 idle');

    return { status: 200, body: JSON.stringify({ message: '已应用并推送，约 1 分钟后线上生效', applied: true }) };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '应用失败: ' + e.message }) };
  }
}

// 获取最近一次 workflow run 的 id（用于拿到 run_id；传入 latest 或空时取最新）
async function getLatestRunId(token) {
  const url = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=1`;
  try {
    const res = await fetch(url, { headers: GH_HEADERS(token) });
    if (!res.ok) return null;
    const j = await res.json();
    if (j.workflow_runs && j.workflow_runs.length) return j.workflow_runs[0].id;
  } catch (e) {}
  return null;
}

// 触发 GitHub Actions 自动检索任务（workflow_dispatch），并返回 run_id
async function triggerUpdate(token) {
  const url = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: GH_HEADERS(token),
      body: JSON.stringify({ ref: 'main' })
    });
    const text = await res.text();
    if (!(res.status >= 200 && res.status < 300)) {
      let msg = '触发失败';
      try { const j = JSON.parse(text); if (j && j.message) msg = j.message; } catch (e) {}
      return { status: res.status, body: JSON.stringify({ message: msg + '（请确认 GITHUB_TOKEN 已含 Actions: read and write 权限）' }) };
    }
    // 触发成功，取最新 run_id（用于后续轮询状态/部署）
    const runId = await getLatestRunId(token);
    return { status: 200, body: JSON.stringify({ message: '已触发自动检索，约 1-3 分钟后刷新页面查看更新', run_id: runId }) };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '触发请求失败: ' + e.message }) };
  }
}

// 查询某次运行的状态 + Pages 部署状态
async function checkStatus(token, runId) {
  if (!runId || runId === 'latest') {
    runId = await getLatestRunId(token);
  }
  if (!runId) {
    return { status: 200, body: JSON.stringify({ runStatus: 'unknown', runConclusion: null, deployStatus: 'unknown' }) };
  }
  try {
    const runUrl = `https://api.github.com/repos/${REPO}/actions/runs/${runId}`;
    const runRes = await fetch(runUrl, { headers: GH_HEADERS(token) });
    if (!runRes.ok) {
      return { status: 200, body: JSON.stringify({ runStatus: 'unknown', runConclusion: null, deployStatus: 'unknown' }) };
    }
    const run = await runRes.json();
    const runStatus = run.status;          // queued | in_progress | completed
    const runConclusion = run.conclusion;  // success | failure | cancelled | timed_out | null
    if (runStatus !== 'completed') {
      return { status: 200, body: JSON.stringify({ runStatus, runConclusion: null, deployStatus: 'pending' }) };
    }
    if (runConclusion !== 'success') {
      return { status: 200, body: JSON.stringify({ runStatus, runConclusion, deployStatus: 'not_needed' }) };
    }
    // 本仓库 Pages 采用「从 main 分支自动发布」：Actions 运行成功后 GitHub 会自动重建站点，
    // 不会产生独立的 deployment 记录（/pages/deployments 通常为空），故运行成功即视为部署成功。
    const deployStatus = 'succeeded';
    return { status: 200, body: JSON.stringify({ runStatus, runConclusion: 'success', deployStatus }) };
  } catch (e) {
    return { status: 200, body: JSON.stringify({ runStatus: 'unknown', runConclusion: null, deployStatus: 'unknown' }) };
  }
}

async function handleRequest(method, pathname, params, bodyStr) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return { status: 500, body: JSON.stringify({ message: '服务端未配置 GITHUB_TOKEN' }) };
  }
  if (pathname === '/trigger-update') {
    if (method !== 'POST') return { status: 405, body: JSON.stringify({ message: '仅支持 POST' }) };
    return await triggerUpdate(token);
  }
  if (pathname === '/check-status') {
    if (method !== 'GET') return { status: 405, body: JSON.stringify({ message: '仅支持 GET' }) };
    const runId = params.get('run_id');
    return await checkStatus(token, runId);
  }
  if (pathname === '/apply-proposed') {
    if (method !== 'POST') return { status: 405, body: JSON.stringify({ message: '仅支持 POST' }) };
    return await applyProposed(bodyStr, token);
  }
  // 默认：处理 user-edits.json 的 GET/PUT（团队协同同步）
  return await proxyUserEdits(method, bodyStr, token);
}

const server = http.createServer(async (req, res) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(200, corsHeaders());
    res.end('');
    return;
  }

  const fullUrl = new URL(req.url, 'http://localhost');
  const pathname = fullUrl.pathname;
  const params = fullUrl.searchParams;
  let bodyStr = '';
  req.on('data', chunk => { bodyStr += chunk; });
  req.on('end', async () => {
    try {
      const result = await handleRequest(req.method, pathname, params, bodyStr);
      res.writeHead(result.status, corsHeaders());
      res.end(result.body);
    } catch (e) {
      res.writeHead(500, corsHeaders());
      res.end(JSON.stringify({ message: '内部错误: ' + e.message }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`Proxy server running on port ${PORT}`);
});
