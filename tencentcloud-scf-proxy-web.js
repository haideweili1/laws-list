// 腾讯云云函数 SCF（Web 函数版）代理
// ⚠️ 这是「Web 函数」专用代码（不是事件函数！）
// 部署方式：腾讯云控制台 → 云函数 → 新建「Web 函数」→ 运行环境 Node.js 18 →
//       把本文件全部内容粘贴进 src/app.js（或直接覆盖 app.js）
//       函数配置里添加环境变量 GITHUB_TOKEN（值=细粒度令牌）
//       函数 URL 开启公网访问

const http = require('http');
const REPO = 'haideweili1/laws-list';
const FILE_PATH = 'user-edits.json';
const PORT = process.env.SCF_LOCAL_PORT || process.env.PORT || 9000;

function corsHeaders() {
  return {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, PUT, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept, Authorization'
  };
}

async function handleRequest(method, bodyStr) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return { status: 500, body: JSON.stringify({ message: '服务端未配置 GITHUB_TOKEN' }) };
  }

  const target = `https://api.github.com/repos/${REPO}/contents/${FILE_PATH}`;
  const ghHeaders = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'User-Agent': 'laws-sync-proxy'
  };

  try {
    const init = { method, headers: ghHeaders };
    if (method === 'PUT' || method === 'POST') {
      init.body = bodyStr || '{}';
    }
    const res = await fetch(target, init);
    const text = await res.text();
    return { status: res.status, body: text };
  } catch (e) {
    return { status: 502, body: JSON.stringify({ message: '代理请求失败: ' + e.message }) };
  }
}

const server = http.createServer(async (req, res) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(200, corsHeaders());
    res.end('');
    return;
  }

  let bodyStr = '';
  req.on('data', chunk => { bodyStr += chunk; });
  req.on('end', async () => {
    try {
      const result = await handleRequest(req.method, bodyStr);
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
