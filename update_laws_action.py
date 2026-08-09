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
  MODEL            (可选)  模型名，默认 glm-4-air（支持 web_search 的模型）
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


def link_alive(url, timeout=8):
    """跟随重定向探测链接是否可访问且未跳回首页。"""
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
                return False
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return True
    except Exception:
        return False


_SITE_SEARCH = [
    ("人大", "https://www.npc.gov.cn/npc/c2/huiyi/search?keyword="),
    ("国务院", "https://www.gov.cn/zhengce/advanced_search?q="),
    ("政府", "https://www.gov.cn/zhengce/advanced_search?q="),
    ("网信", "https://www.cac.gov.cn/search.htm?keyword="),
    ("互联网信息", "https://www.cac.gov.cn/search.htm?keyword="),
    ("市场监督", "https://www.samr.gov.cn/search?q="),
    ("标准化", "https://std.samr.gov.cn/search?q="),
    ("工业和信息化", "https://www.miit.gov.cn/search?q="),
    ("工信部", "https://www.miit.gov.cn/search?q="),
    ("生态环境", "https://www.mee.gov.cn/search?q="),
    ("海关", "https://www.customs.gov.cn/search?q="),
    ("商务", "https://www.mofcom.gov.cn/search?q="),
    ("应急", "https://www.mem.gov.cn/search?q="),
    ("公安", "https://www.mps.gov.cn/search?q="),
    ("ISO", "https://www.iso.org/search.html?q="),
    ("欧盟", "https://europa.eu/!search?q="),
]


def build_fallback_url(source, name):
    """链接失效时的回退：优先该官网站内搜索，其次通用搜索。"""
    name = (name or "").strip()
    if not name:
        return ""
    for key, base in _SITE_SEARCH:
        if key in (source or ""):
            return base + urllib.parse.quote(name)
    return "https://www.baidu.com/s?wd=" + urllib.parse.quote(name + " 正文")


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

【八、铁律】
- 一切以官方文件/官网为唯一权威来源，不凭记忆或推断。
- 低消耗：聚焦最近变更，不无限展开；不为单条做几十次搜索。
- 每条 change 必须附 source_url（你核实所依据的官方页面链接）。
"""


def build_prompt(target_label, domain_text, existing_names):
    names_block = "\n".join(f"- {n}" for n in existing_names) or "（暂无）"
    return f"""你是中国法律法规与标准检索助手，负责维护一份「家电制造业体系工程师使用的法规/标准清单」（data.json，含 laws 与 standards 两张表）。你将运行：使用 web_search 联网检索最近约两周内与【范围】相关的法规/标准变更。一切以官方文件/官网为唯一权威来源，不凭记忆或推断。

═══ 本次检索范围（{target_label}）═══
{domain_text}

当前清单中已有的条目（权威去重基准，不要重复添加，名称相同或高度相似即视为已存在）：
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
  "source_url": "你核实本条所依据的官方页面链接（必填）",
  "note": "变更说明（人类可读，不写入数据）"
}}

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


def _name_match(name, items):
    for it in items:
        if it["name"] == name:
            return it
    shorter = min(name, key=len)
    if len(shorter) < 4:
        return None
    for it in items:
        if name in it["name"] or it["name"] in name:
            return it
    return None


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
            "dept": src, "effectiveDate": ch.get("effectiveDate", "") or today,
            "status": status, "domains": ch.get("domains", []) or [],
            "category": domain_id, "link": ch.get("link", ""),
            "region": ch.get("region", "全国") or "全国",
            "id": str(new_id), "remark": remark,
            "abolishDate": ch.get("abolishDate", "") or "",
            "adopted": adopted, "copyrightNote": (ch.get("copyrightNote") or "").strip(),
        }
    else:
        return {
            "name": name, "stdNo": ch.get("stdNo", "") or "",
            "stdType": ch.get("stdType", "") or "", "publisher": src,
            "effectiveDate": ch.get("effectiveDate", "") or today,
            "status": status, "link": ch.get("link", ""),
            "region": ch.get("region", "全国") or "全国",
            "id": str(new_id), "remark": remark,
            "abolishDate": ch.get("abolishDate", "") or "",
            "adopted": adopted, "copyrightNote": (ch.get("copyrightNote") or "").strip(),
        }


def apply_change(table, all_items, change, domain_id, today):
    """把一条 AI 变更应用到 all_items（原地修改/追加），并返回用于提案记录的 dict。
    返回 dict 含 kind/name/category/table/targetId/newRecord/setFields/display；kind=skip 表示跳过。"""
    action = (change.get("action") or "").strip().lower()
    name = (change.get("name") or "").strip()
    if not name or action not in ("add", "update", "abolish"):
        return {"kind": "skip", "name": name, "reason": "无效 action 或空名称"}
    src_field = "dept" if table == "laws" else "publisher"
    label = CATEGORY_NAMES.get(domain_id, domain_id)
    is_food = bool(re.search(r"GB\s*4806|GB\s*31604", (change.get("stdNo") or "") + (name or "")))

    if action == "add":
        # 去重（精确 + 近义包含）安全网：命中已有则跳过
        if _name_match(name, all_items):
            return {"kind": "skip", "name": name, "reason": "已存在（近义去重）"}
        new_id = max((int(it["id"]) for it in all_items if str(it["id"]).isdigit()), default=0) + 1
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
                            "reason": change.get("note", "") or "废止"}}

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
    src = (change.get("source") or "").strip()
    if src and src != target.get(src_field):
        set_fields[src_field] = src
        diffs.append({"field": "发布部门" if table == "laws" else "发布单位",
                      "from": target.get(src_field, ""), "to": src})
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
    new_url = (change.get("link") or "").strip()
    existing_url = (target.get("link") or "").strip()
    if new_url and new_url != existing_url:
        if is_homepage(new_url):
            pass
        elif not existing_url:
            if link_alive(new_url):
                set_fields["link"] = new_url
                diffs.append({"field": "来源链接", "from": "", "to": new_url})
            else:
                fb = build_fallback_url(src or target.get(src_field, ""), name)
                if fb:
                    set_fields["link"] = fb
                    diffs.append({"field": "来源链接(回退)", "from": "", "to": fb})
        elif is_homepage(existing_url):
            if link_alive(new_url):
                set_fields["link"] = new_url
                diffs.append({"field": "来源链接", "from": "(首页)", "to": new_url})
            else:
                fb = build_fallback_url(src or target.get(src_field, ""), name)
                if fb:
                    set_fields["link"] = fb
                    diffs.append({"field": "来源链接(回退)", "from": "", "to": fb})
        else:
            pass  # 信任现有深链
    # 应用
    for k, v in set_fields.items():
        target[k] = v
    if not diffs:
        return {"kind": "skip", "name": name, "reason": "无实质变更"}
    return {"kind": "update", "name": name, "category": label, "table": table,
            "targetId": tid, "newRecord": None, "setFields": set_fields,
            "display": {"diffs": diffs, "link": target.get("link", ""),
                        "source": target.get(src_field, ""),
                        "sourceUrl": (change.get("source_url") or "").strip(),
                        "reason": change.get("note", "") or "更新"}}


def apply_status_rules(proposed, today):
    """对 proposed 执行通用状态切换（日期到期自动转状态），返回切换清单供提案展示。直接修改 proposed。"""
    switched = []
    for table, key in (("laws", "laws"), ("standards", "standards")):
        for it in proposed[key]:
            old = it.get("status", "")
            new = old
            eff = _ymd(it.get("effectiveDate"))
            if old == "即将实施" and eff and eff <= today:
                new = "现行有效"
            ad = _ymd(it.get("abolishDate"))
            if ad and ad <= today and old != "已废止":
                new = "已废止"
            if new != old:
                it["status"] = new
                switched.append({"table": table, "name": it.get("name", ""), "id": it.get("id"),
                                 "from": old, "to": new})
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
        subprocess.run(["git", "add", "--"] + files, cwd=ROOT, check=False)
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

    model = os.environ.get("MODEL") or "glm-4-air"
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
    for table, cid in targets:
        if table == "laws":
            items = [l for l in proposed_laws if l.get("category") == cid]
            text = DOMAINS[cid]
            all_items = proposed_laws
        else:
            items = proposed_standards
            text = STANDARDS_TEXT
            all_items = proposed_standards
        existing_names = [it["name"] for it in items]
        label = CATEGORY_NAMES.get(cid, cid)
        print(f"检索：{label} ...")
        result = search_target(client, model, label, text, existing_names)
        changes = result.get("changes", []) or []
        print(f"  发现 {len(changes)} 条变更：{result.get('summary', '')}")
        for ch in changes:
            res = apply_change(table, all_items, ch, cid, today)
            if not res or res.get("kind") == "skip":
                if res:
                    print(f"    跳过（{res.get('reason')}）：{res.get('name')}")
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
            },
            "changes": [],
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
            proposed_changes["changes"].append({
                "id": f"c{len(proposed_changes['changes']) + 1}",
                "type": "status_switch",
                "table": s["table"],
                "name": s["name"],
                "category": s["table"],
                "targetId": s["id"],
                "newRecord": None,
                "setFields": {"status": s["to"]},
                "display": {"diffs": [{"field": "状态", "from": s["from"], "to": s["to"]}],
                            "link": "", "source": "", "sourceUrl": "", "reason": "到期自动状态切换"},
            })
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
