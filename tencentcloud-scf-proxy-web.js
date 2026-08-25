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
//   POST     /probe-links      批量链接核验（0-c：部署在广州，稳定访问 gov.cn/openstd/cfsa，
//                                真实打开页面判断 alive/dead/uncertain + 死页，消除境外 runner 超时误杀）
//   POST     /resolve-openstd  按标准号解析 openstd 真实 hcno 详情链接（落地腿1：GLM 不再编 URL，
//                                由本函数从国内 IP 真实搜索+详情页核对标准号，返回可信链接；查不到返回空）

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
// ⚠️ 性能陷阱：GET /contents/<文件> 会把整个文件内容一并返回。
//    data.json / proposed-data.json 都接近 300KB，逐个取 sha 会把云函数拖到超时
//    （现象：网页报「Failed to fetch」，但后端其实已经改了一半）。
//    因此改为：一次列举仓库根目录拿到全部文件的 sha（响应很小、不含内容），
//    后续所有写/删都复用它，不再重复下载大文件。
async function ghListRootShas(token) {
  const url = `https://api.github.com/repos/${REPO}/contents`;
  try {
    const res = await fetch(url, { headers: GH_HEADERS(token) });
    if (!res.ok) return null;              // 列举失败 → 退回逐个取 sha 的老路
    const arr = await res.json();
    if (!Array.isArray(arr)) return null;
    const map = {};
    arr.forEach(f => { if (f && f.name) map[f.name] = f.sha; });
    return map;
  } catch (e) { return null; }
}

async function ghGetSha(token, path) {
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  try {
    const res = await fetch(url, { headers: GH_HEADERS(token) });
    if (!res.ok) return null;
    const j = await res.json();
    return j.sha || null;
  } catch (e) { return null; }
}

// knownSha：传 undefined = 自己去查；传字符串/null = 直接用（null 表示文件不存在）
async function ghPutFile(token, path, contentStr, message, knownSha) {
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  let sha = (knownSha === undefined) ? await ghGetSha(token, path) : knownSha;
  const send = (s) => fetch(url, {
    method: 'PUT', headers: GH_HEADERS(token),
    body: JSON.stringify({
      message: message,
      content: Buffer.from(contentStr, 'utf8').toString('base64'),
      ...(s ? { sha: s } : {})
    })
  });
  let res = await send(sha);
  // 409/422 = sha 过期（多为 Actions 刚好也在写同一文件），重取一次 sha 再试
  if (res.status === 409 || res.status === 422) {
    const fresh = await ghGetSha(token, path);
    if (fresh && fresh !== sha) res = await send(fresh);
  }
  const text = await res.text();
  return { ok: res.status >= 200 && res.status < 300, status: res.status, body: text };
}

async function ghDeleteFile(token, path, message, knownSha) {
  const sha = (knownSha === undefined) ? await ghGetSha(token, path) : knownSha;
  if (!sha) return { ok: true, skipped: true }; // 文件不存在，视为已清理
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  const body = JSON.stringify({ message: message, sha: sha });
  const res = await fetch(url, { method: 'DELETE', headers: GH_HEADERS(token), body });
  if (res.status === 404 || res.status === 409 || res.status === 422) {
    const fresh = await ghGetSha(token, path);
    if (!fresh) return { ok: true, skipped: true };
    if (fresh !== sha) {
      const r2 = await fetch(url, {
        method: 'DELETE', headers: GH_HEADERS(token),
        body: JSON.stringify({ message: message, sha: fresh })
      });
      return { ok: r2.status >= 200 && r2.status < 300, status: r2.status };
    }
  }
  return { ok: res.status >= 200 && res.status < 300, status: res.status };
}

// 读取文件内容（用于合并式写回，如把应用记录追加进 user-edits.json）
async function ghGetContent(token, path) {
  const url = `https://api.github.com/repos/${REPO}/contents/${path}`;
  try {
    const res = await fetch(url, { headers: GH_HEADERS(token) });
    if (!res.ok) return { obj: null, sha: null };
    const j = await res.json();
    if (!j.content) return { obj: null, sha: j.sha || null };
    const content = Buffer.from(j.content.replace(/\s/g, ''), 'base64').toString('utf8');
    return { obj: JSON.parse(content), sha: j.sha || null };
  } catch (e) { return { obj: null, sha: null }; }
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
      const shaMap = await ghListRootShas(token);
      const pick = (n) => (shaMap ? (shaMap[n] || null) : undefined);
      const dc = await ghDeleteFile(token, 'proposed-changes.json', 'chore: 丢弃本次检索提案（人工判定不采纳）', pick('proposed-changes.json'));
      const dd = await ghDeleteFile(token, 'proposed-data.json', 'chore: 清理提案数据快照', pick('proposed-data.json'));
      const st0 = JSON.stringify({ status: 'idle', updatedAt: new Date().toISOString(), note: '提案已丢弃' }, null, 2) + '\n';
      const sr = await ghPutFile(token, 'retrieval-status.json', st0, 'chore: 检索状态复位 idle', pick('retrieval-status.json'));
      const failed = [];
      if (!dc.ok) failed.push('proposed-changes.json');
      if (!dd.ok) failed.push('proposed-data.json');
      if (!sr.ok) failed.push('retrieval-status.json');
      if (failed.length) {
        return { status: 502, body: JSON.stringify({ message: '部分文件未清理成功：' + failed.join('、') + '，请重试一次' }) };
      }
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
    // 一次列举拿到所有 sha，避免逐个 GET 时把 data.json / proposed-data.json 整份下载下来导致超时
    const shaMap = await ghListRootShas(token);
    const pick = (n) => (shaMap ? (shaMap[n] || null) : undefined);
    // 1) 写回 data.json
    const dataStr = JSON.stringify(data, null, 2) + '\n';
    const r1 = await ghPutFile(token, 'data.json', dataStr, 'chore: 应用已确认的检索提案（人工逐条确认）', pick('data.json'));
    if (!r1.ok) {
      let msg = '写入 data.json 失败';
      try { const j = JSON.parse(r1.body); if (j && j.message) msg += '：' + j.message; } catch (e) {}
      return { status: 502, body: JSON.stringify({ message: msg }) };
    }
    // 2) 写变更记录（网页「最近更新」面板读取）
    if (summary && typeof summary === 'object') {
      const sumStr = JSON.stringify(summary, null, 2) + '\n';
      await ghPutFile(token, 'update-summary.json', sumStr, 'chore: 更新变更记录（已确认提案）', pick('update-summary.json'));
    }
    // 方案A：把应用记录也合并进云端「手动记录」(user-edits.json)，保证换设备/换浏览器可见，且与本地 edits.log 用同一 key 去重
    const appliedLog = Array.isArray(payload.appliedLog) ? payload.appliedLog : [];
    if (appliedLog.length) {
      const ue = await ghGetContent(token, 'user-edits.json');
      const ueObj = ue.obj && typeof ue.obj === 'object' ? ue.obj : { log: [], overrides: {}, deleted: [], manual: [] };
      if (!Array.isArray(ueObj.log)) ueObj.log = [];
      const seen = new Set(ueObj.log.map(e => e && e.key));
      for (const e of appliedLog) {
        if (e && e.key && e.op && e.name && e.ts && !seen.has(e.key)) { ueObj.log.push(e); seen.add(e.key); }
      }
      if (ueObj.log.length > 500) ueObj.log = ueObj.log.slice(-500); // 防无限膨胀
      ueObj.ts = Date.now();
      const ueStr = JSON.stringify(ueObj, null, 2) + '\n';
      await ghPutFile(token, 'user-edits.json', ueStr, 'chore: 记录应用提案到变更历史（累积）', ue.sha);
    }
    // 3) 处理提案文件：还有保留项（未采纳的提案 或 待核实线索）就改写，否则删除
    const keepRejected = Array.isArray(payload.rejected) ? payload.rejected : [];
    if ((Array.isArray(remaining) && remaining.length > 0) || keepRejected.length > 0) {
      const keepStr = JSON.stringify({
        generatedAt: (payload.generatedAt || new Date().toISOString().slice(0, 10)),
        pending: (Array.isArray(remaining) ? remaining.length : 0),
        changes: (Array.isArray(remaining) ? remaining : []),
        rejected: keepRejected
      }, null, 2) + '\n';
      await ghPutFile(token, 'proposed-changes.json', keepStr, 'chore: 保留未确认的检索提案', pick('proposed-changes.json'));
    } else {
      await ghDeleteFile(token, 'proposed-changes.json', 'chore: 清理已处理的检索提案', pick('proposed-changes.json'));
    }
    await ghDeleteFile(token, 'proposed-data.json', 'chore: 清理提案数据快照', pick('proposed-data.json'));
    // 4) 复位检索状态
    const st = JSON.stringify({
      status: 'idle',
      appliedAt: new Date().toISOString(),
      note: '提案已人工确认并应用'
    }, null, 2) + '\n';
    await ghPutFile(token, 'retrieval-status.json', st, 'chore: 检索状态复位 idle', pick('retrieval-status.json'));

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

// ===== 0-c：批量链接核验（部署在广州，稳定访问 gov.cn / openstd / cfsa）=====
// GitHub Actions 的 runner 在境外，访问国内官网常超时 → 真条目被误判「无法验证」塞进人工复核栏。
// 这里把链接核验挪到广州 SCF：从国内网络真实打开页面，判断 alive/dead/uncertain + 死页，
// 再由检索脚本据此分类，从而消除境外超时造成的误杀。
const PROBE_DEAD_MARKERS = ["搜索不到", "未找到", "页面不存在", "没有检索到",
  "无相关结果", "内容不存在", "不存在的页面", "没有找到"];

function probeIsHomepage(u) {
  try {
    const p = new URL(u);
    const path = (p.pathname || "").replace(/\/+$/, "");
    return path === "" && !p.search;
  } catch (e) { return false; }
}

async function probeFetchText(url, maxBytes) {
  maxBytes = maxBytes || 150000;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const r = await fetch(url, {
      method: "GET", redirect: "follow",
      headers: { "User-Agent": "Mozilla/5.0 (compatible; laws-probe/1.0)", "Accept": "text/html,application/xhtml+xml,*/*" },
      signal: ctrl.signal
    });
    const buf = Buffer.from(await r.arrayBuffer()).slice(0, maxBytes);
    clearTimeout(timer);
    for (const enc of ["utf-8", "gbk", "gb18030", "latin-1"]) {
      try { return buf.toString(enc); } catch (e) {}
    }
    return buf.toString("utf-8");
  } catch (e) {
    clearTimeout(timer);
    return null;
  }
}

function probeIsDeadPage(text) {
  if (!text) return false;
  return PROBE_DEAD_MARKERS.some(m => text.includes(m));
}

async function probeOne(url) {
  url = (url || "").trim();
  if (!url) return { url, status: "dead", httpStatus: 0, reason: "空链接" };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const r = await fetch(url, {
      method: "GET", redirect: "follow",
      headers: { "User-Agent": "Mozilla/5.0 (compatible; laws-probe/1.0)", "Accept": "*/*", "Range": "bytes=0-0" },
      signal: ctrl.signal
    });
    clearTimeout(timer);
    const finalUrl = r.url || url;
    const code = r.status;
    if (code >= 400) return { url, status: "dead", httpStatus: code, reason: "HTTP " + code };
    if (probeIsHomepage(finalUrl) && !probeIsHomepage(url)) {
      return { url, status: "dead", httpStatus: code, reason: "跳回首页，原链接已失效" };
    }
    // 确认可访问，再取正文判断是否死页（openstd 等拼错 hcno 也返 200 但显示「未找到」）
    const text = await probeFetchText(url);
    if (text && probeIsDeadPage(text)) {
      return { url, status: "dead", httpStatus: code, reason: "页面显示「未找到/搜索不到」死页" };
    }
    return { url, status: "alive", httpStatus: code, reason: "" };
  } catch (e) {
    const msg = (e && e.name === "AbortError") ? "超时" : (e && e.message ? e.message : "网络错误");
    return { url, status: "uncertain", httpStatus: 0, reason: msg };
  }
}

async function handleProbeLinks(bodyStr) {
  let payload;
  try { payload = JSON.parse(bodyStr || "{}"); }
  catch (e) { return { status: 400, body: JSON.stringify({ message: "请求体不是合法 JSON" }) }; }
  const urls = Array.isArray(payload.urls) ? payload.urls.map(u => (u || "").trim()).filter(Boolean) : [];
  if (!urls.length) return { status: 400, body: JSON.stringify({ message: "缺少 urls 数组" }) };
  // 串行探测（链接数不多，避免并发打爆目标站，也控制 SCF 内存/耗时）
  const results = [];
  for (const u of urls) {
    results.push(await probeOne(u));
  }
  return { status: 200, body: JSON.stringify({ results }) };
}

// ===== 按号解析 openstd 真实链接（落地腿1）=====
const OPENSTD_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36';
const HCNO_RE = /[0-9A-Fa-f]{32}/g;
const DETACH_RE = /[^A-Za-z0-9]/g;

async function openstdFetchText(url, cookie) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 12000);
  try {
    const headers = { 'User-Agent': OPENSTD_UA, 'Accept': 'text/html,*/*' };
    if (cookie) headers['Cookie'] = cookie;
    const r = await fetch(url, { method: 'GET', redirect: 'follow', headers, signal: ctrl.signal });
    clearTimeout(timer);
    return { status: r.status, text: await r.text(), cookie: r.headers.get('set-cookie') || null };
  } catch (e) {
    clearTimeout(timer);
    return { status: 0, text: '', cookie: null, error: e.message };
  }
}

async function handleResolveOpenstd(bodyStr) {
  let payload;
  try { payload = JSON.parse(bodyStr || "{}"); }
  catch (e) { return { status: 400, body: JSON.stringify({ message: "请求体不是合法 JSON" }) }; }
  const stdNo = (payload.stdNo || "").trim();
  if (!stdNo) return { status: 400, body: JSON.stringify({ message: "缺少 stdNo" }) };
  if (!/^\s*GB[\s/T]*\d/i.test(stdNo)) {
    return { status: 200, body: JSON.stringify({ ok: false, hcno: "", link: "", verified: false, reason: "非 GB 国标，不走 openstd" }) };
  }
  // 1) 取会话 cookie（openstd 搜索需先到 /bzgk/gb/index 拿 cookie）
  const idx = await openstdFetchText('https://openstd.samr.gov.cn/bzgk/gb/index', null);
  const cookie = idx.cookie || null;
  // 2) 搜索：关键词 = 全称 + 编号数字核心（如 22239），openstd 对数字核心命中最稳
  const norm = stdNo.replace(/\s+/g, '');
  const core = (stdNo.match(/\d+(?:\.\d+)?/) || [''])[0];
  const queries = Array.from(new Set([norm, core].filter(Boolean)));
  const normIn = norm.replace(DETACH_RE, '').toUpperCase();
  for (const q of queries) {
    const url = 'https://openstd.samr.gov.cn/bzgk/std/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=' + encodeURIComponent(q);
    const sr = await openstdFetchText(url, cookie);
    if (!sr.text) continue;
    const hcnos = Array.from(new Set(sr.text.match(HCNO_RE) || []));
    if (!hcnos.length) continue;
    // 3) 详情页核对标准号（确定性判据：详情页正文确含该编号）
    for (const hcno of hcnos.slice(0, 6)) {
      const det = await openstdFetchText('https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=' + hcno, cookie);
      if (det.text && normIn && normIn.includes(core.replace(DETACH_RE, '').toUpperCase()) &&
          det.text.replace(DETACH_RE, '').toUpperCase().includes(normIn)) {
        return { status: 200, body: JSON.stringify({
          ok: true,
          hcno,
          link: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=' + hcno,
          verified: true,
          reason: "openstd 官网返回并校验通过"
        }) };
      }
    }
  }
  return { status: 200, body: JSON.stringify({ ok: false, hcno: "", link: "", verified: false, reason: "未从 openstd 解析到该标准号（可能无此号/反爬/超时）" }) };
}

// ===== 取页面正文（落地验证层：reconcile 经此从国内 IP 真实打开官方页）=====
// 请求体：{ url: "https://..." }；返回：{ ok: true, text: "<正文>", httpStatus } 或 { ok: false, reason }
// 注意：此端点从腾讯云广州 SCF（国内 IP）发起请求，可稳定访问 gov.cn / openstd / npc.gov.cn，
// 避免 GitHub 境外 runner 直连被墙/超时。openstd 需先到首页取会话 cookie 再打开详情/列表页。
async function handleFetch(bodyStr) {
  let payload;
  try { payload = JSON.parse(bodyStr || "{}"); }
  catch (e) { return { status: 400, body: JSON.stringify({ message: "请求体不是合法 JSON" }) }; }
  const url = (payload.url || "").trim();
  if (!url) return { status: 400, body: JSON.stringify({ message: "缺少 url" }) };
  try {
    const u = new URL(url);
    const host = (u.hostname || "").toLowerCase();
    if (!(host.endsWith("gov.cn") || host.endsWith("samr.gov.cn") || host.endsWith("npc.gov.cn") ||
          host.endsWith("cfsa.net.cn") || host.startsWith("www.") || host.includes("."))) {
      return { status: 400, body: JSON.stringify({ message: "不在允许域名范围" }) };
    }
    let cookie = null;
    if (host.endsWith("openstd.samr.gov.cn")) {
      const idx = await openstdFetchText('https://openstd.samr.gov.cn/bzgk/gb/index', null);
      cookie = idx.cookie || null;
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 15000);
    const headers = { 'User-Agent': OPENSTD_UA, 'Accept': 'text/html,application/xhtml+xml,*/*' };
    if (cookie) headers['Cookie'] = cookie;
    const r = await fetch(url, { method: 'GET', redirect: 'follow', headers, signal: ctrl.signal });
    clearTimeout(timer);
    const text = await r.text();
    if (!text) return { status: 200, body: JSON.stringify({ ok: false, reason: "空正文" }) };
    return { status: 200, body: JSON.stringify({ ok: true, text, httpStatus: r.status }) };
  } catch (e) {
    const msg = (e && e.name === "AbortError") ? "超时" : (e && e.message ? e.message : "网络错误");
    return { status: 200, body: JSON.stringify({ ok: false, reason: msg }) };
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
  if (pathname === '/probe-links') {
    if (method !== 'POST') return { status: 405, body: JSON.stringify({ message: '仅支持 POST' }) };
    return await handleProbeLinks(bodyStr);
  }
  if (pathname === '/resolve-openstd') {
    if (method !== 'POST') return { status: 405, body: JSON.stringify({ message: '仅支持 POST' }) };
    return await handleResolveOpenstd(bodyStr);
  }
  if (pathname === '/fetch') {
    if (method !== 'POST') return { status: 405, body: JSON.stringify({ message: '仅支持 POST' }) };
    return await handleFetch(bodyStr);
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
