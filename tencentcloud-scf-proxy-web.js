// 腾讯云云函数 SCF（Web 函数版）代理
// ⚠️ 这是「Web 函数」专用代码（不是事件函数！）
// 部署方式：腾讯云控制台 → 云函数 → 选中函数 → 函数代码 → 把本文件全部内容粘贴进 src/app.js（覆盖原内容）
//       函数配置里环境变量 GITHUB_TOKEN 需要：contents:write（同步用） + Actions: read and write（触发自动检索用）
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

// 处理团队协同同步（user-edits.json 的 GET/PUT）
async function proxyUserEdits(method, bodyStr, token) {
  const target = `https://api.github.com/repos/${REPO}/contents/${FILE_PATH}`;
  const ghHeaders = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'User-Agent': 'laws-sync-proxy'
  };
  try {
    const init = { method, headers: ghHeaders };
    if (method === 'PUT' || method === 'POST') init.body = bodyStr || '{}';
    const res = await fetch(target, init);
    const text = await res.text();
    return { status: res.status, body: text };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '代理请求失败: ' + e.message }) };
  }
}

// 触发 GitHub Actions 自动检索任务（workflow_dispatch）
async function triggerUpdate(token) {
  const url = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'laws-sync-proxy'
      },
      body: JSON.stringify({ ref: 'main' })
    });
    const text = await res.text();
    if (res.status >= 200 && res.status < 300) {
      return { status: 200, body: JSON.stringify({ message: '已触发自动检索，约 1-3 分钟后刷新页面查看更新' }) };
    }
    let msg = '触发失败';
    try { const j = JSON.parse(text); if (j && j.message) msg = j.message; } catch (e) {}
    // 常见原因：令牌缺少 Actions 权限
    return { status: res.status, body: JSON.stringify({ message: msg + '（请确认 GITHUB_TOKEN 已含 Actions: read and write 权限）' }) };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '触发请求失败: ' + e.message }) };
  }
}

async function handleRequest(method, pathname, bodyStr) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return { status: 500, body: JSON.stringify({ message: '服务端未配置 GITHUB_TOKEN' }) };
  }
  if (pathname === '/trigger-update') {
    if (method !== 'POST') return { status: 405, body: JSON.stringify({ message: '仅支持 POST' }) };
    return await triggerUpdate(token);
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

  const pathname = (req.url || '/').split('?')[0];
  let bodyStr = '';
  req.on('data', chunk => { bodyStr += chunk; });
  req.on('end', async () => {
    try {
      const result = await handleRequest(req.method, pathname, bodyStr);
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
