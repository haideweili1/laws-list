// ============================================================
// 法律法规清单同步代理（Cloudflare Worker）
// 作用：让浏览器免登录、免令牌地读写 GitHub 上的 user-edits.json。
//  - 令牌(GH_TOKEN)以“Secret/环境变量”形式配置在服务端，不进代码、不进网页、不被 GitHub 拦截。
//  - 仅代理本仓库这唯一一个文件的 GET/PUT，且只允许指定来源站点调用，降低被滥用风险。
// 部署：Cloudflare 控制台 → Workers → 新建 → 粘贴本文件 → 保存并部署 →
//       在 Worker 的 Settings → Variables → Add variable，Name 填 GH_TOKEN，Value 填你的 GitHub 令牌，
//       Type 选 Secret（加密），Save。然后复制部署得到的 *.workers.dev 地址发给助手填入网页。
// ============================================================

const REPO = 'haideweili1/laws-list';
const FILE_PATH = 'user-edits.json';
// 只允许这个来源站点调用本代理（改成你网页实际地址；用 '*' 则允许任意来源，但不推荐）
const ALLOWED_ORIGIN = 'https://haideweili1.github.io';

export default {
  async fetch(request, env) {
    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== 'GET' && request.method !== 'PUT') {
      return json(405, { message: 'Method Not Allowed' });
    }

    const ghToken = env.GH_TOKEN;
    if (!ghToken) {
      return json(500, { message: '服务端未配置 GH_TOKEN' });
    }

    const target = `https://api.github.com/repos/${REPO}/contents/${FILE_PATH}`;
    const init = {
      method: request.method,
      headers: {
        'Authorization': `Bearer ${ghToken}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'laws-sync-proxy',
      },
    };
    if (request.method === 'PUT') {
      init.body = await request.text();
    }

    const res = await fetch(target, init);
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
    });
  }
};

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
}

function json(status, obj) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...corsHeaders(), 'Content-Type': 'application/json' },
  });
}
