// 腾讯云云函数 SCF（Web 函数版）代理
// ⚠️ 这是「Web 函数」专用代码（不是事件函数！）
// 部署方式：腾讯云控制台 → 云函数 → 选中函数 → 函数代码 → 把本文件全部内容粘贴进 src/app.js（覆盖原内容）
//       函数配置里环境变量 GITHUB_TOKEN 需要：
//         - contents:write        （团队协同同步 user-edits.json 用）
//         - Actions: read and write（触发自动检索 + 读取运行状态用）
//         - Pages: read and write  （读取 GitHub Pages 部署状态用）
//       函数 URL 已开启公网访问

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
    const init = { method, headers: GH_HEADERS(token) };
    if (method === 'PUT' || method === 'POST') init.body = bodyStr || '{}';
    const res = await fetch(target, init);
    const text = await res.text();
    return { status: res.status, body: text };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '代理请求失败: ' + e.message }) };
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
