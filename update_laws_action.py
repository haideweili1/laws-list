#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律法规 / 产品标准 清单自动更新脚本（在 GitHub Actions 环境中运行）
============================================================
- 使用 智谱 GLM（国内可访问、有免费额度）自带的 web_search 联网检索能力
- 检索最近两周中国新发布 / 修订 / 废止的法律法规与产品标准（GB/T、行业标准、ISO 等）
- 更新同目录下的 data.json（laws + standards 双表）并交回 GitHub Actions 提交
- 内置【通用状态自动切换机制】（长期主义核心）：
    * 状态为「即将实施」且实施日期已到  -> 自动转为「现行有效」
    * 设有「废止日期」且已到              -> 自动转为「已废止」
  因此如《生态环境法典》2026-08-15 施行、相关 8 部环境法同日废止，
  无需单独定时任务，每周/手动检索到该日期后自动切换。
- 写出 update-summary.json（本次更新说明）与 retrieval-status.json（前端状态轮询用）

依赖的环境变量：
  ZHIPU_API_KEY  (必填)  在 https://open.bigmodel.cn 免费申请的 API Key
  MODEL            (可选)  模型名，默认 glm-4-air（支持 web_search 的模型）

设计说明：
  - 任何异常都不会中断工作流，确保 GitHub Pages 始终可用。
  - 链接保护：仅当现有链接缺失/是首页时才用 AI 给的链接，且新链需探活；否则信任现有深链。
"""
import os
import json
import re
import sys
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
    """跟随重定向探测链接是否可访问且未跳回首页。404 视为死；
    其他 HTTP 错误（如 403 反爬）保守视为活着，避免误删好链接。"""
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


# ===== 通用状态自动切换机制（长期主义核心）=====
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


def apply_status_rules(laws, standards, today):
    """对全部记录执行通用状态切换，返回切换清单（供更新说明展示）。"""
    switched = []
    for table, items in (("法规", laws), ("标准", standards)):
        for it in items:
            old = it.get("status", "")
            new = old
            # 即将实施 -> 现行有效（实施日期已到）
            eff = _ymd(it.get("effectiveDate"))
            if old == "即将实施" and eff and eff <= today:
                new = "现行有效"
            # 有废止日期且已到 -> 已废止
            ad = _ymd(it.get("abolishDate"))
            if ad and ad <= today and old != "已废止":
                new = "已废止"
            if new != old:
                it["status"] = new
                switched.append({"table": table, "name": it.get("name", ""),
                                 "from": old, "to": new})
    return switched


def norm_status(s):
    s = (s or "").strip()
    return {"在用": "现行有效", "废止": "已废止",
            "现行有效": "现行有效", "即将实施": "即将实施",
            "已废止": "已废止"}.get(s, s)


# ===== 检索领域（喂给模型做定向检索）=====
DOMAINS = {
    "trisystem": (
        "三体系（质量管理体系 ISO9001、环境管理体系 ISO14001、职业健康安全管理体系 ISO45001）相关："
        "产品质量法、计量法、标准化法、认证认可条例、强制性产品认证、环境保护法、水/大气/土壤污染防治法、"
        "固体废物污染环境防治法、噪声污染防治法、碳排放与节能相关法规、安全生产法、职业病防治法、劳动法、"
        "特种设备安全、危险化学品安全等"
    ),
    "social": (
        "社会责任相关：劳动合同法、社会保险法、工伤保险条例、妇女权益保障法、未成年人保护法、残疾人保障法、"
        "工会法、就业促进法、女职工劳动保护特别规定、带薪年休假条例、保障农民工工资支付条例等"
    ),
    "antiterror": (
        "反恐与供应链安全相关：反恐怖主义法、海关法、进出口商品检验法、出境入境管理法、对外贸易法、"
        "海关 AEO 认证与信用管理办法、易制毒化学品管理条例、出口管制相关法规等"
    ),
    "infosec": (
        "信息安全相关：网络安全法、数据安全法、个人信息保护法、密码法、关键信息基础设施安全保护条例、"
        "网络数据安全管理条例、信息安全技术类国家标准(GB/T)、互联网信息服务算法推荐/深度合成管理规定、"
        "网络安全审查办法、数据出境安全评估办法等"
    ),
}

STANDARDS_TEXT = (
    "产品标准相关：与本公司产品有关的强制性国家标准(GB)、推荐性国家标准(GB/T)、行业标准、"
    "国际标准(ISO)的最新发布、修订、替代、作废。重点关注：国家标准公告、标准替代关系"
    "（如 GB/T X-202X 替代 GB/T X-201X）、标准实施日期变更、旧标准转为废止/废止日期。"
)

CATEGORY_NAMES = {
    "trisystem": "三体系 (ISO 9001/14001/45001)",
    "social": "社会责任",
    "antiterror": "反恐/供应链安全",
    "infosec": "信息安全",
    "standards": "产品标准",
}


def build_prompt(target_label, domain_text, existing_names):
    names_block = "\n".join(f"- {n}" for n in existing_names) or "（暂无）"
    return f"""你是中国法律法规与标准检索助手。请使用联网搜索（web_search），查找最近两周内（重点是最新发布、实施或修订）中国国家级、与以下领域相关的法律法规、行政法规、部门规章、国家标准(GB/T)的变更：

领域：{domain_text}

当前清单中已有的条目（仅供你判断哪些是新增/修订/废止，不要重复添加已有条目）：
{names_block}

要求：
1. 只关注「正在实施、非废止」的文件；若发现清单中某部法规/标准已被废止、被新标准替代或修订，请标记。
2. link 必须是【能直接查看该条目正文】的官方页面链接，优先使用：npc.gov.cn / gov.cn / cac.gov.cn / miit.gov.cn / openstd.samr.gov.cn。
3. 严禁返回搜索结果页、列表页、栏目首页、官网首页、新闻稿页（除非该新闻稿页就是正文发布页）。
   判断标准：打开链接后页面应直接显示【标题 + 完整条文/标准全文】；若只是目录或搜索框则该链接不合格。
4. 请勿编造不存在的法规/标准，没有确凿依据时不要返回。

请以 JSON 格式返回（无变更则 changes 为空数组）：
{{
  "changes": [
    {{
      "action": "add" | "update" | "abolish",
      "name": "全称",
      "source": "发布机关官网，如 中国政府网 / 中国人大网 / 国家网信办 / 工业和信息化部 / 国家标准化管理委员会 / 国际标准化组织(ISO)",
      "link": "官方网页链接",
      "effectiveDate": "实施日期 YYYY-MM-DD，未知填空字符串",
      "status": "现行有效" 或 "已废止" 或 "即将实施",
      "note": "一句话说明变更"
    }}
  ],
  "summary": "本次检索小结"
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
            temperature=0.2,
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


def make_new_record(table, name, ch, domain_id, today, new_id):
    status = norm_status(ch.get("status")) or "现行有效"
    src = (ch.get("source") or "").strip() or ("中国政府网" if table == "laws" else "国家标准化管理委员会")
    if table == "laws":
        return {
            "name": name, "docNumber": ch.get("docNumber", "") or "",
            "dept": src, "effectiveDate": ch.get("effectiveDate", "") or today,
            "status": status, "domains": ch.get("domains", []) or [],
            "category": domain_id, "link": ch.get("link", ""),
            "region": ch.get("region", "全国") or "全国",
            "id": str(new_id), "remark": ch.get("note", "") or "",
            "abolishDate": ch.get("abolishDate", "") or "",
        }
    else:
        return {
            "name": name, "stdNo": ch.get("stdNo", "") or "",
            "stdType": ch.get("stdType", "") or "", "publisher": src,
            "effectiveDate": ch.get("effectiveDate", "") or today,
            "status": status, "link": ch.get("link", ""),
            "region": ch.get("region", "全国") or "全国",
            "id": str(new_id), "remark": ch.get("note", "") or "",
            "abolishDate": ch.get("abolishDate", "") or "",
        }


def apply_change(table, all_items, change, domain_id, today):
    """把一条 AI 变更应用到 all_items（原地修改/追加）。返回 (kind, name, detail)。"""
    action = (change.get("action") or "").strip().lower()
    name = (change.get("name") or "").strip()
    if not name or action not in ("add", "update", "abolish"):
        return None
    src_field = "dept" if table == "laws" else "publisher"

    if action == "add":
        if any(name == it["name"] for it in all_items):
            return ("skip", name, "已存在")
        new_id = max((int(it["id"]) for it in all_items if str(it["id"]).isdigit()), default=0) + 1
        all_items.append(make_new_record(table, name, change, domain_id, today, new_id))
        return ("add", name, change.get("note", ""))

    target = _name_match(name, all_items)
    if not target:
        return ("skip", name, "未匹配到现有条目")
    if action == "abolish":
        target["status"] = "已废止"
        return ("abolish", name, "状态 → 已废止")
    # update
    updated = []
    if change.get("effectiveDate") and change["effectiveDate"] != target.get("effectiveDate"):
        target["effectiveDate"] = change["effectiveDate"]
        updated.append("实施时间")
    new_status = norm_status(change.get("status"))
    if new_status and new_status != target.get("status"):
        target["status"] = new_status
        updated.append("状态")
    src = (change.get("source") or "").strip()
    if src and src != target.get(src_field):
        target[src_field] = src
        updated.append("发布部门" if table == "laws" else "发布单位")
    # 链接保护：仅当现有缺失/是首页时才用新链，且新链需探活
    new_url = (change.get("link") or "").strip()
    existing_url = (target.get("link") or "").strip()
    if new_url and new_url != existing_url:
        if is_homepage(new_url):
            pass
        elif not existing_url:
            if link_alive(new_url):
                target["link"] = new_url
                updated.append("来源链接")
            else:
                fb = build_fallback_url(src or target.get(src_field, ""), name)
                if fb:
                    target["link"] = fb
                    updated.append("来源链接(回退)")
        elif is_homepage(existing_url):
            if link_alive(new_url):
                target["link"] = new_url
                updated.append("来源链接")
            else:
                fb = build_fallback_url(src or target.get(src_field, ""), name)
                if fb:
                    target["link"] = fb
                    updated.append("来源链接(回退)")
        else:
            pass  # 信任现有深链
    if updated:
        return ("update", name, "更新：" + "、".join(updated))
    return ("skip", name, "无实质变更")


def get_prev_data_from_git():
    """读取上一次提交的 data.json（作为政府更新前的基线用于比对覆盖手动修改）。"""
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
    """政府更新了某条目字段时，清除用户对该字段的"已修改"标记（若存在 user-edits.json）。"""
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


def write_final_status(status, last_updated=None, error=None):
    try:
        data = {"status": status, "updatedAt": now_iso()}
        if last_updated:
            data["lastUpdated"] = last_updated
        if error:
            data["error"] = error
        with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        git_commit_push([RETRIEVAL_STATUS_PATH, "update-summary.json", "data.json"],
                        f"chore: 检索{status}")
        print(f"  已写入检索状态：{status}")
    except Exception as e:
        print("  写入 final 状态失败（可忽略）:", e)


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

    # —— 通用状态自动切换（先于/独立于 GLM 检索，确保到期法规如生态环境法典按时切换）——
    switched = apply_status_rules(laws, standards, today)
    for s in switched:
        print(f"  [状态切换] {s['table']}《{s['name']}》{s['from']} → {s['to']}")

    # —— GLM 联网检索各域 ——
    targets = [
        ("laws", "trisystem"), ("laws", "social"),
        ("laws", "antiterror"), ("laws", "infosec"),
        ("standards", "standards"),
    ]
    n_added = n_abolished = n_updated = 0
    summary_changes = []
    for table, cid in targets:
        if table == "laws":
            items = [l for l in laws if l.get("category") == cid]
            text = DOMAINS[cid]
        else:
            items = standards
            text = STANDARDS_TEXT
        existing_names = [it["name"] for it in items]
        label = CATEGORY_NAMES.get(cid, cid)
        print(f"检索：{label} ...")
        result = search_target(client, model, label, text, existing_names)
        changes = result.get("changes", []) or []
        print(f"  发现 {len(changes)} 条变更：{result.get('summary', '')}")
        for ch in changes:
            res = apply_change(table, items if table == "standards" else laws, ch, cid, today)
            if not res or res[0] == "skip":
                if res:
                    print(f"    跳过（{res[2]}）：{res[1]}")
                continue
            kind, name, detail = res
            if kind == "add":
                n_added += 1
            elif kind == "abolish":
                n_abolished += 1
            else:
                n_updated += 1
            summary_changes.append({
                "type": kind, "name": name,
                "category": label, "detail": detail,
            })
            print(f"    [{kind}] {name}（{detail}）")

    # 无论内容是否变更，刷新"最近更新时间"
    data["lastUpdated"] = today
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 更新说明
    for s in switched:
        summary_changes.append({
            "type": "status_switch", "name": s["name"],
            "category": s["table"], "detail": f"状态：{s['from']} → {s['to']}",
        })
    summary = {
        "updatedAt": today,
        "hasUpdates": (n_added + n_abolished + n_updated + len(switched)) > 0,
        "counts": {"added": n_added, "abolished": n_abolished,
                   "updated": n_updated, "statusSwitched": len(switched)},
        "changes": summary_changes,
    }
    try:
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  已写出 update-summary.json（hasUpdates={summary['hasUpdates']}）")
    except Exception as e:
        print(f"  写出 update-summary.json 失败：{e}")

    prev_data = get_prev_data_from_git()
    reconcile_user_overrides(prev_data, data)

    total = n_added + n_abolished + n_updated + len(switched)
    if total > 0:
        print(f"\n本次共处理 {total} 条（新增 {n_added} / 修改 {n_updated} / 废止 {n_abolished} / 状态切换 {len(switched)}），lastUpdated -> {today}")
    else:
        print(f"\n本次无内容变更，仅刷新更新时间 -> {today}")
    write_final_status("success", last_updated=today)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        write_final_status("failed", error=repr(e))
        sys.exit(1)
