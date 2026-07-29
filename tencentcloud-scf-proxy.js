// 腾讯云云函数 SCF（Web 函数）代理
// 作用：浏览器把"写回 GitHub"的请求发到这个国内可达的函数，
//       函数用服务端环境变量 GITHUB_TOKEN 调用 GitHub API，写 user-edits.json。
// 浏览器无需直连 api.github.com（国内被墙），同事零填写、免登录。
//
// 部署：腾讯云控制台 → 云函数 → 新建「Web 函数」→ 运行环境选 Node.js 18 →
//       把本文件全部内容粘贴进函数代码 → 函数配置里添加环境变量 GITHUB_TOKEN（值=细粒度令牌）→
//       触发器里创建「Web 函数 URL」并勾选启用 CORS。

const REPO = 'haideweili1/laws-list';
const FILE_PATH = 'user-edits.json';

exports.main = async (event, context) => {
  const method = (event.httpMethod || 'GET').toUpperCase();
  const token = process.env.GITHUB_TOKEN;

  const corsHeaders = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, PUT, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  };

  // 浏览器跨域预检
  if (method === 'OPTIONS') {
    return { statusCode: 200, headers: corsHeaders, body: '' };
  }

  if (!token) {
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ message: '服务端未配置 GITHUB_TOKEN' })
    };
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
      init.body = typeof event.body === 'string' ? event.body : JSON.stringify(event.body || {});
    }
    const res = await fetch(target, init);
    const text = await res.text();
    return {
      statusCode: res.status,
      headers: corsHeaders,
      body: text
    };
  } catch (e) {
    return {
      statusCode: 502,
      headers: corsHeaders,
      body: JSON.stringify({ message: '代理请求失败: ' + e.message })
    };
  }
};
