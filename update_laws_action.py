#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律法规 / 产品标准 清单自动更新脚本（在 GitHub Actions 环境中运行）
============================================================
- 使用 智谱 GLM（国内可访问、有免费额度）自带的 web_search 联网检索能力
- 检索最近中国新发布 / 修订 / 废止的法律法规与产品标准（GB/T、行业标准、ISO 等）
- 默认 DRAFT_MODE=True：只产出「提案」(proposed-changes.json + proposed-data.json)，
  **绝不改动 data.json**；需用户在网页端逐条确认后，由 SCF /apply-proposed 写入。
  待提示词质量稳定可靠后，将 DRAFT_MODE 改为 False（或环境变量 DRAFT_MODE=false）
  即可恢复全自动直写 data.json。
- 写出 retrieval-status.json（前端状态轮询用）：draft_ready（草稿待确认）/ success（直更成功）。

依赖环境变量：
  ZHIPU_API_KEY  (必填)  在 https://open.bigmodel.cn 免费申请的 API Key
  MODEL            (可选)  模型名，默认 glm-4-plus（智谱最强模型，事实准确性明显优于 air）
  DRAFT_MODE       (可选)  true(默认)=只出提案不动数据；false=直写 data.json
  SYNC_PROXY       (可选)  国内腾讯云 SCF 代理地址（含 https://）。配置后，链接核验改由
                      广州境内 SCF 执行，消除 GitHub 境外 runner 访问国内官网超时造成的误杀；
                      不配置则沿用旧逻辑（本地逐项探测）。
"""

import os
import json
import re
import sys
import copy
import subprocess
import traceback
import urllib.request
import urllib.parse
import ssl
from datetime import date, datetime
from collections import Counter

try:
    from zhipuai import ZhipuAI
except ImportError:
    ZhipuAI = None  # 本地离线自检时可缺；生产环境(GitHub Actions)必装，main() 会校验

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data.json")
USER_EDITS_PATH = os.path.join(ROOT, "user-edits.json")
SUMMARY_PATH = os.path.join(ROOT, "update-summary.json")
RETRIEVAL_STATUS_PATH = os.path.join(ROOT, "retrieval-status.json")
PROPOSED_CHANGES_PATH = os.path.join(ROOT, "proposed-changes.json")
PROPOSED_DATA_PATH = os.path.join(ROOT, "proposed-data.json")
REPORT_PATH = os.path.join(ROOT, "retrieval-report.json")
REPORT_MD_PATH = os.path.join(ROOT, "retrieval-report.md")

# ===== 闸门：默认草稿模式（只出提案，不动数据）=====
DRAFT_MODE = os.environ.get("DRAFT_MODE", "true").lower() not in ("0", "false", "no")

# ===== 分诊自救台账：记录"哪些条目的链接是系统按官方渠道自动解析补上的" =====
# 用途是测量：若此表持续有内容而"编造URL"分类归零，说明提示词训练已见效。
_RESOLVE_LOG = []

# ===== 质量测量计数器（Step⑤）：每轮检索统计 4 类问题，报告里直接数、看改善 =====
#   fake_abolish        —— 模型称「已废止/替代」但官方页无任何依据，被 Step② 直接丢弃（伪废止·伪替代）
#   publish_date_misfill—— 模型把「发布日期」填进「实施日期」，被 Step① 纠正清空（发布日期误填）
#   dup_rereport        —— 模型重报清单里【早已做过】的变更（无实质变更/已废止再报），被当作重复拦下
#   cross_file          —— Step③ 从新文件「代替」声明跨文件推断命中的废止条数
_METRICS = {"fake_abolish": 0, "publish_date_misfill": 0, "dup_rereport": 0, "cross_file": 0}

# ===== 链接校验与回退（仅对新增/变更的少量链接触发，低资源） =====
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def is_homepage(url):
    if not url:
        return False
    try:
        p = urllib.parse.urlparse(str(url).strip())
        return (p.path or "").rstrip("/") == ""
    except Exception:
        return False


def probe_link(url, timeout=10):
    """三态探活。返回 True=确认可访问 / False=确认失效(404等) / None=无法判定(超时、连不上)。
    做成三态是为了避免 GitHub 服务器在境外访问国内官网超时，把本来正确的条目一律误杀。"""
    url = (url or "").strip()
    if not url:
        return False
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": _UA, "Accept": "*/*", "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            final = r.geturl()
            code = getattr(r, "status", 200)
            if code >= 400:
                return False
            if is_homepage(final) and not is_homepage(url):
                return False   # 跳回首页 = 原链接已失效
            return True
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 406, 429):
            return True        # 官网反爬拦截，页面本身通常存在
        if e.code in (404, 410, 451):
            return False       # 确认失效（编造链接最典型的表现）
        return None            # 5xx 等服务端临时故障，判不了
    except Exception:
        return None            # 超时 / DNS / 连接失败，判不了


def link_alive(url, timeout=10):
    """布尔版：仅在「确认可访问」时为真（写入链接用，从严）。"""
    return probe_link(url, timeout) is True


# ===== 0-c：链接核验挪到国内 SCF（广州），消除境外 runner 超时误杀 =====
# 思路：GitHub Actions 的 runner 在境外，访问 gov.cn / openstd / cfsa 等国内官网经常超时，
# 导致本应「可直接应用」的真条目被误判为「无法自动验证」塞进右栏（人工复核）。
# 改为把链接交给部署在广州的腾讯云 SCF（/probe-links）真实打开核验；
# 国内网络稳定，超时类误杀基本消失。SCF 不可用时自动回退本地逐项探测，行为不变。
PROBE_CACHE = {}  # url -> {state, dead_page_checked, dead_page, reason, via}


def scf_batch_probe(urls, timeout=90, chunk=10):
    """把一批 source_url 交给国内 SCF 探测，结果写入 PROBE_CACHE。
    按 chunk 分批调用，避免单次 SCF 调用耗时过长。仅当 SYNC_PROXY 已配置才生效；
    SCF 调用失败则不动缓存，后续自动回退本地逐项探测（不阻断流程）。"""
    proxy = (os.environ.get("SYNC_PROXY") or "").strip()
    if not proxy or not urls:
        return
    try:
        for i in range(0, len(urls), chunk):
            batch = urls[i:i + chunk]
            req = urllib.request.Request(
                proxy.rstrip("/") + "/probe-links",
                data=json.dumps({"urls": batch}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                j = json.loads(r.read().decode("utf-8"))
            for it in (j.get("results") or []):
                u = (it.get("url") or "").strip()
                st = it.get("status")
                if u and st in ("alive", "dead", "uncertain"):
                    PROBE_CACHE[u] = {
                        "state": {"alive": True, "dead": False, "uncertain": None}.get(st),
                        "dead_page_checked": True,
                        "dead_page": (st == "dead"),
                        "reason": it.get("reason", ""),
                        "via": "scf",
                    }
        print(f"  [0-c] 国内 SCF 探测完成，共缓存 {len(PROBE_CACHE)} 条链接结果")
    except Exception as e:
        # SCF 调用失败：不动缓存，后续自动回退本地逐项探测（不阻断流程）
        print(f"  [0-c] 国内 SCF 探测不可用，回退本地探测：{e}")


def scf_probe_link(url):
    """三态探活，优先取 PROBE_CACHE（来自国内 SCF），未命中则本地回退。
    返回 dict: {state: True/False/None, dead_page_checked, dead_page, reason, via}"""
    url = (url or "").strip()
    cached = PROBE_CACHE.get(url)
    if cached is not None:
        return cached
    local = probe_link(url)
    res = {"state": local, "dead_page_checked": False, "dead_page": None,
           "reason": "", "via": "local"}
    PROBE_CACHE[url] = res
    return res


# =====================================================================
# 链接分诊解析框架（多源 / 通用，不写死任何具体标准号）
# ---------------------------------------------------------------------
# 设计目标（对应「让 GLM 不必再编 URL」的腿1落地）：
#   GLM 只负责判断"这条要不要更新/废止"，链接这一环由脚本按"这条该去哪个官网"
#   确定性地查回真实链接，而不是由模型凭记忆拼。
# 分诊优先级（与清单铁律「链接以现有链接为准」一致）：
#   1) 现有有效链接 → 直接复用（先核验活体+非死页），不重查、不瞎编；
#   2) 有标准号 → 按"类别→官网源"通用映射查（国标→openstd / 食安→cfsa / 行业站→TODO）；
#   3) 无号法规 → 按"名称+发布部门"去对应部委/地方站查（TODO，通用接口预留）。
# 说明：本框架目前只"提供能力"，尚未接入活检索流程（接入为独立步骤，需另行确认）。
# =====================================================================

# 类别→官网源 的通用映射（不写死任何具体标准号，只按前缀/类别识别"去哪类站"）
# 食安国标(GB 4806.x / 31604.x) openstd 不收录，归 cfsa；其余 GB/T、GB 国标归 openstd。
_FOOD_STD_RE = re.compile(r"GB\s*4806|GB\s*31604", re.IGNORECASE)
_GB_STD_RE = re.compile(r"^\s*GB[\s/T]*\d", re.IGNORECASE)
_HCNO_RE = re.compile(r"[0-9A-Fa-f]{32}")
_OPENSTD_SEARCH = "https://openstd.samr.gov.cn/bzgk/std/std_list"
_OPENSTD_DETAIL = "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno="


def domestic_fetch(url, timeout=20, max_bytes=200000):
    """取页面正文：优先走已配置的国内 SCF 代理（SYNC_PROXY）执行真实打开，
    否则回退本地 fetch_text。返回 (text_or_None, via)。
    注：当前 SCF 仅部署了 /probe-links，/fetch 端点为落地时新增；
    未部署时自动回退本地（GitHub 海外 runner 可能超时，属已知限制，落地后消除）。"""
    proxy = (os.environ.get("SYNC_PROXY") or "").strip().rstrip("/")
    if proxy:
        try:
            req = urllib.request.Request(
                proxy + "/fetch",
                data=json.dumps({"url": url}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                j = json.loads(r.read().decode("utf-8"))
            if j.get("ok") and j.get("text") is not None:
                return j.get("text"), "scf"
        except Exception as e:
            print(f"  [分诊] 国内 SCF /fetch 不可用，回退本地：{e}")
    return fetch_text(url, timeout=timeout, max_bytes=max_bytes), "local"


def _openstd_search_session(query):
    """按关键词确定性检索 openstd 真实结果页（无需浏览器，纯 HTTP）。
    实测可用姿势：先 GET /bzgk/gb/index 取会话 cookie，再
    GET /bzgk/std/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=<关键词>。
    关键词可为编号数字核心(22239)或全称(GB/T 22239-2019)，均命中。
    返回检索页正文；失败返回 None。"""
    s = (query or "").strip()
    if not s:
        return None
    cj = urllib.request.HTTPCookieProcessor()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    op = urllib.request.build_opener(cj, urllib.request.HTTPSHandler(context=ctx))
    try:
        op.open(urllib.request.Request("https://openstd.samr.gov.cn/bzgk/gb/index",
                                       headers={"User-Agent": _UA}), timeout=15)
    except Exception:
        pass
    url = (_OPENSTD_SEARCH + "?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2="
           + urllib.parse.quote(s))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA,
                 "Accept": "text/html,*/*",
                 "Referer": "https://openstd.samr.gov.cn/bzgk/gb/index"})
    try:
        with op.open(req, timeout=20) as r:
            return r.read(400000).decode("utf-8", "replace")
    except Exception:
        return None


def _resolve_openstd_via_proxy(proxy, std_no, timeout=25):
    """调用国内 SCF 代理 /resolve-openstd 真实从国内 IP 搜索并校验。
    返回 {ok, hcno, link, verified, reason}；调用失败返回 ok=False。"""
    try:
        req = urllib.request.Request(
            proxy + "/resolve-openstd",
            data=json.dumps({"stdNo": std_no}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "reason": "代理调用失败：" + str(e)}


def resolve_openstd(std_no, retries=1, max_detail_checks=6):
    """按标准号确定性解析 openstd 真实详情页链接（hcno）。
    步骤：检索→从列表页提取 hcno(32位十六进制)→打开详情页校验官方标准号一致。
    返回 dict: {link, hcno, verified, reason}。查不到/校验失败返回 link=''（绝不编造）。
    注：为低消耗与防超时，每个检索变体最多校验前 max_detail_checks 个 hcno；
    详情页核对是确定性保障，故宁可少查不可错报。"""
    out = {"link": "", "hcno": "", "verified": False, "reason": "", "method": "openstd"}
    if not _GB_STD_RE.search(std_no or ""):
        out["reason"] = "非 GB 国标，不走 openstd"
        return out
    # 优先走国内 SCF 代理 /resolve-openstd（真实从国内 IP 搜索，海外 runner 搜不到）
    proxy = (os.environ.get("SYNC_PROXY") or "").strip().rstrip("/")
    if proxy:
        pr = _resolve_openstd_via_proxy(proxy, std_no)
        if pr.get("ok"):
            out.update({"link": pr.get("link", ""), "hcno": pr.get("hcno", ""),
                        "verified": True, "reason": "国内代理解析：" + pr.get("reason", "")})
            return out
        out["reason"] = "国内代理未命中（" + pr.get("reason", "") + "），回退本地"
    # 本地 urllib 实现（海外 runner 可能失败，属已知限制；落地代理后消除）
    norm = re.sub(r"[^A-Z0-9]", "", std_no.upper())
    for q in _openstd_query_variants(std_no):
        for _ in range(retries + 1):
            html = _openstd_search_session(q)
            if not html:
                out["reason"] = "openstd 检索无返回（海外超时/波动）"
                continue
            # 列表页 hcno 为 32 位十六进制（JS showInfo('...') 写法），去重保序
            hcnos = list(dict.fromkeys(_HCNO_RE.findall(html)))
            if not hcnos:
                out["reason"] = "openstd 检索结果未含 hcno（可能无此号或反爬）"
                continue
            # 逐个 hcno 抓详情页校验标准号，取第一个"详情页确含该号"的（有限次，防超时）。
            # 注意：openstd 详情页正文含"尚未收录"等免责声明字样，is_dead_page 会误判有效页为死页；
            # 这里以"详情页确含该标准号"作为确定性判据（含号即非死页），不依赖 is_dead_page。
            found = False
            for hcno in hcnos[:max_detail_checks]:
                text = None
                for _attempt in range(2):  # openstd 详情页偶发返回空，重试一次
                    t = fetch_text(_OPENSTD_DETAIL + hcno, timeout=8)
                    if t:
                        text = t
                        break
                if text and norm in re.sub(r"[^A-Z0-9]", "", text.upper()):
                    out["link"] = _OPENSTD_DETAIL + hcno
                    out["hcno"] = hcno
                    out["verified"] = True
                    out["reason"] = "openstd 官网返回并校验通过"
                    found = True
                    break
            if found:
                return out
            out["reason"] = "详情页标准号与输入不符（hcno 取错或未在前%d条内）" % max_detail_checks
        # 该 query 变体未命中，换下一个变体再试
    return out


def _openstd_query_variants(std_no):
    """生成检索查询变体（通用，不写死具体标准号）。优先用"编号数字核心"（如 22239），
    其次用"去空格斜杠全称"（如 GBT22239-2019）。openstd 对数字核心命中最稳。"""
    s = (std_no or "").strip()
    variants = []
    core = re.search(r"\d+(?:\.\d+)?", s)
    if core:
        variants.append(core.group())
    compact = re.sub(r"[\s/]", "", s)
    if compact:
        variants.append(compact)
    seen, out = set(), []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _source_kind(entry, table):
    """通用识别该条目该去哪类官网查（返回 'reuse'/'openstd'/'cfsa'/'name_query'/'none'）。
    不写死任何具体标准号，只按"是否有现有链接 / 标准号前缀 / 类别"判断。"""
    link = (entry.get("link") or "").strip()
    if link and has_valid_official_link(link):
        return "reuse"
    stdno = (entry.get("stdNo") or "").strip()
    name = (entry.get("name") or "").strip()
    if stdno:
        if _FOOD_STD_RE.search(stdno + " " + name):
            return "cfsa"
        if _GB_STD_RE.search(stdno):
            return "openstd"
        # 其它前缀的标准（如行业/地方标准）目前无对应解析器 → 归待补
        return "none"
    # 无号法规：按名称+部门去部委/地方站查（TODO 落地，先归 name_query 占位）
    return "name_query"


def resolve_link_for_entry(entry, table, verify_existing=True):
    """主分诊入口：给定清单条目（含 name/stdNo/link/category），返回真实官方链接。
    返回 dict: {link, method, verified, reason}。查不到返回 link=''（留待人工补，绝不编造）。"""
    kind = _source_kind(entry, table)
    link = (entry.get("link") or "").strip()

    if kind == "reuse":
        if verify_existing:
            st = scf_probe_link(link)
            alive = (st.get("state") is True)
            txt = fetch_text(link, timeout=12) if not alive else None
            if alive or (txt and not is_dead_page(txt)):
                return {"link": link, "method": "reuse_existing",
                        "verified": True, "reason": "复用现有有效链接并核验通过"}
            return {"link": link, "method": "reuse_existing",
                    "verified": False, "reason": "现有链接核验失败（死链/超时），建议重查"}
        return {"link": link, "method": "reuse_existing",
                "verified": False, "reason": "复用现有链接（未核验）"}

    if kind == "openstd":
        return resolve_openstd(entry.get("stdNo") or "")

    if kind == "cfsa":
        # 食安国标 openstd 不收录，归 cfsa；cfsa 反爬，落地时由国内代理处理
        return {"link": "", "method": "cfsa",
                "verified": False, "reason": "食安国标(cfsa)解析待落地：留空待补"}

    if kind == "name_query":
        # 无号法规按名称+部门查（落地时由国内代理抓对应部委站）；当前不编造
        return {"link": "", "method": "name_query",
                "verified": False, "reason": "无号法规按名称+部门查询待落地：留空待补"}

    return {"link": "", "method": "none",
            "verified": False, "reason": "无对应解析源，留空待补"}


def _change_version_changed(change, target):
    """本次变更是否涉及版本号变化（改版）。改版时旧条目链接指向旧版正文，严禁复用。
    通用判断：比对标准号主键与完整版本号（含年份），不写死任何具体标准。"""
    if not target:
        return False
    new_no = (change.get("stdNo") or "").strip()
    old_no = (target.get("stdNo") or "").strip()
    ka, kb = _std_key(new_no), _std_key(old_no)
    if ka and kb and ka != kb:
        return True
    # 年份变化（GB/T 4288-2018 → GB/T 4288-2025）也是改版
    fa = _parse_std_full(new_no) or _parse_std_full(change.get("name") or "")
    fb = _parse_std_full(old_no) or _parse_std_full(target.get("name") or "")
    if fa and fb and fa != fb:
        return True
    return False


def resolve_source_url_for_change(table, change, target):
    """把「通用多源分诊」接进活检索：GLM 给不出/给错依据链接时，由本系统按
    标准号(openstd 按号解析)或复用清单现有链接，确定性地拿到真实官方链接。
    —— 目的是让 GLM 不必再编 URL：它只负责说清"哪个字段改了、依据是什么"，
    取链接这件确定性的事交给代码做。解析不到就返回 link=''（绝不编造）。"""
    # 标准号来源优先级：本条 stdNo → 清单现值 → GLM 给的 source_hint 线索 → 名称里内嵌的编号
    # （source_hint 是提示词里承诺"你留空、系统拿线索去解析"的入口，必须真的用上）
    stdno = ((change.get("stdNo") or "").strip()
             or (target or {}).get("stdNo", "").strip())
    if not stdno:
        # 优先取「带年份的完整标准号」（GB/T 22239-2019）：年份参与详情页核对，能防版本混淆；
        # 取不到年份才退用不带年份的编号（GB/T 22239）。
        for pat in (_STD_FULL_RE, _STD_KEY_RE):
            for cand in (change.get("source_hint") or "", change.get("name") or ""):
                m = pat.search(cand or "")
                if m:
                    stdno = m.group(0).strip()
                    break
            if stdno:
                break
    entry = {
        "name": (change.get("name") or "").strip(),
        "stdNo": stdno,
        "category": (change.get("category")
                     or (target or {}).get("category", "")),
        "link": "",
    }
    # 复用清单现有链接：仅「非改版」时允许（改版须提供新版自身链接）
    if target and not _change_version_changed(change, target):
        entry["link"] = (target.get("link") or "").strip()
    try:
        return resolve_link_for_entry(entry, table)
    except Exception as e:
        return {"link": "", "method": "error", "verified": False,
                "reason": "分诊解析异常：" + str(e)}


def _confirm_claim_on_page(change, target, url):
    """拿系统解析出的真实官方页，反向核对 GLM 声称的变更内容。
    返回 (是否确认, 说明)。取不到正文或页面无该日期 → (False, 原因)，
    交人工复核，绝不当成已确认（宁可少报，不可错报）。"""
    text = fetch_text(url, timeout=12)
    if not text:
        return False, "系统已解析出真实官方链接，但正文取不到（境外超时/反爬），请人工点开确认"
    # 标准类：解析页标准号须与本条一致，防张冠李戴
    stdno = (change.get("stdNo") or "").strip() or (target or {}).get("stdNo", "")
    if stdno and _source_version_mismatch(text, stdno):
        return False, "系统解析出的官方页标注了其它版本号，疑似版本混淆，请人工确认"
    # 实施日期防御：以官方页正文『实施日期』为权威，自动纠正/留空（显式排除『发布日期』）
    page_date, why_ed = _rectify_effective_date(change, url, target=target, text=text)
    if page_date and _ymd(change.get("effectiveDate")) == _ymd(page_date):
        return True, f"链接由系统按官方渠道自动解析补正，且实施日期 {page_date} 与官方页正文一致（{why_ed}）"
    # page_date 为空 = 官方页未标注实施日期（或版本混淆）：交人工复核，不默认确认
    return False, (why_ed or "官方页未能读出实施日期，请人工确认")


def _rectify_effective_date(change, url, target=None, text=None):
    """实施日期防御：以官方页正文『实施日期』为权威，显式排除『发布日期』。
    模型把发布日期填进实施日期时，自动纠正为正文实施日期；页面无实施日期时清空留待人工核。
    返回 (修正后日期或None, 说明)。"""
    if text is None:
        text = fetch_text(url, timeout=12)
    if not text:
        return None, "官方页正文取不到，实施日期无法自动核对"
    stdno = (change.get("stdNo") or "").strip() or (target or {}).get("stdNo", "")
    if stdno and _source_version_mismatch(text, stdno):
        return None, "官方页标注了其它版本号，疑似版本混淆，实施日期未自动修改"
    page_date = _extract_effective_date(text)   # 只匹配『实施日期』，绝不会取到发布日期
    if page_date:
        claimed = _ymd(change.get("effectiveDate"))
        if claimed and claimed != _ymd(page_date):
            change["effectiveDate"] = page_date
            return page_date, f"实施日期已按官方页正文修正为 {page_date}（原称 {claimed}）"
        if not claimed:
            change["effectiveDate"] = page_date
            return page_date, f"实施日期按官方页正文补为 {page_date}"
        return page_date, "实施日期与官方页正文一致"
    # 页面没有『实施日期』：确认是否只有『发布日期』——绝不能把发布日期当实施日期
    pub = _extract_publish_date(text)
    claimed = _ymd(change.get("effectiveDate"))
    if claimed:
        change["effectiveDate"] = ""   # 模型所填（多为发布日期）清空，留待人工核
        if pub and claimed == _ymd(pub):
            _METRICS["publish_date_misfill"] += 1
            return None, "官方页只标注发布日期、未标注实施日期，已把误填的实施日期清空待核"
        return None, "官方页未标注实施日期，原填实施日期已清空待核"
    return None, "官方页未标注实施日期，无法自动填写"


def _confirm_status_on_page(change, target, url):
    """状态/废止/替代证据核对（Step②）：称某条『已废止』或带『替代关系』时，
    拿真实官方页正文核对——正文必须出现『废止/代替』等字样，且出现本标准号（防张冠李戴）。
    返回三态：
      ("ok",    说明)          —— 有依据，放行；
      ("discard",原因)          —— 页面取到了但【无任何废止依据】，直接丢弃、不提出（用户要求：没依据别提废止）；
      ("review", 原因)          —— 页面取不到/无法核实（超时），降级人工复核，不自动采信也不误杀。
    注意：旧标准自己的页面通常不写『废止』，废止信号只在替代它的新文件里——
    本函数只核对【所引官方页】是否有据；跨文件推断（有依据）见 Step③。"""
    status = (change.get("status") or "").strip()
    replaced = (change.get("replacedBy") or "").strip()
    abolish = (change.get("abolishDate") or "").strip()
    if status != "已废止" and not replaced and not abolish:
        return "ok", "非废止/替代类变更，无需正文废止词核对"
    # 重复重报守卫：清单里该条本就已是废止，模型又来报废止 = 重报早已做过的变更，
    #   直接丢弃、且不计入 fake_abolish（改由 dup_rereport 计数，避免重复计数）。
    if status == "已废止" and target and (target.get("status") or "") == "已废止":
        return "discard", "清单里该条目本就标记已废止，模型又报一次废止 = 重复重报，直接丢弃（不提出）"
    text = fetch_text(url, timeout=12)
    if not text:
        return "review", "官方页正文取不到，所称废止/替代无法自动核实，请人工点开确认"
    stdno = (change.get("stdNo") or "").strip() or (target or {}).get("stdNo", "")
    # 搜废止/代替类关键词（含『代替/替代/被代替/同时废止/作废』）
    kw = re.search(r"(废止|代替|替代|被代替|同时废止|作废|修订并代替)", text)
    if not kw:
        _METRICS["fake_abolish"] += 1
        return "discard", "官方页正文未出现「废止/代替」等字样，所称废止/替代无任何可核实依据，直接丢弃（不提出）"
    # 防张冠李戴：关键词附近应出现本标准号（或所称被替代号），否则疑似拿错文件
    if stdno and stdno not in text:
        _METRICS["fake_abolish"] += 1
        return "discard", f"官方页出现了废止/代替字样，但未出现本标准号 {stdno}，疑似张冠李戴，直接丢弃（不提出）"
    return "ok", "官方页正文含废止/代替依据，与所称变更一致"


# ===== 质检关卡：官方域名白名单（不在名单内的链接一律不采信）=====
OFFICIAL_DOMAIN_SUFFIXES = (
    # 国内：政府与部委（gov.cn 已覆盖 npc/samr/miit/mee/mem/cac/customs/mofcom/mps/mohrss/nhc/moj 等全部子域）
    "gov.cn",
    # 国内：非 gov.cn 的官方机构
    "cfsa.net.cn", "cnis.ac.cn", "chinacdc.cn", "sacinfo.org.cn",
    "ttbz.org.cn", "spc.org.cn", "cnca.org.cn", "cqc.com.cn", "srrc.org.cn",
    # 国际/境外官方（产品标准与出口合规会用到）
    "iso.org", "iec.ch", "cenelec.eu", "cen.eu", "etsi.org",
    "europa.eu", "eur-lex.europa.eu", "gesetze-im-internet.de",
    "fcc.gov", "govinfo.gov", "ecfr.gov", "cpsc.gov", "bluetooth.com",
)

# 明显不是正文的链接特征（搜索引擎 / 站内搜索 / 列表页 / 栏目首页）
BAD_URL_PATTERNS = re.compile(
    r"(baidu\.com|google\.|bing\.com|sogou\.com|so\.com|zhihu\.|toutiao\.|sohu\.|163\.com|sina\."
    r"|/search|search\?|/so\?|keyword=|advanced_search|/list|/index\.html?$)", re.I)


def domain_ok(url):
    """质检关卡③：链接域名必须落在官方白名单内。"""
    try:
        host = (urllib.parse.urlparse((url or "").strip()).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAIN_SUFFIXES)


def url_shape_ok(url):
    """质检关卡③（形态）：拒收搜索页/列表页/栏目首页；国标全文页必须带 hcno= 参数；
    且 hcno 不能是编造的（同一 8 位块重复 ≥3 次，如 FFB7A8B3×4）。"""
    u = (url or "").strip()
    if not u or is_homepage(u):
        return False
    if BAD_URL_PATTERNS.search(u):
        return False
    host = (urllib.parse.urlparse(u).hostname or "").lower()
    if "openstd.samr.gov.cn" in host:
        if "hcno=" not in u:
            # 国标平台全文页真实格式必为 ...detail.html?hcno=XXXX，拼出来的一律判为伪造
            return False
        # hcno 必须是 32 位十六进制，否则（长度不符/含非十六进制字符）判伪造
        m = re.search(r"hcno=([0-9A-Fa-f]+)", u, re.I)
        if not m or len(m.group(1)) != 32:
            return False
        # hcno 编造识别：规律重复块/字母数字交替（FFB7A8B3+A8B3A8B3×3、A1B2C3...）一律判伪造
        if _hcno_looks_fabricated(m.group(1)):
            return False
    return True


def url_trusted(url):
    """四重校验：官方域名 + 正文形态 + 真实可访问 + 正文非死页。任一不过即不采信。"""
    u = (url or "").strip()
    if not u:
        return False
    if not (domain_ok(u) and url_shape_ok(u)):
        return False
    st = probe_link(u)
    if st is False:
        return False
    # 确认可访问时再查正文是否为死页；超时(None)保守放行，避免误杀好链接
    if st is True and is_dead_page(fetch_text(u)):
        return False
    return True


# 正文内容探测：openstd 等平台对拼错的 hcno 也返回 HTTP 200，但正文显示
# 「搜索不到 / 未找到」，这种死链必须识别，否则会被当成有效链接采信。
DEAD_PAGE_MARKERS = ("搜索不到", "未找到", "页面不存在", "没有检索到",
                     "无相关结果", "内容不存在", "不存在的页面", "没有找到",
                     "尚未收录", "未收录", "不提供")


def fetch_text(url, timeout=10, max_bytes=150000):
    """下载页面正文（限制大小，低消耗）并返回解码文本；失败返回 None。"""
    url = (url or "").strip()
    if not url:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml,*/*"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            raw = r.read(max_bytes)
        for enc in ("utf-8", "gbk", "gb18030", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                pass
        return raw.decode("utf-8", "replace")
    except Exception:
        return None


def is_dead_page(text):
    """正文是否是没有内容的死页（搜索不到 / 未找到等）。"""
    if not text:
        return False
    return any(m in text for m in DEAD_PAGE_MARKERS)


def has_valid_official_link(url):
    """轻量判定：是否为官方域名下的正文页（不联网，仅看域名与形态）。"""
    u = (url or "").strip()
    return bool(u) and domain_ok(u) and url_shape_ok(u)


def _extract_effective_date(text):
    """从标准官方页正文里提取『实施日期』，返回 YYYY-MM-DD；取不到返回 None。
    覆盖多种官方写法：实施日期：YYYY-MM-DD / 实施日期：YYYY年M月D日 / 实施日期为YYYY-MM-DD /
    自YYYY年M月D日起实施(施行) / 自YYYY-MM-DD起实施(施行) / 于YYYY年M月D日实施(施行)。"""
    if not text:
        return None
    patterns = [
        r"实施日期[：:\s为是]*(\d{4})-(\d{2})-(\d{2})",
        r"实施日期[：:\s为是]*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"实施日期[：:\s为是]*(\d{4})/(\d{2})/(\d{2})",
        r"自\s*(\d{4})-(\d{2})-(\d{2})\s*起\s*(实施|施行)",
        r"自\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*起\s*(实施|施行)",
        r"于\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*(实施|施行)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def _extract_publish_date(text):
    """从官方页正文里提取『发布日期』，返回 YYYY-MM-DD；取不到返回 None。
    仅用于实施日期防御：当页面没有『实施日期』时，确认模型所填是否其实是发布日期。
    所有写法都带『发布』字样，绝不会误抓到实施日期。"""
    if not text:
        return None
    patterns = [
        r"发布日期[：:\s]*(\d{4})-(\d{2})-(\d{2})",
        r"发布日期[：:\s]*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"发布于\s*(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*发布",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def _source_name(url):
    """依据官方链接推断来源机构名，用于提案展示。"""
    u = (url or "").strip()
    if "openstd.samr.gov.cn" in u:
        return "国家标准全文公开系统"
    if "std.samr.gov.cn" in u:
        return "行业标准备案公告"
    if "cfsa.net.cn" in u:
        return "国家食品安全风险评估中心"
    if "gov.cn" in u or "gov" in u.split("/")[2].split(".")[-2:][0] if "/" in u else False:
        return "政府部门网站"
    return "官方来源"


def _ymd(s):
    """把各种写法转成 YYYY-MM-DD，无法解析返回 None。"""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    m = re.match(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date().isoformat()
        except Exception:
            return None
    return None


def norm_status(s):
    s = (s or "").strip()
    return {"在用": "现行有效", "废止": "已废止",
            "现行有效": "现行有效", "即将实施": "即将实施",
            "已废止": "已废止"}.get(s, s)


# ===== 根因修复：结论抽取器（GLM 只当检索员，结论 100% 由代码从官方页确定性抽取）=====
def _resolve_new_std_effective_date(new_stdno):
    """被替代标准的真实废止日 = 替代它的新标准实施日（确定性解析新标准官方页取实施日）。取不到返回空字符串。"""
    try:
        entry = {"name": new_stdno, "stdNo": new_stdno, "category": "", "link": ""}
        rs = resolve_link_for_entry(entry, "standards")
        link = (rs.get("link") or "").strip()
        if not (link and domain_ok(link) and url_shape_ok(link)):
            return ""
        txt = fetch_text(link, timeout=8)
        if not txt or is_dead_page(txt):
            return ""
        return _extract_effective_date(txt) or ""
    except Exception:
        return ""


def _extract_conclusions_from_page(text, stdno="", today=None):
    """从官方页正文【确定性】抽取结论字段，返回 dict: effectiveDate/status/abolishDate/replacedBy。
    全部由通用正则/规则得出，绝不编造；取不到的字段为空字符串。规则（不硬编码任何标准号/日期）：
      - 实施日期：复用 _extract_effective_date（只匹配『实施日期』，绝不含『发布日期』）。
      - 状态：页面含 废止/被代替/作废/停止施行/不再施行/明令废止 → 已废止；
              页面含『代替/替代 GB/T X』（真实替代）→ 旧标准已废止（被替代=已废止）；
              以上都无 且 实施日期已给出 → 实施日<=today 现行有效，否则 即将实施；
              以上都无 且 实施日期无 → 空（交人工）。
      - 替代关系：页面『代替/替代 GB/T X』→ 抽 X。
      - 废止日期：页面明写 废止日期 YYYY-MM-DD 用之；否则若被真实替代，尝试解析新标准官方页取其
              实施日（即旧标准真实废止日）；都取不到则空。"""
    eff = _extract_effective_date(text)
    status = ""
    abolish = ""
    replaced = ""
    # 替代关系（通用：代替/替代 + 标准号）
    m_rep = re.search(r"(代替|替代)\s*[《]?\s*(GB[/\s]?T?\s?[0-9]+(?:\.[0-9]+)*\s*-\s*\d{4})", text)
    if not m_rep:
        m_rep = re.search(r"(代替|替代)\s*[《]?\s*([A-Za-z]+[/\s]?\d+(?:\.\d+)*\s*-\s*\d{4})", text)
    if m_rep:
        replaced = m_rep.group(2).strip().upper()   # 保留 "GB/T 4288-2025" 原格式，仅去空格
    # 废止/被代替 信号（涵盖"被替代"与"起废止/废止日期"等明确废止表述）
    has_abolish_word = bool(re.search(
        r"(同时废止|予以废止|现予废止|被代替|停止施行|不再施行|明令废止|予以宣布废止|起废止|废止日期)", text))
    if has_abolish_word:
        status = "已废止"
    elif replaced:
        status = "已废止"          # 被替代 = 已废止（通用，不针对具体标准）
    else:
        if eff:
            status = "现行有效" if (today and _ymd(eff) <= today) else "即将实施"
        else:
            status = ""
    # 废止日期：页面明写
    m_ab = re.search(r"(废止日期|自[^\n]{0,30}?起废止)[：:\s]*(\d{4})-(\d{2})-(\d{2})", text)
    if m_ab:
        abolish = f"{m_ab.group(2)}-{int(m_ab.group(3)):02d}-{int(m_ab.group(4)):02d}"
    elif replaced and stdno:
        # 被真实替代：废止日期 = 新标准实施日（确定性解析新标准官方页取实施日）
        nb = _resolve_new_std_effective_date(replaced)
        if nb:
            abolish = nb
    return {"effectiveDate": eff or "", "status": status,
            "abolishDate": abolish, "replacedBy": replaced}


def reconcile_conclusions(change, target, table, today):
    """【根因修复核心】GLM 检索后只给了"它认为的变更草稿"。本函数拿官方页正文，用通用规则
    确定性抽取 实施日期/状态/废止日期/替代关系，并【覆盖】GLM 的同名字段，使结论 100% 来自
    官方页 + 规则，而非 LLM 生成。
      - 取不到官方正文 / 死链 / 张冠李戴（无可用官方页候选）：交回 check_change 按既有规则处置
        （编造/无链接/死链→整条丢弃），【绝不】改成「人工复核」——否则会把本应丢弃的垃圾塞进
        人工复核栏，反而增加用户核查负担（与"减少人工复核/丢弃"目标相悖）。
      - 仅在「有真实官方页、且 GLM 声称的字段与页面抽不到的结论矛盾」时，才标 _unverified 转人工复核。
    不改动 apply_status_rules（用户确认其状态切换正确，不动）。"""
    stdno = ((change.get("stdNo") or "").strip()
             or (target or {}).get("stdNo", "").strip())
    if not stdno:
        for pat in (_STD_FULL_RE, _STD_KEY_RE):
            for cand in (change.get("source_hint") or "", change.get("name") or ""):
                m = pat.search(cand or "")
                if m:
                    stdno = m.group(0).strip()
                    break
            if stdno:
                break
    # 1) 确定官方页候选 URL：优先 GLM 给的合法 source_url，否则按标准号/复用现有链接确定性解析
    url = (change.get("source_url") or "").strip()
    resolved = False
    if not (url and domain_ok(url) and url_shape_ok(url)):
        rs = resolve_source_url_for_change(table, change, target)
        ru = (rs.get("link") or "").strip()
        if ru and rs.get("verified") and domain_ok(ru) and url_shape_ok(ru):
            url = ru
            resolved = True
        else:
            url = ""                         # 无可用官方页候选
    # 2) 取官方页正文（仅在确有候选时才取；无候选交回 check_change 按「编造/无链接→丢弃」）
    text = fetch_text(url, timeout=12) if url else None
    # 3) 取不到正文：区分「无候选（垃圾）」与「有链接但读取失败（超时）」
    if not text:
        if url:
            # 有真实链接候选但读取失败（超时/被拦截）→ 无法自动核实，转人工复核，不静默丢弃
            change["_unverified"] = True
            change["_unverified_reason"] = "官方页超时/无法读取，所称变更无法自动核实，请人工点开确认"
        # 无候选(url="")：不标 _unverified、不改 source_url，交回 check_change 按「编造/无链接→丢弃」
        return change
    # 4) 死页 / 张冠李戴：该页不能作为依据 → 交回 check_change 按「死链/版本不符→丢弃」处置
    #    （不标 _unverified、不改 source_url，避免把垃圾塞进人工复核栏）
    if is_dead_page(text) or (stdno and _source_version_mismatch(text, stdno)):
        return change
    # 5) 成功：提交确定性解析出的真链接 + 通用抽取结论覆盖 GLM 草稿
    if resolved:
        change["source_url"] = url
        # 同步把官方真链接补进条目的 link 字段（仅当条目原本缺链接/是首页时），
        # 与 apply_change 的链接保护逻辑一致；不改已有深链，避免冲掉人工校对好的链接。
        tgt_link = (((target or {}).get("link", "") or "").strip()) if target else ""
        if not tgt_link or is_homepage(tgt_link):
            change["link"] = url
    derived = _extract_conclusions_from_page(text, stdno, today)
    # 6) 覆盖 GLM 字段：抽到的覆盖；抽不到的按"是否曾声称与清单不同"决定保留待核 or 清空
    for fld in ("effectiveDate", "status", "abolishDate", "replacedBy"):
        dv = (derived.get(fld) or "").strip()
        tv = (target or {}).get(fld, "") if target else ""
        if dv:
            change[fld] = dv                  # 代码抽到的结论覆盖 GLM
        else:
            gv = (change.get(fld) or "").strip()
            if gv and gv != tv:
                change["_unverified"] = True   # 声称了但官方页抽不到 → 交人工核实
                change.setdefault("_unverified_reason",
                                  f"官方页未能核实字段「{fld}」（{gv}），请人工确认")
            else:
                change[fld] = ""               # 无声称或与清单一致 → 清空，避免伪变更
    change["_verified"] = True
    change["_derived"] = derived
    print(f"  [结论抽取] 《{change.get('name')}》实施日={derived.get('effectiveDate') or '-'} "
          f"状态={derived.get('status') or '-'} 废止日={derived.get('abolishDate') or '-'} 替代={derived.get('replacedBy') or '-'}")
    return change


# ===== 检索领域（喂给模型做定向检索）=====
DOMAINS = {
    "环境与职业健康": (
        "环境 / 职业健康安全 / 产品安全 / 社会责任 / 地方法规相关："
        "环境保护法、水/大气/土壤/噪声污染防治、固废污染环境防治、碳排放与节能、生态环境法典、"
        "安全生产法、职业病防治法、劳动法、女职工劳动保护、未成年人/劳工权益（童工、强迫劳动）、"
        "工会法、社会保险、工伤保险、特种设备、危险化学品安全、"
        "消费品安全、产品召回、电器安全、产品质量、"
        "广东/中山等地方法规（保留地方站链接，不换成国家级）"
    ),
    "质量": (
        "质量 / 标准化 / 认证认可相关：产品质量法、计量法、标准化法、认证认可条例、"
        "强制性产品认证(CCC)、标准化发展、质量强国建设"
    ),
    "信息安全": (
        "信息安全相关：网络安全法、数据安全法、个人信息保护法、密码法、"
        "关键信息基础设施安全保护条例、网络数据安全管理条例、"
        "信息安全技术类国家标准(GB/T)、算法推荐/深度合成管理规定、"
        "网络安全审查办法、数据出境安全评估办法"
    ),
    "反恐": (
        "反恐与供应链安全 / 进出口相关：反恐怖主义法、海关法、进出口商品检验法、"
        "出境入境管理法、对外贸易法、海关 AEO 认证、易制毒化学品管理条例、"
        "出口管制、技术性贸易壁垒"
    ),
}

STANDARDS_TEXT = (
    "产品标准相关：与本公司产品有关的强制性国家标准(GB)、推荐性国家标准(GB/T)、行业标准、"
    "国际标准(ISO/IEC)的最新发布、修订、替代、作废。本公司产品：洗衣机（含滚筒洗衣机、波轮洗衣机、干衣机）、"
    "微波炉、小型制冷产品（制冰机、冰沙机、啤酒机、雪沙机、咀嚼冰、车载冰箱 等）。"
    "重点关注标准族：家用和类似用途电器安全(IEC 60335 / GB 4706 系列)、电磁兼容 EMC(GB 4343 / CISPR)、"
    "能效(GB 12021 / ERP)、噪声(GB 19606)、食品接触材料(GB 4806 / GB 31604)、插头插座(GB 1002 / GB 2099)、"
    "无线/蓝牙(中国 SRRC、欧盟 RED、美国 FCC、蓝牙 SIG)、电池、制冷/低温、标准替代关系"
    "（如 GB/T X-202X 替代 GB/T X-201X）、标准实施日期变更、旧标准转为废止/废止日期。"
)

CATEGORY_NAMES = {
    "环境与职业健康": "环境与职业健康",
    "质量": "质量",
    "信息安全": "信息安全",
    "反恐": "反恐",
    "standards": "产品标准",
}

# ===== 通用硬性要求（高要求写死进 GLM 提示词）=====
COMMON_RULES = """（以下为所有检索通用的硬性要求，必须严格遵守，违反任一条都算不合格）

【一、去重：严禁新增已有条目】
- 你拿到的"当前清单已有条目"列表是权威去重基准。任何候选新增项，若其名称与列表中某条相同，或高度相似（互为包含/被包含、仅差"管理""办法""条例""规定"等少量字），一律不得新增，视为已存在。
- 若你判断某已有条目需要更新（修订/废止/新版替代/日期变更），请用 action="update" 或 "abolish"，不要另起一条 add。

【二、链接：必须是能直接看全文的官方文档页】
- 法规/标准的权威来源分布在不同官方渠道，请按条目去找"对的那个"，**不要默认某一个**（尤其不要一看到标准就默认 openstd）。可引用来源类别包括：① 对应部委/主管部门官网及其子站（如 npc.gov.cn、gov.cn、samr.gov.cn、mee.gov.cn、mps.gov.cn 等）；② 地方监管/行业局站（如 xcoss.henan.gov.cn、yjgl.tj.gov.cn 等）；③ 国家标准全文公开系统 openstd.samr.gov.cn（仅当该标准确由其发布、且你拿到真实详情页时）；④ 本清单该条目【已有且能打开的链接】（优先复用，见下条）。只接受直接展示"标题 + 完整条文/全文"的官方页面。
- **优先复用清单里该条目已有的链接**：清单现有链接都是能打开的官方源，除非你确认它确实失效、并在官方站找到验证可打开的正确替代链接，否则保留原链接、不要擅自更换。
- openstd 详情页 URL 必须带 `?hcno=32位十六进制` 参数（形如 `.../newGbInfo?hcno=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`，hcno 为 32 位十六进制）；不带 hcno 的 openstd 链接（如 `.../bzgk/gb/GBXXXX-YYYY`、`.../bzgk/gb/index`）是凭编号硬拼的死链，系统会判为伪造整条丢弃——所以**只有 web_search 真实返回了该 hcno 详情页才用 openstd**，不要自己拼。
- **绝对禁止从记忆/编号拼任何 URL**。link 与 source_url 只能填你**真正在 web_search 实际返回的官方结果里看到**的链接。若检索后没有拿到真实可打开的官方链接：link 填空字符串 + remark 注明「官方链接待补」。对**新增条目(add)**：内容仍会被保留——系统会把它作为一条**可勾选的新增提案**提交给你核准，且链接自动清空待补（核准写入时绝不写入编造链接），你在网页上勾选核准后再补官方链接即可；对**更新/废止条目**，无合格 source_url 则不要提交（编造 URL 必被系统判为伪造整条丢弃，反而把真正有用的变更一起丢掉——宁可少报，不可错报）。
- **条目已有有效链接时，直接复用它，不要另编（但版本号有变化则严禁复用）**：本次清单在『正文链接=已有』的条目，说明已经有能打开的官方链接。若你只变更 status / effectiveDate / remark 等非链接字段，且**标准号/版本号未变**（例如 即将实施→现行有效、补填原本空白的实施日期、加废止日期），source_url 直接填该条目**现有的 link**（它是真实官方正文页，能通过校验），不要去编新的链接；也不要为了"显得有更新"去改 link 字段。⚠️ **若本次变更涉及版本号变化（如条目从 2018 版变为 2025 版、或检索发现"新版替代旧版"），这就是改版——旧条目的链接指向旧版正文，严禁复用旧链接**：新版本必须提供它自身的真实官方链接（source_url 标准号须与新版本号完全一致），否则 link 留空 + remark 注明「官方链接待补」，且新版本应作为"新增条目"处理，而不是改写旧条目的日期去复用旧链接。
- 严禁：搜索引擎结果页、列表页、栏目首页、新闻稿/媒体报道页（除非该新闻稿本身就是官方发布的全文页）。
- ⭐**取链接这件事，你不必硬扛：系统会替你解析（这是本轮最重要的新规则）**。系统已具备「按标准号从国内官方渠道自动解析真实链接」的能力（国内 IP 直连国家标准全文公开系统等官方站，取到真实详情页并核对标准号一致）。因此：
  1) 只要 web_search 真实返回了官方正文链接，就照填 source_url（原样复制，一个字符都不要改动或"补全"）。
  2) **没有真实拿到链接时：source_url 填空字符串**，改为把你掌握的定位线索填进 `source_hint` 字段（例如"GB/T 22239-2019"、"国务院令第XXX号"、"国家网信办2026年第X号公告"、"发布部门+公告标题"）。系统会拿这些线索去官方站按号/按名解析真链接，解析成功后自动补进本条。
  3) **这是对你有利的规则**：编造 URL 的后果是整条被判伪造丢弃（你真正查到的变更也一起没了）；而留空+给线索，系统能把链接补上、这条变更得以保留。所以拿不准时**一律留空填线索，绝不要拼 URL**。
  4) 注意：系统补上链接后，还会拿该官方页反向核对你声称的实施日期等内容。**所以日期/状态仍须来自真实检索，不能靠"反正系统会补链接"就乱填**——核对不上会被标为待人工确认，核对矛盾会被判错报。
- 你提供的 source_url（依据来源）必须亲自确认能显示正文、且不是「搜索不到 / 未找到 / 尚未收录」的死链（部分平台对拼错的编号也返回 200，但正文无内容）；若只是搜索页或死链，source_url 填空字符串并在 remark 注明待补。为某条标准(standards 表)提出的日期/状态变更，其 source_url 指向页面的标准号必须与本条 stdNo 完全一致（如本条是 GB/T 4288-2018 就引用 2018 版页面，绝不用 2025 版页面去改 2018 版）。

【三、日期：必须来自官方文件原文，禁止编造】
- effectiveDate（实施日期）与 abolishDate（废止日期）必须取自官方文件明确写明的日期。
- 查不到确切日期就填 ""（空字符串），绝对不要凭记忆猜测或填错日期。

【四、备注 remark：只允许三类，其余一律不写】
- 类型A（采标）：该标准采用国际标准时，remark 必须原样照抄官网版权原话（"暂不提供在线阅读服务"或"仅提供在线阅读服务"）。无官网原话不得写。
- 类型B（食安待补）：食安国标(GB 4806.x / GB 31604.x)因官方反爬无法自动取链接时，remark 写「【官方链接待替换】cfsa.net.cn官方直链待用户手动补充」。
- 类型C（即将被替代）：旧版仍现行有效、但有新版即将实施时，remark 写"即将被 XX 替代（新标准实施日期 YYYY-MM-DD）"。
- 除上述三类外，remark 一律留空。禁止写"新增法规，属于XX领域""由XX发布"等废话。

【五、状态与废止：以官方为准，状态与日期必须自洽】
- status 只能取：现行有效 / 即将实施 / 已废止。
- 状态自洽铁律：实施日期 ≤ 今天 ⇒ status 必为"现行有效"；仅当实施日期 > 今天 ⇒ 才可"即将实施"。绝不把已实施/已生效的法规标成"即将实施"。
- 判定废止必须有官方公告/复审结论支撑；老标准（2003/2008/2009 版等）≠ 废止。
- 判定为废止须三处齐改：status="已废止" + abolishDate（官方写明）+ remark「废止标准不提供标准文本阅读服务。」—— 缺一不可。
- "即将被替代"的旧版仍标"现行有效"，不要改成废止。

【六、采标标记 adopted：必须有官网原话佐证】
- 仅当能在官网查到并原样引用版权原话时，才设 adopted=true 并填写 copyrightNote；否则保持原样（adopted 不要随意翻转）。
- 不要仅凭"这是 GB/T 标准"就假设它是采标；是否采标看官网有无"采用 ISO/IEC"字样。

【七、无实质变更不记录】
- 每条 change 必须能清楚说明"哪个字段 旧值→新值"以及"依据来源(source_url)"。若你无法说明变更内容与依据，就不要返回该条。
- 禁止返回"看起来更新了但说不清改了什么"的条目（如只改采标标记却给不出版权原话）。

【八、绝对禁止修改的字段】
- 名称(name) 与 发布部门/发布单位(dept/publisher) **一律不许修改**。把"国家互联网信息办公室"改写成"国家网信办"这类同义简称**不算变更**，禁止提交。
- 你只被允许提出以下字段的变更：effectiveDate（实施日期）、status（状态）、abolishDate（废止日期）、link（正文链接）、remark（备注）、adopted / copyrightNote（采标）。
- 提交了禁改字段的条目会被系统整条拒收。

【九、旧值必须与清单完全一致（最重要）】
- 我在下面会把清单里每条的【实施日期 / 状态 / 部门 / 是否已有链接】全部给你，你**必须先看清楚再说话**。
- 清单里某个字段**已经有值**（例如实施日期=2025-08-01），你就**绝不能把它说成空字符串或没标注**；fromValues 必须填清单里的真实值，与下面清单一字不差。
- 每条 change 必须填写 fromValues 对象：{"字段名": "清单里当前的值"}，且必须与我给你的清单值**一字不差**。
- 系统会拿 fromValues 和真实清单逐字比对，对不上就判定"你没看清单"，整条拒收。
- **禁止"无变化却返回 change"**：若你的 web 检索结果与该条目在清单里的现有值一致（即官方并未给出"变了"的白纸黑字依据），就不要返回这条 change——没有变化就别动，尤其不要把"清单已有的实施日期"先说成空、再填回原值。
- 禁止出现"原清单未标注实施日期""清单里没有这条"之类的说法——清单内容就在下面，看清楚再写。
- **提交前先核对清单是否已存在该条目 / 是否已做过该变更（通用，杜绝重复提案）**：在发出任何 action=add 之前，先在本清单的「当前清单已有条目」里检索**同名或同标准号**的条目。若已存在：① 不要重复新增（add）；② 判断该已有条目是否需要更新（状态/日期/链接变了）→ 需要就改提 action=update 并填 fromValues，不需要就整条跳过。只有确认清单里确实没有的，才 action=add。对旧版（已标「已废止」/「由 XX 替代」/「即将被 XX 替代」）也不要重复提交 update/abolish——这些变更清单往往已经做完，重复提交只会被判「无变化/已做过」而丢弃。总之：对比下面清单的**最新状态**再决定要不要发，不要凭"网上看到有新版本"就盲目 add。

【十、铁律】
- 一切以官方文件/官网为唯一权威来源，不凭记忆或推断。
- 低消耗：聚焦最近变更，不无限展开；不为单条做几十次搜索。
- 每条 change 必须附 source_url（你核实所依据的官方页面链接），且该链接必须是官方域名下能打开的正文页；系统会真实访问校验，打不开或是搜索页/列表页的一律整条拒收。
- 宁可少报，不可错报。没有把握就不要提交该条——漏报只是没更新，错报会污染整份清单。

【十一、废止—替代关系（通用规则，覆盖法规与所有标准）】
- 当官方文件写明某法规/标准被另一法规/标准替代时，必须同时做两件事：
  1) 被替代的旧条目：用 action="abolish"，status="已废止"，填 abolishDate（官方写明），并在 replacedBy 字段填"替代它的法规/标准名称或编号"；系统会自动把 remark 写成「由 XX 替代。废止标准不提供标准文本阅读服务。」，你无需手填 remark。
  2) 若替代它的新法规/标准【不在】当前清单里，必须再用一条 action="add" 把它加进清单（按正常 add 规则提供官方链接、实施日期、发布部门等），不得遗漏。
- 此规则为通用规则，适用于 laws 表（法规）与 standards 表（所有产品标准），不止食安标准。
- 若官方只宣布废止、未写明被谁替代（极少见），replacedBy 留空，remark 仍为「废止标准不提供标准文本阅读服务。」，不得编造替代项。

【十二、提交前自检：杜绝"张冠李戴"与"凭记忆填充"】
- **依据必须指向本条自身**：你为某条目提供的 source_url 与所引用的标准号，必须属于**这条条目本身**的官方页与编号。绝不要把为 A 标准找到的页面/编号，套用到 B 标准头上（例如拿"冲模"类标准的依据去支撑"人工智能安全"类条目）。若检索结果其实指向另一个标准，说明你找错了，应**放弃该条**，而不是硬凑。
- **名称与编号自检**：你填写的标准编号（stdNo 或名称里的 GB/T XXXX）其真实名称，必须与你填写的条目名称一致。若不一致（如编号对应"冲模"而你写的是"AI 安全"），说明你串了标准，立即放弃该条、不要输出。
- **每字段都要有出处，没有就别填**：effectiveDate / dept / status / stdNo 每个值都必须能指到你检索到的官方来源原文；若 web_search 没有返回该值，就填 "" 或跳过该条，**绝不凭记忆猜**（例如把实施日期写成 2024-09-01 而官网其实是 2025-11-01）。
- **新增条目(add)同样要可靠**：新增不是"可以先编、留待人工补"——你填写的新增条目的名称、编号、部门、实施日期，每一项都必须来自真实检索来源；任何一项你无法指出来源，就不要输出该新增提案。宁可这条不出，也不要把拼凑的内容交出去。
"""


def build_existing_block(items, table):
    """把清单已有条目的关键字段全部摊开给模型看（名称/实施日期/状态/部门/是否已有链接）。
    这是「旧值核对」这道质检关卡的基准，模型再也不能说『原清单未标注』。"""
    lines = []
    for it in items:
        src = it.get("dept") if table == "laws" else it.get("publisher")
        no = ("｜标准号=" + (it.get("stdNo") or "")) if table != "laws" else ""
        lines.append(
            f"- {it.get('name','')}{no}"
            f"｜id={it.get('id','')}"
            f"｜实施日期={it.get('effectiveDate') or '(空)'}"
            f"｜状态={it.get('status') or '(空)'}"
            f"｜部门={src or '(空)'}"
            f"｜正文链接={'已有' if (it.get('link') or '').strip() else '缺失'}"
        )
    return "\n".join(lines) or "（暂无）"


def build_prompt(target_label, domain_text, existing_names):
    names_block = existing_names if isinstance(existing_names, str) else (
        "\n".join(f"- {n}" for n in existing_names) or "（暂无）")
    return f"""你是中国法律法规与标准检索助手，负责维护一份「家电制造业体系工程师使用的法规/标准清单」（data.json，含 laws 与 standards 两张表）。你将运行：使用 web_search 联网检索最近约两周内与【范围】相关的法规/标准变更。一切以官方文件/官网为唯一权威来源，不凭记忆或推断。

═══ 本次检索范围（{target_label}）═══
{domain_text}

═══ 当前清单已有条目（既是去重基准，也是旧值核对基准，务必逐条看清再作答）═══
{names_block}

{COMMON_RULES}

请返回 JSON（无变更则 changes 为空数组）。每条 change 字段：
{{
  "action": "add | update | abolish",
  "name": "全称",
  "table": "laws 或 standards。本清单规矩：仅『与本公司产品相关』的标准（洗衣机/微波炉/制冷/电器安全/EMC/能效/食品接触/插头插座/电池/无线蓝牙等）才填 standards；其余标准（职业健康/安全/环境/信息安全类国标）一律填 laws（法规表）。法规/条例/办法等填 laws。",
  "stdNo": "标准号（标准类填）",
  "docNumber": "发文字号（法规类填，查不到留空）",
  "domains": ["环境"],
  "category": "环境与职业健康 / 质量 / 信息安全 / 反恐（法规类填其一）",
  "source": "发布机关，如 中国政府网/中国人大网/国家网信办/工信部/国家标准化管理委员会/ISO",
  "link": "官方文档页链接（能直接看全文；给不出填空字符串）",
  "effectiveDate": "YYYY-MM-DD 或空字符串（必须来自官方文件）",
  "status": "现行有效 | 即将实施 | 已废止（须与实施日期自洽）",
  "abolishDate": "YYYY-MM-DD 或空字符串",
  "adopted": true | false,
  "copyrightNote": "采标时原样照抄的官网版权原话，否则空字符串",
  "remark": "仅限三类：采标官网原话 / 食安待补说明 / 即将被XX替代说明；其余留空",
  "fromValues": {{"effectiveDate": "清单里当前的实施日期", "status": "清单里当前的状态"}},
  "source_url": "你核实本条所依据的官方页面链接。只填 web_search 真实返回的链接（原样复制）；没真实拿到就填空字符串，改填下面的 source_hint，绝不许自己拼 URL。系统会真实访问校验。",
  "source_hint": "当 source_url 留空时必填：本条的定位线索，供系统去官方站自动解析真链接。写标准号 / 发文字号 / 发布部门+公告标题，如「GB/T 22239-2019」或「国家网信办 2026年第3号公告」。",
  "replacedBy": "替代本标准的法规/标准名称或编号（仅当官方写明被XX替代时填；否则空字符串）",
  "note": "变更说明：必须写明『哪个字段 由X 改为 Y，依据是官方哪份文件』，不许写空话"
}}

重要：effectiveDate / status / abolishDate / replacedBy 这四个结论字段你【不必填写】（直接留空字符串 ""），系统会依据你提供的 source_url 官方页确定性抽取并覆盖，不会采用你生成的值。你只需：① 确保 source_url 是你 web_search 真实返回的官方页链接（原样复制，绝不自造 URL）；② 在 note 里尽量引用官方页原文；③ fromValues 仍须如实填写清单当前值（旧值核对基准）。

注意：action=update / abolish 时 fromValues 必填且必须与上面清单一字不差，否则整条拒收。
只输出 JSON，不要额外说明文字。"""


def extract_json(text):
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1:
        text = text[s:e + 1]
    return text


def search_target(client, model, label, text, existing_names):
    prompt = build_prompt(label, text, existing_names)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            tools=[{"type": "web_search", "web_search": {"enable": True, "search_result": True}}],
            temperature=0,
        )
        return json.loads(extract_json(resp.choices[0].message.content))
    except Exception as e:
        print(f"  [{label}] 检索出错: {e}")
        return {"changes": [], "summary": f"检索出错: {e}"}


def _contains_ok(short, long_):
    """short 被 long_ 包含，且不是「数字前缀」式的假包含。
    例：GB4706.1 出现在 GB4706.14 里，但后面紧跟数字，属两份不同标准，不算匹配。"""
    i = long_.find(short)
    if i < 0:
        return False
    nxt = long_[i + len(short): i + len(short) + 1]
    return not (nxt.isdigit() or nxt == ".")


_STD_KEY_RE = re.compile(
    r"\b(GB\s*/?\s*T|GBZ\s*/?\s*T|GB|GBZ|QB\s*/?\s*T|JB\s*/?\s*T|YY\s*/?\s*T|SN\s*/?\s*T|"
    r"HG\s*/?\s*T|HJ|IEC|ISO|EN)\s*([0-9]+(?:\.[0-9]+)*)", re.I)


def _std_key(s):
    """抽出标准号主键，如 (GB, 4706.1)。GB 与 GB/T 归为同族（清单里两种写法混用）。"""
    m = _STD_KEY_RE.search(s or "")
    if not m:
        return None
    fam = re.sub(r"[\s/]", "", m.group(1)).upper()
    if fam == "GBT":
        fam = "GB"
    if fam == "GBZT":
        fam = "GBZ"
    return (fam, m.group(2))


_STD_FULL_RE = re.compile(
    r"\b(GB\s*/?\s*T?|GBZ\s*/?\s*T?|QB|JB|YY|SN|HG|HJ|IEC|ISO|EN)\s*"
    r"([0-9]+(?:\.[0-9]+)*)\s*-\s*(\d{4})", re.I)


def _norm_fam(s):
    return re.sub(r"[\s/]", "", s or "").upper().replace("GBT", "GB").replace("GBZT", "GBZ")


def _parse_std_full(s):
    """从文本里抽出第一个完整标准号 (family, base, year)。"""
    m = _STD_FULL_RE.search(s or "")
    if not m:
        return None
    return (_norm_fam(m.group(1)), m.group(2), m.group(3))


def _source_version_mismatch(text, target_stdno):
    """依据来源页面是否用『其它版本』的标准号改动本条（张冠李戴）。
    例：本条 GB/T 4288-2018，来源页却标注 GB/T 4288-2025 → 返回 True。"""
    t = _parse_std_full(target_stdno)
    if not t:
        return False
    for m in _STD_FULL_RE.finditer(text or ""):
        fam = _norm_fam(m.group(1))
        if fam == t[0] and m.group(2) == t[1] and m.group(3) != t[2]:
            return True
    return False


def _name_match(name, items):
    """四层匹配：①精确 ②同一标准号 ③互相包含 ④高相似度。

    ⚠️ 旧版这里写的是 `shorter = min(name, key=len)`——那是在遍历字符串里的单个字符，
    结果恒为长度 1，于是 `len(shorter) < 4` 永远成立、直接 return None，近义匹配整段失效。
    这正是重复条目被当成新条目加进来的根因。

    误配风险由质检关卡③（fromValues 必须与清单一字不差）兜底：万一匹配到了错误条目，
    旧值必然对不上，整条会被拒收，不会把改动写到别的条目上。"""
    import difflib
    n = _norm_txt(name)
    if not n:
        return None
    kn = _std_key(n)
    # ① 精确（去空格后）
    for it in items:
        if _norm_txt(it.get("name")) == n:
            return it
    # ② 标准号相同即同一标准（对标准表最可靠）
    if kn:
        for it in items:
            if _std_key(_norm_txt(it.get("name"))) == kn:
                return it
    # ③ 互相包含（较短一方≥4 字，且排除 4706.1 / 4706.14 这类数字前缀假包含）
    for it in items:
        m = _norm_txt(it.get("name"))
        if not m or min(len(n), len(m)) < 4:
            continue
        km = _std_key(m)
        if kn and km and kn != km:
            continue          # 明确是两份不同标准
        if (len(n) <= len(m) and _contains_ok(n, m)) or (len(m) < len(n) and _contains_ok(m, n)):
            return it
    # ④ 高相似度（覆盖「服务管理办法」vs「服务安全管理办法」这类多/少几个字的情况）
    best, best_r = None, 0.0
    for it in items:
        m = _norm_txt(it.get("name"))
        if not m or min(len(n), len(m)) < 6:
            continue
        km = _std_key(m)
        if (kn and km and kn != km) or (bool(kn) != bool(km)):
            continue          # 一方有标准号一方没有，或标准号不同，都不比
        r = difflib.SequenceMatcher(None, n, m).ratio()
        if r > best_r:
            best, best_r = it, r
    return best if best_r >= 0.88 else None


def clean_remark(ch, is_food=False, is_abolish=False):
    """备注只允许三类：采标官网原话 / 食安待补 / 即将被替代；其余一律清空，杜绝废话。"""
    copyright = (ch.get("copyrightNote") or "").strip()
    if copyright:
        return copyright
    if is_abolish:
        return "废止标准不提供标准文本阅读服务。"
    r = (ch.get("remark") or "").strip()
    if not r:
        return ""
    if is_food and "官方链接待替换" in r:
        return r
    if "即将被" in r and "替代" in r:
        return r
    if "废止标准不提供标准文本阅读服务" in r:
        return r
    # 其余（含"新增法规，属于XX领域"等废话）一律丢弃
    return ""


def make_new_record(table, name, ch, domain_id, today, new_id, is_food=False):
    status = norm_status(ch.get("status")) or "现行有效"
    src = (ch.get("source") or "").strip() or ("中国政府网" if table == "laws" else "国家标准化管理委员会")
    remark = clean_remark(ch, is_food=is_food)
    adopted = bool(ch.get("adopted"))
    if table == "laws":
        return {
            "name": name, "docNumber": ch.get("docNumber", "") or "",
            "dept": src, "effectiveDate": _ymd(ch.get("effectiveDate")) or "",
            "status": status, "domains": ch.get("domains", []) or [],
            "category": domain_id,
            "link": (ch.get("link") or "").strip() if url_trusted(ch.get("link")) else "",
            "region": ch.get("region", "全国") or "全国",
            "id": str(new_id), "remark": remark,
            "abolishDate": ch.get("abolishDate", "") or "",
            "adopted": adopted, "copyrightNote": (ch.get("copyrightNote") or "").strip(),
        }
    else:
        return {
            "name": name, "stdNo": ch.get("stdNo", "") or "",
            "stdType": ch.get("stdType", "") or "", "publisher": src,
            "effectiveDate": _ymd(ch.get("effectiveDate")) or "",
            "status": status,
            "link": (ch.get("link") or "").strip() if url_trusted(ch.get("link")) else "",
            "region": ch.get("region", "全国") or "全国",
            "id": str(new_id), "remark": remark,
            "abolishDate": ch.get("abolishDate", "") or "",
            "adopted": adopted, "copyrightNote": (ch.get("copyrightNote") or "").strip(),
        }


def next_id(table, all_items):
    """生成正确的下一个 id：法规 L0403 / 标准 S0156。
    修复旧 bug：旧逻辑用 str(id).isdigit() 判断，对 'L0116' 恒为假，导致新条目从 1 重新编号。"""
    prefix = "L" if table == "laws" else "S"
    mx = 0
    for it in all_items:
        m = re.match(r"^[A-Za-z]*0*(\d+)$", str(it.get("id") or "").strip())
        if m:
            try:
                mx = max(mx, int(m.group(1)))
            except Exception:
                pass
    return f"{prefix}{mx + 1:04d}"


# 标准号特征：带这些编号的条目属于「标准」，不许混进法规表
STD_NO_RE = re.compile(
    r"(GB\s*/?\s*T?\s*\d|QB\s*/?\s*T|JB\s*/?\s*T|YY\s*/?\s*T|SN\s*/?\s*T|HG\s*/?\s*T|"
    r"\bIEC\s*\d|\bISO\s*\d|\bEN\s*\d)", re.I)

# 产品相关标准提示词（与本公司产品有关）。用户规矩：仅这类标准才进 standards 表；
# 其余标准（职业健康/安全/环境/信息安全类国标）进 laws 表是允许的。
PRODUCT_STD_HINTS = re.compile(
    r"洗衣机|微波|制冷|冰箱|电磁兼容|EMC|能效|GB\s*12021|噪声|GB\s*19606|食品接触|"
    r"GB\s*4806|GB\s*31604|插头插座|GB\s*1002|GB\s*2099|电池|无线|蓝牙|SRRC|RED|FCC|"
    r"电器安全|GB\s*4706|IEC\s*60335|耦合器|电线电缆|灯具|led|咀嚼冰|冰沙|啤酒机|制冰",
    re.I)

def _hcno_looks_fabricated(hcno):
    """识别编造的 hcno：真实 hcno 是随机哈希，呈现规律重复即编造。

    覆盖的编造形态：
    ① 8 位块重复（周期8）：如 FFB7A8B3 + A8B3A8B3×3 → 拆 4 块后存在重复块；
    ② 4 位块重复（周期4）：如 ABCDABCDABCDABCD；
    ③ 字母-数字交替规律：如 A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6。
    """
    h = (hcno or "").strip()
    if len(h) != 32:
        return False  # 长度问题交由调用方单独判
    # ① 8 位块重复
    blocks8 = [h[i:i + 8] for i in range(0, 32, 8)]
    if len(set(blocks8)) < len(blocks8):
        return True
    # ② 4 位块重复（同一块出现 ≥3 次）
    blocks4 = [h[i:i + 4] for i in range(0, 32, 4)]
    if max(blocks4.count(b) for b in set(blocks4)) >= 3:
        return True
    # ③ 字母-数字交替规律
    if re.fullmatch(r"([A-Fa-f][0-9]){16}", h) or re.fullmatch(r"([0-9][A-Fa-f]){16}", h):
        return True
    return False


def _norm_txt(v):
    return re.sub(r"\s+", "", str(v or "")).strip()


def check_change(table, change, target, today):
    """7 道质检关卡。返回 (是否通过, 未通过原因列表, 是否直接丢弃)。
    - 通过：进「可直接应用」。
    - 未通过但 '丢弃'=False：进「待核实线索」栏（人工复核，真候选）。
    - '丢弃'=True：确属垃圾（无依据/死链/非官方/理由缺失），直接丢弃，不污染任何面板。"""
    reasons = []
    name = (change.get("name") or "").strip()
    action = (change.get("action") or "").strip().lower()
    discard = False

    # 根因修复：结论无法从官方页核实 → 进人工复核（不静默丢弃、不自动采信）
    if change.get("_unverified"):
        return (False, [change.get("_unverified_reason", "官方页无法核实，请人工确认")], False)

    # ① 表归属：用户规矩——只有「产品相关标准」才进 standards 表，
    #    其余标准（职业健康/安全/环境/信息安全类国标）放 laws 表是允许的。
    #    因此仅当「产品相关标准」被放进 laws 表时才拦；其余标准进 laws 放行进人工复核也不算错。
    is_std = bool(STD_NO_RE.search(name) or (change.get("stdNo") or "").strip())
    if table == "laws" and is_std and PRODUCT_STD_HINTS.search(name + " " + (change.get("stdNo") or "")):
        reasons.append("这是产品相关标准，按规矩应放进标准表(standards)而非法规表(laws)")

    # 重复重报计数（Step⑤）：模型重报清单里早已做过的变更，仅计数、不改任何处置。
    if action in ("update", "abolish") and target is not None:
        ns = norm_status(change.get("status"))
        ts = norm_status(target.get("status"))
        ce = _ymd(change.get("effectiveDate"))
        te = _ymd(target.get("effectiveDate"))
        if ns == "已废止" and ts == "已废止":
            _METRICS["dup_rereport"] += 1
        elif (not ns or ns == ts) and (not ce or ce == te) and not (change.get("replacedBy") or "").strip():
            _METRICS["dup_rereport"] += 1

    # ② 依据来源：硬门槛
    #    - update/abolish（改动已有条目）：链接无/死/非官方/非正文 → 直接丢弃（确属垃圾）
    #    - add（新增条目）：链接问题不整条丢弃；改为生成可勾选的新增提案、链接清空待补（保住可能真实的新增内容，且核准时绝不写入假链接）
    su = (change.get("source_url") or "").strip()
    is_add = (action == "add")
    link_issue = None
    rl = ""   # 分诊自救解析到的真链接（在下方 if link_issue 块内赋值）；先置空避免 step② 提前引用未绑定
    if not su:
        link_issue = "没有提供依据来源网址（source_url）"
    elif not domain_ok(su):
        link_issue = "依据来源不是官方域名：" + su
    elif not url_shape_ok(su):
        link_issue = "依据来源不是正文页（搜索页/列表页/伪造格式）：" + su
    else:
        pr = scf_probe_link(su)
        if pr["state"] is False:
            link_issue = "依据来源确认失效（" + (pr.get("reason") or "404 / 跳回首页") + "），多半是编造的链接：" + su
        elif pr["state"] is None:
            link_issue = "依据来源无法自动验证（超时 / 被拦截），请人工点开确认：" + su
        elif pr["state"] is True:
            if pr.get("dead_page_checked") and pr.get("dead_page"):
                link_issue = "依据来源打开后无正文（显示「搜索不到 / 未找到」），属死链或编造：" + su
            elif pr.get("dead_page_checked"):
                # 国内 SCF 已确认是真实正文页：只做版本号核对，取不到正文也放行（绝不因境外超时误杀真条目）
                text = fetch_text(su)
                if text is not None and table != "laws" and target and target.get("stdNo"):
                    if _source_version_mismatch(text, target.get("stdNo")):
                        link_issue = "依据来源页面标注的标准号与本条不一致（疑似拿其它版本页面改动本条）：" + su
            else:
                # 本地回退路径（SCF 未配置/不可用）：保留原逐条探活逻辑
                text = fetch_text(su)
                if text is None:
                    link_issue = "依据来源能打开但无法读取正文，请人工点开确认：" + su
                elif is_dead_page(text):
                    link_issue = "依据来源打开后无正文（显示「搜索不到 / 未找到」），属死链或编造：" + su
                elif table != "laws" and target and target.get("stdNo"):
                    if _source_version_mismatch(text, target.get("stdNo")):
                        link_issue = "依据来源页面标注的标准号与本条不一致（疑似拿其它版本页面改动本条）：" + su

    # 实施日期防御：模型给出可信官方链接时，也拿官方页正文核对实施日期，
    #   避免把『发布日期』当『实施日期』写入（仅修正 change，不新增 reject 逻辑）。
    if not link_issue and su:
        _rectify_effective_date(change, su, target=target)

    # 状态/废止/替代证据核对（Step②）：称废止/替代必须有官方页正文依据。
    #   - 页面取到了但【无任何废止依据】→ 直接丢弃，不提出（用户要求：没依据别提废止）；
    #   - 页面取不到/无法核实（超时）→ 降级人工复核，不自动采信也不误杀；
    #   - 有依据 → 放行。根治伪废止与张冠李戴。
    status_url = rl if (link_issue and rl) else (su if not link_issue else None)
    if status_url:
        verdict_st, why_st = _confirm_status_on_page(change, target, status_url)
        if verdict_st == "discard":
            reasons.append(why_st)
            discard = True
        elif verdict_st == "review":
            reasons.append("状态/废止/替代依据未能在官方页自动核实：" + why_st)

    # ②-b 分诊自救：GLM 给不出/给错链接时，不立刻判死——先由本系统按官方渠道
    #     （按标准号解析 openstd / 复用清单现有链接）确定性地取真实链接。
    #     这样 GLM 不必再编 URL，真变更也不会被"链接编错"一起丢掉。
    #     解析成功后仍要拿该页反向核对声称内容：核对通过才放行左栏，
    #     核不上只降级到人工复核（绝不因"有了真链接"就默认变更为真）。
    if link_issue:
        rs = resolve_source_url_for_change(table, change, target)
        rl = (rs.get("link") or "").strip()
        if rl and rs.get("verified") and domain_ok(rl) and url_shape_ok(rl):
            change["source_url"] = rl
            change["_link_resolved"] = {
                "link": rl, "method": rs.get("method", ""),
                "reason": rs.get("reason", ""), "was": su,
            }
            # 按标准号解析出的 openstd 详情页，就是该条目自身的官方正文页（已核对标准号一致）：
            # 若 GLM 给的 link 不可信，就用这个真链接顶上，让缺链接的条目顺势补齐。
            # 写入仍走原有 url_trusted 关卡，安全性不降级。
            if rs.get("method") == "openstd" and not url_trusted(change.get("link")):
                change["link"] = rl
            ok_claim, why = _confirm_claim_on_page(change, target, rl)
            print(f"  [分诊自救] 《{name}》→ {rs.get('method')} {rl}｜{'确认' if ok_claim else '待人工'}")
            _RESOLVE_LOG.append({
                "name": name, "table": table, "action": action,
                "method": rs.get("method", ""), "link": rl,
                "glmGave": su or "(留空)", "claimConfirmed": bool(ok_claim),
                "detail": why,
            })
            if ok_claim:
                link_issue = None          # 依据已由系统确定性补正并核对通过
            else:
                link_issue = None          # 链接问题已解决，剩下是"内容待确认"
                reasons.append(why)        # 降级人工复核，不丢弃
        else:
            link_issue += f"；系统按官方渠道自动解析也未取到真实链接（{rs.get('reason', '')}）"

    if link_issue:
        if is_add:
            # 合法新增：链接问题不整条丢弃；交由 apply_change 的 action=="add" 分支
            # 生成可勾选的新增提案、链接自动清空待补，核准时绝不写入假链接
            reasons.append(link_issue + "；该新增条目链接已留空待补，建议人工确认是否新增")
        else:
            # 更新/废止条目：链接无/死/非官方/非正文 → 确属垃圾，直接丢弃（不污染任何面板）
            reasons.append(link_issue)
            discard = True

    # ③ 旧值核对：声称的旧值必须与清单一字不差（证明它真的看过清单）
    if action in ("update", "abolish") and target:
        fv = change.get("fromValues")
        src_field = "dept" if table == "laws" else "publisher"
        if not isinstance(fv, dict) or not fv:
            reasons.append("未填写 fromValues，无法证明它核对过清单现值")
        else:
            for k, v in fv.items():
                key = src_field if k in ("dept", "publisher") else k
                cur = target.get(key, "")
                if key == "status":
                    if norm_status(_norm_txt(v)) != norm_status(_norm_txt(cur)):
                        reasons.append(f"声称原状态是「{v}」，清单里其实是「{cur or '空'}」")
                elif key in ("effectiveDate", "abolishDate"):
                    if _ymd(v) != _ymd(cur):
                        reasons.append(f"声称原日期是「{v}」，清单里其实是「{cur or '空'}」")
                elif _norm_txt(v) and _norm_txt(v) != _norm_txt(cur):
                    reasons.append(f"声称原{key}是「{v}」，清单里其实是「{cur or '空'}」")

    # ④ 状态与日期必须自洽
    st = norm_status(change.get("status"))
    eff = _ymd(change.get("effectiveDate")) or (_ymd((target or {}).get("effectiveDate")))
    if st == "即将实施" and eff and eff <= today:
        # 实施日期已过却标"即将实施" = 矛盾，自动纠正为现行有效（不进任何拦截栏）；
        # 若清单现状本就是现行有效，则不再是变更，后续因无差异自然跳过。
        change["status"] = "现行有效"
        st = "现行有效"
    if st == "已废止" and not (_ymd(change.get("abolishDate")) or (target or {}).get("abolishDate")):
        reasons.append("判定为废止，却给不出官方写明的废止日期")

    # ⑤ 理由必须与实际改动自洽，且不能为空
    note = str(change.get("note") or "").strip()
    if not note:
        reasons.append("没有说明改了什么、依据是什么")
        discard = True
    elif ("实施日期" in note or "实施时间" in note) and not change.get("effectiveDate"):
        reasons.append("理由里说改实施日期，实际却没给出日期")
        discard = True

    return (len(reasons) == 0), reasons, discard


def _proposed_summary(change):
    """提取 GLM 想设置的关键字段，供报告展示『它想改/想新增什么』。"""
    fields = ("name", "stdNo", "docNumber", "dept", "publisher", "effectiveDate",
              "abolishDate", "status", "link", "remark", "domains", "category",
              "replacedBy", "source", "adopted", "copyrightNote")
    out = {}
    a=0
    for f in fields:
        v = change.get(f)
        if v not in (None, "", [], {}):
            out[f] = v
    fv = change.get("fromValues")
    if isinstance(fv, dict) and fv:
        out["fromValues"] = fv
    return out


def _fmt_prop(p):
    """把 proposed 字典格式化为可读字符串（用于 .md 报告）。"""
    if not isinstance(p, dict) or not p:
        return ""
    parts = []
    for k, v in p.items():
        if k == "fromValues" and isinstance(v, dict):
            v = "，".join(f"{a}={b}" for a, b in v.items())
        parts.append(f"{k}={v}")
    return "；想设：" + "，".join(parts)


def apply_change(table, all_items, change, domain_id, today):
    """把一条 AI 变更应用到 all_items（原地修改/追加），并返回用于提案记录的 dict。
    kind=skip 表示跳过；kind=reject 表示未过质检（带 reasons，进待核实栏，不改数据）。"""
    action = (change.get("action") or "").strip().lower()
    name = (change.get("name") or "").strip()
    if not name or action not in ("add", "update", "abolish"):
        return {"kind": "skip", "name": name, "reason": "无效 action 或空名称"}
    src_field = "dept" if table == "laws" else "publisher"
    label = CATEGORY_NAMES.get(domain_id, domain_id)
    is_food = bool(re.search(r"GB\s*4806|GB\s*31604", (change.get("stdNo") or "") + (name or "")))

    # —— 质检：不通过则整条拦下，带原因进「待核实线索」栏，绝不改动数据 ——
    pre_target = None if action == "add" else _name_match(name, all_items)
    # 根因修复：先拿官方页正文确定性抽取结论，覆盖 GLM 草稿（GLM 不再当事实来源）
    change = reconcile_conclusions(change, pre_target, table, today)
    ok, reasons, discard = check_change(table, change, pre_target, today)
    if discard:
        # 确属垃圾（无依据/死链/非官方/理由缺失）：直接丢弃，不污染任何面板
        return {"kind": "discard", "name": name, "action": action, "table": table,
                "reason": "；".join(reasons), "proposed": _proposed_summary(change)}
    if action == "add":
        # 软未过（多为链接问题，但内容可能真实）→ 仍作为可勾选的「新增」提案交人工核准。
        # make_new_record 内部只用 url_trusted 通过的链接；未通过则 link 自动留空待补，
        # 因此核准写入时绝不会把 GLM 编的假链接写进清单（等级保护基本要求这类即此情形）。
        if _name_match(name, all_items):
            return {"kind": "skip", "name": name, "reason": "已存在（近义去重）"}
        new_id = next_id(table, all_items)
        rec = make_new_record(table, name, change, domain_id, today, new_id, is_food=is_food)
        disp = {
            "diffs": [{"field": f, "from": "", "to": str(rec.get(f, ""))}
                      for f in (("name", "docNumber", "dept", "effectiveDate", "status", "link", "remark")
                                if table == "laws" else ("name", "stdNo", "publisher", "effectiveDate", "status", "link", "remark"))
                      if rec.get(f)],
            "link": rec.get("link", ""), "source": rec.get("dept" if table == "laws" else "publisher", ""),
            "sourceUrl": (change.get("source_url") or "").strip(),
            "reason": (change.get("note") or "新增") + "（链接已清空待补，请核准后再补官方链接）",
        }
        return {"kind": "add", "name": name, "category": label, "table": table,
                "targetId": str(new_id), "newRecord": rec, "setFields": None, "display": disp}
    if not ok:
        return {"kind": "reject", "name": name, "category": label, "table": table,
                "action": action, "reasons": reasons,
                "sourceUrl": (change.get("source_url") or "").strip(),
                "note": str(change.get("note") or ""), "proposed": _proposed_summary(change)}

    if action == "add":
        # 去重（精确 + 近义包含）安全网：命中已有则跳过
        if _name_match(name, all_items):
            return {"kind": "skip", "name": name, "reason": "已存在（近义去重）"}
        new_id = next_id(table, all_items)
        rec = make_new_record(table, name, change, domain_id, today, new_id, is_food=is_food)
        all_items.append(rec)
        disp = {
            "diffs": [{"field": f, "from": "", "to": str(rec.get(f, ""))}
                      for f in (("name", "docNumber", "dept", "effectiveDate", "status", "link", "remark")
                                if table == "laws" else ("name", "stdNo", "publisher", "effectiveDate", "status", "link", "remark"))
                      if rec.get(f)],
            "link": rec.get("link", ""), "source": rec.get("dept" if table == "laws" else "publisher", ""),
            "sourceUrl": (change.get("source_url") or "").strip(),
            "reason": change.get("note", "") or "新增",
        }
        return {"kind": "add", "name": name, "category": label, "table": table,
                "targetId": str(new_id), "newRecord": rec, "setFields": None, "display": disp}

    target = _name_match(name, all_items)
    if not target:
        return {"kind": "skip", "name": name, "reason": "未匹配到现有条目"}
    tid = target.get("id")

    if action == "abolish":
        old_status = target.get("status", "")
        abolish_date = change.get("abolishDate", "") or target.get("abolishDate", "")
        replaced_by = (change.get("replacedBy") or "").strip()
        if replaced_by:
            # 通用废止—替代规则：官方写明被XX替代时，备注须写明"由XX替代"
            remark = f"由 {replaced_by} 替代。废止标准不提供标准文本阅读服务。"
        else:
            remark = clean_remark(change, is_abolish=True)
        set_fields = {"status": "已废止", "abolishDate": abolish_date, "remark": remark}
        # 应用
        target["status"] = "已废止"
        if abolish_date:
            target["abolishDate"] = abolish_date
        target["remark"] = remark
        return {"kind": "abolish", "name": name, "category": label, "table": table,
                "targetId": tid, "newRecord": None, "setFields": set_fields,
                "display": {"diffs": [{"field": "状态", "from": old_status, "to": "已废止"}],
                            "link": target.get("link", ""), "source": target.get(src_field, ""),
                            "sourceUrl": (change.get("source_url") or "").strip(),
                            "reason": ((f"由 {replaced_by} 替代：" if replaced_by else "") + (change.get("note", "") or "废止"))}}

    # update
    set_fields = {}
    diffs = []
    if change.get("effectiveDate") and change["effectiveDate"] != target.get("effectiveDate"):
        set_fields["effectiveDate"] = change["effectiveDate"]
        diffs.append({"field": "实施时间", "from": target.get("effectiveDate", ""), "to": change["effectiveDate"]})
    new_status = norm_status(change.get("status"))
    if new_status and new_status != target.get("status"):
        set_fields["status"] = new_status
        diffs.append({"field": "状态", "from": target.get("status", ""), "to": new_status})
    # 【禁改字段】名称与发布部门/发布单位一律不许改动。
    # "国家互联网信息办公室"→"国家网信办" 这类同义简称改写不是变更，直接忽略。
    src = (change.get("source") or "").strip()
    # 采标备注（仅当本次提供了版权原话时才覆盖）
    copyright = (change.get("copyrightNote") or "").strip()
    if copyright:
        set_fields["remark"] = copyright
        set_fields["copyrightNote"] = copyright
        set_fields["adopted"] = True
        diffs.append({"field": "采标备注", "from": target.get("remark", ""), "to": copyright})
    elif change.get("adopted") is not None and bool(change.get("adopted")) != bool(target.get("adopted")):
        set_fields["adopted"] = bool(change.get("adopted"))
        diffs.append({"field": "采标标记", "from": str(target.get("adopted", "")),
                      "to": str(bool(change.get("adopted")))})
    # 链接保护：仅当现有缺失/是首页时才用新链，且新链需探活
    # 【链接】只有通过三重校验(官方域名+正文形态+真实可访问)的新链接才允许写入；
    # 校验不过就宁可留空，绝不再用百度/站内搜索页顶替（那正是"链接不是正文"的老毛病）。
    new_url = (change.get("link") or "").strip()
    existing_url = (target.get("link") or "").strip()
    if new_url and new_url != existing_url and url_trusted(new_url):
        if not existing_url:
            set_fields["link"] = new_url
            diffs.append({"field": "来源链接", "from": "", "to": new_url})
        elif is_homepage(existing_url):
            set_fields["link"] = new_url
            diffs.append({"field": "来源链接", "from": "(原为首页)", "to": new_url})
        # 现有已是有效深链时不动，避免把人工校对好的链接冲掉
    # 应用
    for k, v in set_fields.items():
        target[k] = v
    if not diffs:
        # 若它其实是想改「部门/名称」这类禁改字段，不要静默跳过——
        # 摆到「待核实线索」栏里，让人看得见 GLM 到底错在哪，才能迭代提示词。
        tried_dept = bool(src) and _norm_txt(src) != _norm_txt(target.get(src_field, ""))
        if tried_dept:
            return {"kind": "reject", "name": name, "category": label, "table": table,
                    "action": action,
                    "reasons": [f"只提出了禁改字段的改动：想把部门「{target.get(src_field,'') or '空'}」"
                                f"改成「{src}」，属同义改写，已拦截"],
                    "sourceUrl": (change.get("source_url") or "").strip(),
                    "note": str(change.get("note") or "")}
        return {"kind": "skip", "name": name, "reason": "无实质变更"}
    return {"kind": "update", "name": name, "category": label, "table": table,
            "targetId": tid, "newRecord": None, "setFields": set_fields,
            "display": {"diffs": diffs, "link": target.get("link", ""),
                        "source": target.get(src_field, ""),
                        "sourceUrl": (change.get("source_url") or "").strip(),
                        "reason": change.get("note", "") or "更新"}}


def _find_replaced_stdnos(text, self_stdno):
    """Step③：从官方页正文提取被代替/被废止的标准号。
    匹配『代替/替代/被代替/同时废止/修订并代替』之后出现的标准号，排除自身标准号。"""
    if not text:
        return []
    pat = re.compile(r"GB\s*/?\s*T?\s*\d[\w.\-]*(?:-\d{4})?|IEC\s*\d[\w.\-]*(?:-\d{4})?|ISO\s*\d[\w.\-]*(?:-\d{4})?")
    out = []
    for m in re.finditer(r"(代替|替代|被代替|同时废止|修订并代替)", text):
        tail = text[m.end():m.end() + 30]
        sm = pat.search(tail)
        if sm:
            no = sm.group(0).strip().upper()
            if no and no != (self_stdno or "").strip().upper():
                out.append(no)
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); res.append(x)
    return res


def _scan_abolish_for_target(ch, res, proposed_laws, proposed_standards, today):
    """Step③ 跨文件废止推断：本条官方页声明『代替 GB/T X』，反查清单把 X 标已废止。
    仅当本条有可信官方链接时才做（无依据不自动判定，符合诚实边界）。
    返回新增的 abolish 结果列表（已应用到 proposed 工作副本）。"""
    url = (ch.get("source_url") or "").strip() or (res.get("display") or {}).get("sourceUrl", "") or ""
    if not (url and domain_ok(url)):   # 仅限官方域名；url_shape_ok 对 openstd 详情页有误判，且 Y 链接本就经 check_change 使用过
        return []
    text = fetch_text(url, timeout=12)
    if not text:
        return []
    new_rec = res.get("newRecord") or {}
    self_no = (new_rec.get("stdNo") or ch.get("stdNo") or "").strip() or (new_rec.get("name") or "")
    replaced = _find_replaced_stdnos(text, self_no)
    new_res = []
    for x in replaced:
        hit, hit_table = None, None
        for tbl, items in (("laws", proposed_laws), ("standards", proposed_standards)):
            for it in items:
                if re.sub(r"\s+", "", (it.get("stdNo") or "")).upper() == re.sub(r"\s+", "", x).upper():
                    hit, hit_table = it, tbl
                    break
            if hit:
                break
        if not hit or (hit.get("status") or "") == "已废止":
            continue
        y_no = self_no
        # 依据来自同源官方页正文（确定性提取"代替 GB/T X"），比 AI 自觉更可靠，
        # 故直接标记 X 为已废止，不走 apply_change 的 AI 防御路径（避免被表归属/链接硬门槛误拦）。
        old_status = hit.get("status", "")
        if y_no:
            remark = f"由 {y_no} 替代。废止标准不提供标准文本阅读服务。"
            hit["replacedBy"] = y_no
        else:
            remark = "跨文件推断：被新版标准替代（具体替代号未能从页面解析）"
        hit["status"] = "已废止"
        hit["remark"] = remark
        res_x = {
            "kind": "abolish", "name": hit.get("name", ""),
            "category": hit.get("category") or "", "table": hit_table,
            "targetId": hit.get("id"), "newRecord": None,
            "setFields": {"status": "已废止", "replacedBy": y_no, "remark": remark},
            "display": {"diffs": [{"field": "状态", "from": old_status, "to": "已废止"}],
                        "link": hit.get("link", ""), "source": "",
                        "sourceUrl": url,
                        "reason": f"跨文件推断：官方页（{y_no}）声明代替 {x}"},
            "crossFile": True,
        }
        new_res.append(res_x)
        _METRICS["cross_file"] += 1
        print(f"    [Step③跨文件废止] 《{hit.get('name')}》→ 由 {y_no} 替代，标已废止")
    return new_res


def apply_status_rules(proposed, today):
    """通用状态切换（日期到期自动转状态）。仅当该条目自身有有效官方链接时才切换，
    并以该链接作为依据；无有效官方链接则不盲目切换（避免『无来源的状态切换』）。"""
    switched = []
    for table, key in (("laws", "laws"), ("standards", "standards")):
        for it in proposed[key]:
            # 先做同义归一（废止 ≡ 已废止、在用 ≡ 现行有效），归一后相同就不算变更，
            # 杜绝每跑一次就报一遍「废止 → 已废止」这种纯噪音。
            old = norm_status(it.get("status", ""))
            new = old
            eff = _ymd(it.get("effectiveDate"))
            if old == "即将实施" and eff and eff <= today:
                new = "现行有效"
            ad = _ymd(it.get("abolishDate"))
            if ad and ad <= today and old != "已废止":
                new = "已废止"
            if new != old:
                link = (it.get("link") or "").strip()
                if has_valid_official_link(link):
                    # 顺便从官方页抓正确实施日期，和状态一起建议（境外访问偶发超时则只改状态）
                    eff_date = None
                    try:
                        txt = fetch_text(link, timeout=8)
                        if txt and not is_dead_page(txt):
                            eff_date = _extract_effective_date(txt)
                    except Exception:
                        eff_date = None
                    set_fields = {"status": new}
                    reason = f"实施日期已至，依据标准官方页自动转为{new}"
                    if eff_date and eff_date != eff:
                        set_fields["effectiveDate"] = eff_date
                        reason += f"；官方页实施日期为 {eff_date}，已据实修正"
                    elif eff_date:
                        reason += f"（官方页实施日期 {eff_date}）"
                    it["status"] = new
                    switched.append({"table": table, "name": it.get("name", ""), "id": it.get("id"),
                                     "from": old, "to": new, "eff_old": eff,
                                     "sourceUrl": link, "setFields": set_fields,
                                     "reason": reason})
                else:
                    # 无有效官方链接：不盲目切换，保持原状态，留待有链接时再处理
                    print(f"  [状态切换跳过] {it.get('name','')}：无有效官方链接，不自动切换")
    return switched


def get_prev_data_from_git():
    try:
        out = subprocess.run(
            ["git", "show", "HEAD:data.json"],
            cwd=ROOT, capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except Exception as e:
        print(f"  [reconcile] 无法读取上版本 data.json（跳过覆盖清理）：{e}")
        return None


def reconcile_user_overrides(prev_data, new_data):
    if not prev_data or not os.path.exists(USER_EDITS_PATH):
        return
    try:
        with open(USER_EDITS_PATH, "r", encoding="utf-8") as f:
            ue = json.load(f)
    except Exception as e:
        print(f"  [reconcile] 读取 user-edits.json 失败，跳过：{e}")
        return
    try:
        prev_laws = {f"{l.get('category','')}::{l['id']}": l for l in prev_data.get("laws", [])}
        overrides = ue.get("lawOverrides") or {}
        override_ts = ue.get("overrideTs") or {}
        changed = False
        for l in new_data.get("laws", []):
            key = f"{l.get('category','')}::{l['id']}"
            prev_law = prev_laws.get(key)
            ov = overrides.get(key)
            if not prev_law or not ov:
                continue
            changed_fields = [fld for fld in ("name", "dept", "link", "effectiveDate", "status", "remark")
                              if (l.get(fld) or "") != (prev_law.get(fld) or "")]
            for fld in changed_fields:
                if fld in ov:
                    del ov[fld]
                    override_ts.pop(key, None)
                    changed = True
                    print(f"    [覆盖手动修改] {l.get('name','')} 的字段「{fld}」已被政府更新，清除'已修改'标识")
            if len(ov) == 0:
                overrides.pop(key, None)
                override_ts.pop(key, None)
        if changed:
            ue["lawOverrides"] = overrides
            ue["overrideTs"] = override_ts
            with open(USER_EDITS_PATH, "w", encoding="utf-8") as f:
                json.dump(ue, f, ensure_ascii=False, indent=2)
            print("  [reconcile] 已更新 user-edits.json，清除被政府覆盖的'已修改'字段")
    except Exception as e:
        print(f"  [reconcile] 处理失败，跳过：{e}")


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _classify_reason(r):
    """把一条质检原因归类到训练用分类桶，便于逐类压降『人工复核』数量。"""
    s = (r or "")
    # 分诊自救相关（新）：链接已由系统确定性补正，剩下的只是"内容待人工确认"，
    # 与"GLM 编链接"性质完全不同，单独归类才能看清提示词是否真的见效。
    if "系统已解析出真实官方链接" in s or "系统解析出的官方页" in s:
        return "系统已补正链接，内容待人工确认（分诊自救成功）"
    if "官方页面读到的实施日期" in s:
        return "日期与官方页不一致（GLM 报错日期）"
    if "系统按官方渠道自动解析也未取到真实链接" in s:
        return "无来源且系统也解析不到（须落地 name_query/cfsa）"
    if "无法自动验证" in s or "无法读取正文" in s or "超时" in s:
        return "探活超时/被拦截（疑似误杀，可借国内SCF消除）"
    if "确认失效" in s or "打开后无正文" in s or "多半是编造" in s or "无正文" in s:
        return "死链/编造（确属垃圾）"
    if "没有提供依据来源" in s:
        return "无来源(留空→待补)"
    if "不是官方域名" in s or "不是正文页" in s:
        if "openstd.samr.gov.cn" in s and "hcno" not in s:
            return "openstd 拼错格式(无hcno)"
        return "编造URL/非正文页(搜索页/列表页/伪造格式)"
    if "标准号与本条不一致" in s:
        return "版本混淆（拿错版本页）"
    if "即将实施」，但实施日期" in s or "判定为废止，却给不出" in s:
        return "状态/日期不自洽"
    if "声称原" in s or "未填写 fromValues" in s or "无法证明它核对过清单" in s:
        return "旧值核对不符（未看清单）"
    if "这是标准，却被放进了法规表" in s:
        return "表归属错误（标准混进法规表）"
    if "只提出了禁改字段" in s:
        return "只改了禁改字段（同义改写）"
    if "没有说明改了什么" in s or "理由里说改实施日期" in s:
        return "理由缺失/不自洽"
    return "其它"


def _tally_reasons(items, reason_getter):
    """对一组条目（rejected/discarded）按原因分类计数。"""
    c = Counter()
    for it in items:
        rs = reason_getter(it)
        if isinstance(rs, list):
            for r in rs:
                c[_classify_reason(r)] += 1
        elif rs:
            c[_classify_reason(rs)] += 1
    return dict(c)


def write_retrieval_report(summary_changes, rejected, discarded, switched, today, metrics=None):
    """测量仪表：每轮检索产出结构化质检报告，作为『训练 GLM 让人工复核归零』的瞄准镜。
    只产出报告文件，绝不改动 data.json。"""
    if metrics is None:
        metrics = _METRICS
    counts = {
        "ok_可直接应用": len(summary_changes),
        "reject_人工复核": len(rejected),
        "discard_丢弃": len(discarded),
        "status_switch_状态切换": len(switched),
    }
    reject_breakdown = _tally_reasons(rejected, lambda r: r.get("reasons", []))
    discard_breakdown = _tally_reasons(discarded, lambda d: d.get("reason", ""))
    report = {
        "generatedAt": today,
        "note": "测量仪表：右栏(人工复核)是诊断信号不是负担。逐类压降 reject_breakdown，才能让它归零。",
        "counts": counts,
        "reject_breakdown": reject_breakdown,
        "discard_breakdown": discard_breakdown,
        "rejected_items": [
            {"name": r.get("name"), "category": r.get("category"), "table": r.get("table"),
             "action": r.get("action"), "reasons": r.get("reasons", []),
             "sourceUrl": r.get("sourceUrl", ""), "proposed": r.get("proposed", {})}
            for r in rejected
        ],
        "discarded_items": [
            {"name": d.get("name"), "table": d.get("table"), "action": d.get("action"),
             "reason": d.get("reason", ""), "proposed": d.get("proposed", {})}
            for d in discarded
        ],
        # 分诊自救台账：GLM 没给/给错链接，但系统按官方渠道确定性补上了真链接
        "auto_resolved_links": list(_RESOLVE_LOG),
        "auto_resolved_count": len(_RESOLVE_LOG),
        # 质量测量（Step⑤）：4 类问题计数，推送后点开报告即可直接数到改善
        "quality_metrics": {
            "fake_abolish": metrics["fake_abolish"],
            "publish_date_misfill": metrics["publish_date_misfill"],
            "dup_rereport": metrics["dup_rereport"],
            "cross_file": metrics["cross_file"],
        },
    }
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("  写出 retrieval-report.json 失败（可忽略）:", e)
    try:
        lines = []
        lines.append(f"# 自动检索质检报告（{today}）\n")
        lines.append("> 测量仪表：右栏(人工复核)是诊断信号。逐类压降下面 reject 的分类，才能让它归零。\n")
        lines.append("## 计数")
        lines.append(f"- 可直接应用（左栏）：**{counts['ok_可直接应用']}**")
        lines.append(f"- 人工复核（右栏）：**{counts['reject_人工复核']}**")
        lines.append(f"- 丢弃：**{counts['discard_丢弃']}**")
        lines.append(f"- 状态切换：**{counts['status_switch_状态切换']}**")
        lines.append("\n## 右栏「为什么被拒」分类（训练瞄准镜）")
        if reject_breakdown:
            for k, v in sorted(reject_breakdown.items(), key=lambda x: -x[1]):
                lines.append(f"- {k}：{v}")
        else:
            lines.append("- （无）")
        lines.append("\n## 丢弃「为什么被丢」分类")
        if discard_breakdown:
            for k, v in sorted(discard_breakdown.items(), key=lambda x: -x[1]):
                lines.append(f"- {k}：{v}")
        else:
            lines.append("- （无）")
        lines.append("\n## 质量测量（Step⑤：推送后直接看这 4 个数是否下降）")
        lines.append(f"- 伪废止·无依据直接丢弃（本应归零）：**{metrics['fake_abolish']}**")
        lines.append(f"- 发布日期误填实施日期（本应归零）：**{metrics['publish_date_misfill']}**")
        lines.append(f"- 重复重报早已做过的变更（本应归零）：**{metrics['dup_rereport']}**")
        lines.append(f"- 跨文件废止命中（越多越好）：**{metrics['cross_file']}**")
        if _RESOLVE_LOG:
            lines.append("\n## 系统自动补正链接的条目（分诊自救，GLM 不必再编 URL）")
            for g in _RESOLVE_LOG:
                lines.append(
                    f"- 《{g['name']}》[{g['method']}]：GLM 原本给的是 {g['glmGave']} → "
                    f"系统解析到 {g['link']}｜"
                    f"{'内容已核对一致，可直接应用' if g['claimConfirmed'] else '内容待人工确认'}")
        if rejected:
            lines.append("\n## 右栏条目明细")
            for r in rejected:
                lines.append(f"- 《{r.get('name')}》[{r.get('category')}]：{'；'.join(r.get('reasons', []))}{_fmt_prop(r.get('proposed'))}")
        if discarded:
            lines.append("\n## 丢弃条目明细")
            for d in discarded:
                lines.append(f"- 《{d.get('name')}》：{d.get('reason', '')}{_fmt_prop(d.get('proposed'))}")
        with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print("  写出 retrieval-report.md 失败（可忽略）:", e)
    return report


def _git_config():
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=False)
    subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=False)


def git_commit_push(files, message):
    try:
        _git_config()
        # 逐个 add：某个文件不存在（如本轮删掉了提案文件）时不会连累其它文件入库
        for fp in files:
            subprocess.run(["git", "add", "--", fp], cwd=ROOT, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if r.returncode == 0:
            return
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=False)
        subprocess.run(["git", "push"], cwd=ROOT, check=False)
    except Exception as e:
        print("  [git] 提交/推送失败（可忽略）:", e)


def write_running_status():
    try:
        with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({"status": "running", "updatedAt": now_iso()}, f, ensure_ascii=False, indent=2)
        git_commit_push([RETRIEVAL_STATUS_PATH], "chore: 检索进行中")
        print("  已写入检索状态：running")
    except Exception as e:
        print("  写入 running 状态失败（可忽略）:", e)


def main():
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("缺少环境变量 ZHIPU_API_KEY，跳过更新（保持原数据）。")
        sys.exit(0)
    if ZhipuAI is None:
        print("缺少 zhipuai 库，请先执行: pip install zhipuai")
        sys.exit(1)

    model = os.environ.get("MODEL") or "glm-4-plus"
    client = ZhipuAI(api_key=api_key)
    write_running_status()

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取 data.json 失败: {e}")
        sys.exit(1)

    laws = data.setdefault("laws", [])
    standards = data.setdefault("standards", [])
    today = date.today().isoformat()

    # proposed 为工作副本；草稿模式下它不会被写回 data.json
    proposed = copy.deepcopy(data)
    proposed_laws = proposed.setdefault("laws", [])
    proposed_standards = proposed.setdefault("standards", [])

    # —— 通用状态自动切换（先跑，确保到期法规按时切换；草稿模式也只进提案）——
    switched = apply_status_rules(proposed, today)
    for s in switched:
        print(f"  [状态切换] {s['table']}《{s['name']}》{s['from']} → {s['to']}")

    # —— GLM 联网检索各域 ——
    targets = [
        ("laws", "环境与职业健康"),
        ("laws", "质量"),
        ("laws", "信息安全"),
        ("laws", "反恐"),
        ("standards", "standards"),
    ]
    summary_changes = []
    for k in _METRICS:  # 每轮检索重置质量测量计数器
        _METRICS[k] = 0
    rejected = []   # 未过质检的候选：不改数据，带着原因进网页「待核实线索」栏
    discarded = []  # 确属垃圾（无依据/死链/非官方/理由缺失）：直接丢弃，收集以便报告计数
    for table, cid in targets:
        if table == "laws":
            items = [l for l in proposed_laws if l.get("category") == cid]
            text = DOMAINS[cid]
            all_items = proposed_laws
        else:
            items = proposed_standards
            text = STANDARDS_TEXT
            all_items = proposed_standards
        # 把已有条目的全字段摊给模型（名称/实施日期/状态/部门/是否已有链接），
        # 它才有据可依，也才能被「旧值核对」这道关卡验证。
        existing_block = build_existing_block(items, table)
        label = CATEGORY_NAMES.get(cid, cid)
        print(f"检索：{label} ...")
        result = search_target(client, model, label, text, existing_block)
        changes = result.get("changes", []) or []
        # 0-c：把本域候选的来源链接一次性交国内 SCF 探测，消除境外超时误杀（SCF 不可用时自动回退）
        _su = [(ch.get("source_url") or "").strip() for ch in changes]
        _su = [u for u in _su if u and domain_ok(u) and url_shape_ok(u)]
        if _su:
            scf_batch_probe(_su)
        print(f"  发现 {len(changes)} 条候选：{result.get('summary', '')}")
        for ch in changes:
            res = apply_change(table, all_items, ch, cid, today)
            if not res or res.get("kind") == "skip":
                if res:
                    print(f"    跳过（{res.get('reason')}）：{res.get('name')}")
                continue
            if res.get("kind") == "discard":
                discarded.append({"name": res.get("name"), "action": res.get("action", ""),
                                  "table": res.get("table", ""), "reason": res.get("reason", "")})
                print(f"    丢弃（{res.get('reason')}）：{res.get('name')}")
                continue
            if res.get("kind") == "reject":
                rejected.append(res)
                print(f"    [未过质检] {res['name']} → {'；'.join(res['reasons'])}")
                continue
            summary_changes.append(res)
            print(f"    [{res['kind']}] {res['name']}（{res['display'].get('reason')}）")
            # Step③ 跨文件废止推断：本条官方页声明"代替 GB/T X"→反查清单把 X 标已废止
            if res.get("kind") in ("add", "update", "abolish"):
                for r3 in _scan_abolish_for_target(ch, res, proposed_laws, proposed_standards, today):
                    summary_changes.append(r3)

    # —— 测量仪表：每轮产出质检报告（训练闭环瞄准镜，不碰 data.json）——
    write_retrieval_report(summary_changes, rejected, discarded, switched, today, metrics=_METRICS)
    print(f"  已写出 retrieval-report.json / .md（可直接应用 {len(summary_changes)} / 人工复核 {len(rejected)} / 丢弃 {len(discarded)}）")

    # —— 组装提案 / 摘要 ——
    if DRAFT_MODE:
        # 提案：逐条可审阅，含 targetId / setFields / newRecord / display
        proposed_changes = {
            "generatedAt": today,
            "draftMode": True,
            "counts": {
                "added": sum(1 for c in summary_changes if c["kind"] == "add"),
                "updated": sum(1 for c in summary_changes if c["kind"] == "update"),
                "abolished": sum(1 for c in summary_changes if c["kind"] == "abolish"),
                "statusSwitched": len(switched),
                "rejected": len(rejected),
            },
            "changes": [],
            "rejected": [
                {
                    "id": f"r{i + 1}",
                    "type": "reject",
                    "table": r.get("table"),
                    "name": r.get("name"),
                    "category": r.get("category"),
                    "action": r.get("action"),
                    "reasons": r.get("reasons", []),
                    "sourceUrl": r.get("sourceUrl", ""),
                    "note": r.get("note", ""),
                }
                for i, r in enumerate(rejected)
            ],
        }
        for c in summary_changes:
            proposed_changes["changes"].append({
                "id": f"c{len(proposed_changes['changes']) + 1}",
                "type": c["kind"],
                "table": c["table"],
                "name": c["name"],
                "category": c["category"],
                "targetId": c.get("targetId"),
                "newRecord": c.get("newRecord"),
                "setFields": c.get("setFields"),
                "display": c["display"],
            })
        # 状态切换也进提案
        for s in switched:
            sf = s.get("setFields") or {"status": s["to"]}
            diffs = []
            if "status" in sf:
                diffs.append({"field": "状态", "from": s["from"], "to": s["to"]})
            if "effectiveDate" in sf:
                diffs.append({"field": "实施日期", "from": s.get("eff_old") or "", "to": sf["effectiveDate"]})
            proposed_changes["changes"].append({
                "id": f"c{len(proposed_changes['changes']) + 1}",
                "type": "status_switch",
                "table": s["table"],
                "name": s["name"],
                "category": s["table"],
                "targetId": s["id"],
                "newRecord": None,
                "setFields": sf,
                "display": {"diffs": diffs,
                            "link": s.get("sourceUrl", ""), "source": "", "sourceUrl": s.get("sourceUrl", ""),
                            "reason": s.get("reason", "")},
            })
        # 本轮零结果（既无可应用变更，也无待核实线索）时不产出提案文件，
        # 避免网页弹出一个空的「待确认更新」面板。
        if not proposed_changes["changes"] and not proposed_changes["rejected"]:
            for p in (PROPOSED_DATA_PATH, PROPOSED_CHANGES_PATH):
                try:
                    os.remove(p)
                except Exception:
                    pass
            try:
                with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
                    json.dump({"status": "no_change", "updatedAt": now_iso(),
                               "counts": proposed_changes["counts"]}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("  写入 no_change 状态失败（可忽略）:", e)
            git_commit_push([PROPOSED_DATA_PATH, PROPOSED_CHANGES_PATH, RETRIEVAL_STATUS_PATH,
                             REPORT_PATH, REPORT_MD_PATH],
                            f"draft: 自动检索完成 {today}（本次无合格变更）")
            print("\n[draft 模式] 本次未发现合格变更，未产出提案。")
            return
        try:
            with open(PROPOSED_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(proposed, f, ensure_ascii=False, indent=2)
            with open(PROPOSED_CHANGES_PATH, "w", encoding="utf-8") as f:
                json.dump(proposed_changes, f, ensure_ascii=False, indent=2)
            print(f"  已写出 proposed-data.json / proposed-changes.json（draft 模式，未改动 data.json）")
        except Exception as e:
            print(f"  写出提案文件失败：{e}")
        # 状态：草稿待确认
        try:
            with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"status": "draft_ready", "updatedAt": now_iso(),
                           "counts": proposed_changes["counts"]}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("  写入 draft_ready 状态失败（可忽略）:", e)
        git_commit_push([PROPOSED_DATA_PATH, PROPOSED_CHANGES_PATH, RETRIEVAL_STATUS_PATH],
                        f"draft: 自动检索提案 {today}（待人工确认）")
        total = len(proposed_changes["changes"])
        print(f"\n[draft 模式] 本次产出 {total} 条提案（新增/更新/废止/状态切换），未改动 data.json。请到网页端逐条确认后应用。")
        return

    # —— 非草稿模式：直写 data.json（未来放开用）——
    data = proposed
    data["lastUpdated"] = today
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    summary = {
        "updatedAt": today,
        "hasUpdates": (len(summary_changes) + len(switched)) > 0,
        "counts": {"added": sum(1 for c in summary_changes if c["kind"] == "add"),
                   "abolished": sum(1 for c in summary_changes if c["kind"] == "abolish"),
                   "updated": sum(1 for c in summary_changes if c["kind"] == "update"),
                   "statusSwitched": len(switched)},
        "changes": [{"type": c["kind"], "name": c["name"], "category": c["category"],
                     "detail": c["display"].get("reason", "")} for c in summary_changes]
                    + [{"type": "status_switch", "name": s["name"], "category": s["table"],
                        "detail": f"状态：{s['from']} → {s['to']}"} for s in switched],
    }
    try:
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  已写出 update-summary.json（hasUpdates={summary['hasUpdates']}）")
    except Exception as e:
        print(f"  写出 update-summary.json 失败：{e}")

    prev_data = get_prev_data_from_git()
    reconcile_user_overrides(prev_data, data)

    total = len(summary_changes) + len(switched)
    print(f"\n本次共处理 {total} 条，lastUpdated -> {today}")
    try:
        with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({"status": "success", "updatedAt": now_iso(), "lastUpdated": today}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("  写入 success 状态失败（可忽略）:", e)
    git_commit_push([DATA_PATH, SUMMARY_PATH, RETRIEVAL_STATUS_PATH,
                     REPORT_PATH, REPORT_MD_PATH], f"chore: 检索success {today}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        try:
            with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"status": "failed", "updatedAt": now_iso(), "error": repr(e)}, f, ensure_ascii=False, indent=2)
            git_commit_push([RETRIEVAL_STATUS_PATH], "chore: 检索failed")
        except Exception:
            pass
        sys.exit(1)
