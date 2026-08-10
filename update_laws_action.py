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

try:
    from zhipuai import ZhipuAI
except ImportError:
    print("缺少 zhipuai 库，请先执行: pip install zhipuai")
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data.json")
USER_EDITS_PATH = os.path.join(ROOT, "user-edits.json")
SUMMARY_PATH = os.path.join(ROOT, "update-summary.json")
RETRIEVAL_STATUS_PATH = os.path.join(ROOT, "retrieval-status.json")
PROPOSED_CHANGES_PATH = os.path.join(ROOT, "proposed-changes.json")
PROPOSED_DATA_PATH = os.path.join(ROOT, "proposed-data.json")

# ===== 闸门：默认草稿模式（只出提案，不动数据）=====
DRAFT_MODE = os.environ.get("DRAFT_MODE", "true").lower() not in ("0", "false", "no")

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
    """质检关卡③（形态）：拒收搜索页/列表页/栏目首页；国标全文页必须带 hcno= 参数。"""
    u = (url or "").strip()
    if not u or is_homepage(u):
        return False
    if BAD_URL_PATTERNS.search(u):
        return False
    host = (urllib.parse.urlparse(u).hostname or "").lower()
    if "openstd.samr.gov.cn" in host and "hcno=" not in u:
        # 国标平台全文页真实格式必为 ...detail.html?hcno=XXXX，拼出来的一律判为伪造
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
                     "无相关结果", "内容不存在", "不存在的页面", "没有找到")


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
    """从标准官方页正文里提取『实施日期』，返回 YYYY-MM-DD；取不到返回 None。"""
    if not text:
        return None
    m = re.search(r"实施日期[：:\s]*(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"实施日期[：:\s]*(\d{4})年(\d{1,2})月(\d{1,2})日", text)
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
- 只接受直接展示"标题 + 完整条文/全文"的官方页面。优先级：人大网(npc.gov.cn)、中国政府网(gov.cn)、各部委官网、标准官方平台(openstd.samr.gov.cn / std.samr.gov.cn)。
- 严禁：搜索引擎结果页、列表页、栏目首页、新闻稿/媒体报道页（除非该新闻稿本身就是官方发布的全文页）。
- 链接必须以官方域名开头，且打开后能直接看到正文；给不出合格链接就填 ""（空字符串），并在 remark 注明"官方链接待补"，绝不用非正文链接充数。
- 你提供的 source_url（依据来源）必须亲自确认能显示正文、且不是「搜索不到 / 未找到」的死链（部分平台对拼错的编号也返回 200，但正文无内容）；若只是搜索页或死链，source_url 填空字符串并在 remark 注明待补。为某条标准(standards 表)提出的日期/状态变更，其 source_url 指向页面的标准号必须与本条 stdNo 完全一致（如本条是 GB/T 4288-2018 就引用 2018 版页面，绝不用 2025 版页面去改 2018 版）。

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
- 每条 change 必须填写 fromValues 对象：{"字段名": "清单里当前的值"}，且必须与我给你的清单值**一字不差**。
- 系统会拿 fromValues 和真实清单逐字比对，对不上就判定"你没看清单"，整条拒收。
- 禁止出现"原清单未标注实施日期""清单里没有这条"之类的说法——清单内容就在下面，看清楚再写。

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
  "table": "laws 或 standards（法规填 laws，标准填 standards）",
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
  "source_url": "你核实本条所依据的官方页面链接（必填，须官方域名正文页，系统会真实访问校验）",
  "replacedBy": "替代本标准的法规/标准名称或编号（仅当官方写明被XX替代时填；否则空字符串）",
  "note": "变更说明：必须写明『哪个字段 由X 改为 Y，依据是官方哪份文件』，不许写空话"
}}

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

    # ① 表归属：带标准号的条目不许进法规表（信息安全类豁免，用户允许其标准放法规表）
    cat = (change.get("category") or (target or {}).get("category") or "")
    if table == "laws" and cat != "信息安全" and (STD_NO_RE.search(name) or (change.get("stdNo") or "").strip()):
        reasons.append("这是标准，却被放进了法规表")

    # ② 依据来源：硬门槛（无链接/死链/非官方 → 直接丢弃；超时无法验证 → 人工复核）
    su = (change.get("source_url") or "").strip()
    if not su:
        reasons.append("没有提供依据来源网址（source_url）")
        discard = True
    elif not domain_ok(su):
        reasons.append("依据来源不是官方域名：" + su)
        discard = True
    elif not url_shape_ok(su):
        reasons.append("依据来源不是正文页（搜索页/列表页/伪造格式）：" + su)
        discard = True
    else:
        st = probe_link(su)
        if st is False:
            reasons.append("依据来源确认失效（404 / 跳回首页），多半是编造的链接：" + su)
            discard = True
        elif st is None:
            reasons.append("依据来源无法自动验证（超时 / 被拦截），请人工点开确认：" + su)
        elif st is True:
            text = fetch_text(su)
            if text is None:
                reasons.append("依据来源能打开但无法读取正文，请人工点开确认：" + su)
            elif is_dead_page(text):
                reasons.append("依据来源打开后无正文（显示「搜索不到 / 未找到」），属死链或编造：" + su)
                discard = True
            elif table != "laws" and target and target.get("stdNo"):
                if _source_version_mismatch(text, target.get("stdNo")):
                    reasons.append("依据来源页面标注的标准号与本条不一致（疑似拿其它版本页面改动本条）：" + su)

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
        reasons.append(f"标成「即将实施」，但实施日期 {eff} 早已过去")
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
    ok, reasons, discard = check_change(table, change, pre_target, today)
    if discard:
        # 确属垃圾（无依据/死链/非官方/理由缺失）：直接丢弃，不污染任何面板
        return {"kind": "discard", "name": name, "reason": "；".join(reasons)}
    if not ok:
        return {"kind": "reject", "name": name, "category": label, "table": table,
                "action": action, "reasons": reasons,
                "sourceUrl": (change.get("source_url") or "").strip(),
                "note": str(change.get("note") or "")}

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
    rejected = []   # 未过质检的候选：不改数据，带着原因进网页「待核实线索」栏
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
        print(f"  发现 {len(changes)} 条候选：{result.get('summary', '')}")
        for ch in changes:
            res = apply_change(table, all_items, ch, cid, today)
            if not res or res.get("kind") == "skip":
                if res:
                    print(f"    跳过（{res.get('reason')}）：{res.get('name')}")
                continue
            if res.get("kind") == "discard":
                print(f"    丢弃（{res.get('reason')}）：{res.get('name')}")
                continue
            if res.get("kind") == "reject":
                rejected.append(res)
                print(f"    [未过质检] {res['name']} → {'；'.join(res['reasons'])}")
                continue
            summary_changes.append(res)
            print(f"    [{res['kind']}] {res['name']}（{res['display'].get('reason')}）")

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
            git_commit_push([PROPOSED_DATA_PATH, PROPOSED_CHANGES_PATH, RETRIEVAL_STATUS_PATH],
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
    git_commit_push([DATA_PATH, SUMMARY_PATH, RETRIEVAL_STATUS_PATH], f"chore: 检索success {today}")


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
