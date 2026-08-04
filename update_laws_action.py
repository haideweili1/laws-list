#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律法规清单自动更新脚本（在 GitHub Actions 环境中运行）
=========================================================
- 使用 智谱 GLM（国内可访问、有免费额度）自带的 web_search 联网检索能力
- 检索最近两周中国新发布 / 修订 / 废止的法律法规
- 更新同目录下的 laws.json 并交回 GitHub Actions 提交
- 同时写出 update-summary.json（本次更新说明，供网页"更新说明"面板展示）

依赖的环境变量：
  ZHIPU_API_KEY  (必填)  在 https://open.bigmodel.cn 免费申请的 API Key
  MODEL            (可选)  模型名，默认 glm-4-air（支持 web_search 的模型）

设计说明：
  - 只保留「正在实施、非废止」的文件；若发现已有法规被废止/修订会做标记。
  - 新增法规自动编号、归入对应分类，并补全字段。
  - 任何异常都不会中断工作流，确保 GitHub Pages 始终可用。
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
LAWS_PATH = os.path.join(ROOT, "laws.json")
USER_EDITS_PATH = os.path.join(ROOT, "user-edits.json")
SUMMARY_PATH = os.path.join(ROOT, "update-summary.json")
RETRIEVAL_STATUS_PATH = os.path.join(ROOT, "retrieval-status.json")

# 参与"政府更新 vs 用户手动修改"比对的字段
FIELDS = ["name", "source", "sourceUrl", "effectiveDate", "introducedDate",
          "status", "storageMethod", "retentionPeriod"]

# ===== 链接校验与回退（仅对新增/变更的少量链接触发，低资源） =====
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def is_homepage(url):
    """判断 URL 是否为网站根/首页（不含具体路径）"""
    if not url:
        return False
    try:
        p = urllib.parse.urlparse(str(url).strip())
        path = (p.path or "").rstrip("/")
        return path == ""
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
                return False  # 被重定向回首页
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return True  # 403 等反爬，保守当作活着
    except Exception:
        return False


# 主要来源站点的站内搜索入口（回退第一级）
_SITE_SEARCH = [
    ("中国人大网", "https://www.npc.gov.cn/npc/c2/huiyi/search?keyword="),
    ("中国政府网", "https://www.gov.cn/zhengce/advanced_search?q="),
    ("国家网信办", "https://www.cac.gov.cn/search.htm?keyword="),
    ("工信部", "https://www.miit.gov.cn/search?q="),
    ("国家标准委", "https://std.samr.gov.cn/search?q="),
    ("生态环境部", "https://www.mee.gov.cn/search?q="),
    ("应急管理部", "https://www.mem.gov.cn/search?q="),
]


def build_fallback_url(source, name):
    """链接失效时的回退：第一级该官网站内搜索；第二级（不限官网）通用搜索。"""
    name = (name or "").strip()
    if not name:
        return ""
    for key, base in _SITE_SEARCH:
        if key in (source or ""):
            return base + urllib.parse.quote(name)
    # 第二级：通用搜索引擎搜"法规名 正文"，点开可见各官网正文入口，零额外调用
    return "https://www.baidu.com/s?wd=" + urllib.parse.quote(name + " 正文")

# 四大分类的检索领域说明（喂给模型做定向检索）
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

CATEGORY_NAMES = {
    "trisystem": "三体系 (ISO 9001/14001/45001)",
    "social": "社会责任",
    "antiterror": "反恐/供应链安全",
    "infosec": "信息安全",
}


def build_prompt(category_id, existing_names):
    domain = DOMAINS[category_id]
    names_block = "\n".join(f"- {n}" for n in existing_names) or "（暂无）"
    return f"""你是中国法律法规检索助手。请使用联网搜索（web_search），查找最近两周内（重点是最新发布、实施或修订）中国国家级、与以下领域相关的法律法规、行政法规、部门规章、国家标准(GB/T)的变更：

领域：{domain}

当前清单中已有的法规（仅供你判断哪些是新增/修订/废止，不要重复添加已有条目）：
{names_block}

要求：
1. 只关注「正在实施、非废止」的文件；若发现清单中某部法规已被废止或修订，请标记。
2. sourceUrl 必须是【能直接查看该法规正文】的官方页面链接，优先使用：npc.gov.cn / gov.cn / cac.gov.cn / miit.gov.cn / openstd.samr.gov.cn。
3. 严禁返回以下"非正文"链接：搜索结果页、列表页、栏目首页、官网首页、新闻稿页（除非该新闻稿页就是法规正文发布页）。
   判断标准：打开该链接后，页面应直接显示法规的【标题 + 完整条文】；若只是目录或搜索框，则该链接不合格，请继续查找"全文"页。
   例如：中国政府网应优先用"政策文件库"的具体条文页（URL 形如 .../zhengce/.../content_....shtml），而非 /zhengce/ 栏目首页。
4. 请勿编造不存在的法规，没有确凿依据时不要返回。

请以 JSON 格式返回（无变更则 changes 为空数组）：
{{
  "changes": [
    {{
      "action": "add" | "update" | "abolish",
      "name": "法规全称",
      "source": "发布机关官网，如 中国政府网 / 中国人大网 / 国家网信办 / 工业和信息化部 / 国家标准化管理委员会",
      "sourceUrl": "官方网页链接",
      "effectiveDate": "实施日期 YYYY-MM-DD，未知填空字符串",
      "status": "在用" 或 "废止",
      "note": "一句话说明变更"
    }}
  ],
  "summary": "本次检索小结"
}}
只输出 JSON，不要额外说明文字。"""


def extract_json(text):
    """从模型返回中稳健地提取 JSON 字符串。"""
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1:
        text = text[s:e + 1]
    return text


def search_category(client, model, category_id, existing_names):
    prompt = build_prompt(category_id, existing_names)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            tools=[{"type": "web_search", "web_search": {"enable": True, "search_result": True}}],
            temperature=0.2,
        )
        return json.loads(extract_json(resp.choices[0].message.content))
    except Exception as e:
        print(f"  [{category_id}] 检索出错: {e}")
        return {"changes": [], "summary": f"检索出错: {e}"}


def _name_match(name, laws):
    """按名称匹配已有法规，优先精确匹配。"""
    for l in laws:
        if l["name"] == name:
            return l
    # 容错：包含匹配，但要求较短串长度 >= 4 避免误匹配
    shorter = min(name, key=len)
    if len(shorter) < 4:
        return None
    for l in laws:
        if name in l["name"] or l["name"] in name:
            return l
    return None


def get_prev_laws_from_git():
    """读取上一次提交的 laws.json（作为"政府更新前的基线"用于比对）。失败返回 None。"""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "show", "HEAD:laws.json"],
            cwd=ROOT, capture_output=True, text=True, timeout=30
        )
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except Exception as e:
        print(f"  [reconcile] 无法读取上版本 laws.json（跳过覆盖清理）：{e}")
        return None


def reconcile_user_overrides(prev_data, new_data):
    """
    需求 7：自动检索更新了某部法规的正文/状态等字段时，应当覆盖用户对该字段的手动修改，
    并清除网页上的"已修改"标识；用户修改过、但政府【未】变更的字段则保留（不被覆盖）。
    做法：比对 prev_data 与 new_data 的逐字段差异，凡是政府变更的字段，就从 user-edits.json
    的 lawOverrides 中删掉对应字段（即清除"已修改"标记，显示政府最新值）。
    """
    if not prev_data:
        return
    if not os.path.exists(USER_EDITS_PATH):
        return  # 没有用户手动编辑，无需处理
    try:
        with open(USER_EDITS_PATH, "r", encoding="utf-8") as f:
            ue = json.load(f)
    except Exception as e:
        print(f"  [reconcile] 读取 user-edits.json 失败，跳过：{e}")
        return

    prev_by_key = {}
    for c in prev_data.get("categories", []):
        for l in c.get("laws", []):
            prev_by_key[f"{c['id']}::{l['id']}"] = l

    overrides = ue.get("lawOverrides") or {}
    override_ts = ue.get("overrideTs") or {}
    changed = False
    for c in new_data.get("categories", []):
        for l in c.get("laws", []):
            key = f"{c['id']}::{l['id']}"
            prev_law = prev_by_key.get(key)
            if not prev_law:
                continue  # 新增法规，没有历史覆盖
            ov = overrides.get(key)
            if not ov:
                continue
            # 找出政府本次变更的字段
            changed_fields = [fld for fld in FIELDS
                              if (l.get(fld) or "") != (prev_law.get(fld) or "")]
            if not changed_fields:
                continue
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
        try:
            with open(USER_EDITS_PATH, "w", encoding="utf-8") as f:
                json.dump(ue, f, ensure_ascii=False, indent=2)
            print("  [reconcile] 已更新 user-edits.json，清除被政府覆盖的'已修改'字段")
        except Exception as e:
            print(f"  [reconcile] 写回 user-edits.json 失败：{e}")
    else:
        print("  [reconcile] 无需要清除的用户手动修改字段")


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _git_config():
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=False)
    subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=False)


def git_commit_push(files, message):
    """把指定文件加入暂存区并提交、推送到 origin（依赖 Actions checkout 注入的凭据）。"""
    try:
        _git_config()
        subprocess.run(["git", "add", "--"] + files, cwd=ROOT, check=False)
        r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if r.returncode == 0:
            return  # 无暂存变化，跳过
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=False)
        subprocess.run(["git", "push"], cwd=ROOT, check=False)
    except Exception as e:
        print("  [git] 提交/推送失败（可忽略）:", e)


def write_running_status():
    """检索刚开始：写出 running 状态（前端据此显示'检索中'）。"""
    try:
        with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({"status": "running", "updatedAt": now_iso()}, f, ensure_ascii=False, indent=2)
        git_commit_push([RETRIEVAL_STATUS_PATH], "chore: 检索进行中")
        print("  已写入检索状态：running")
    except Exception as e:
        print("  写入 running 状态失败（可忽略）:", e)


def write_final_status(status, last_updated=None, error=None):
    """检索结束：写出 success/failed 状态，连同 laws.json 与 update-summary.json 一并提交。"""
    try:
        data = {"status": status, "updatedAt": now_iso()}
        if last_updated:
            data["lastUpdated"] = last_updated
        if error:
            data["error"] = error
        with open(RETRIEVAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        git_commit_push([RETRIEVAL_STATUS_PATH, "update-summary.json", "laws.json"],
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
        with open(LAWS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取 laws.json 失败: {e}")
        sys.exit(1)

    cat_by_id = {c["id"]: c for c in data["categories"]}
    today = date.today().isoformat()

    # 本次变更统计与说明
    n_added = n_abolished = n_updated = 0
    summary_changes = []

    for cid in DOMAINS:
        cat = cat_by_id.get(cid)
        if not cat:
            print(f"分类 {cid} 不存在，跳过")
            continue
        existing_names = [l["name"] for l in cat["laws"]]
        print(f"检索分类：{CATEGORY_NAMES.get(cid, cid)} ...")
        result = search_category(client, model, cid, existing_names)
        changes = result.get("changes", []) or []
        print(f"  发现 {len(changes)} 条变更：{result.get('summary', '')}")

        def max_id():
            nums = []
            for l in cat["laws"]:
                try:
                    nums.append(int(l["id"]))
                except Exception:
                    pass
            return max(nums) if nums else 0

        for ch in changes:
            action = (ch.get("action") or "").strip().lower()
            name = (ch.get("name") or "").strip()
            if not name or action not in ("add", "update", "abolish"):
                continue

            if action == "add":
                if any(name == l["name"] for l in cat["laws"]):
                    print(f"    跳过（已存在）：{name}")
                    continue
                new_id = max_id() + 1
                cat["laws"].append({
                    "id": str(new_id),
                    "name": name,
                    "source": ch.get("source", "中国政府网"),
                    "sourceUrl": ch.get("sourceUrl", ""),
                    "effectiveDate": ch.get("effectiveDate", ""),
                    "introducedDate": today,
                    "status": ch.get("status", "在用") or "在用",
                    "storageMethod": "电子档",
                    "retentionPeriod": "三年",
                })
                print(f"    [新增] {name}")
                summary_changes.append({
                    "type": "add",
                    "name": name,
                    "category": CATEGORY_NAMES.get(cid, cid),
                    "detail": "新增法规",
                })
                n_added += 1
            else:
                target = _name_match(name, cat["laws"])
                if not target:
                    print(f"    未匹配到现有法规，跳过：{name}")
                    continue
                if action == "abolish":
                    target["status"] = "废止"
                    print(f"    [废止] {name}")
                    summary_changes.append({
                        "type": "abolish",
                        "name": name,
                        "category": CATEGORY_NAMES.get(cid, cid),
                        "detail": "使用状态：在用 → 废止",
                    })
                    n_abolished += 1
                else:
                    updated_fields = []
                    # 实施时间：仅当 AI 给的值与现有值不同才写
                    if ch.get("effectiveDate") and ch["effectiveDate"] != target.get("effectiveDate"):
                        target["effectiveDate"] = ch["effectiveDate"]
                        updated_fields.append("实施时间")
                    # 来源网站：仅当不同才写
                    if ch.get("source") and ch["source"] != target.get("source"):
                        target["source"] = ch["source"]
                        updated_fields.append("来源网站")
                    # 来源链接：保护现有深链；仅在现有缺失/是首页时补充，且新链需探活
                    new_url = (ch.get("sourceUrl") or "").strip()
                    existing_url = (target.get("sourceUrl") or "").strip()
                    if new_url and new_url != existing_url:
                        if is_homepage(new_url):
                            pass  # AI 给的是首页/根，不覆盖现有（保护深链）
                        elif not existing_url:
                            # 现有无链接：探活新链，活着才采用，否则回退
                            if link_alive(new_url):
                                target["sourceUrl"] = new_url
                                updated_fields.append("来源链接")
                            else:
                                fb = build_fallback_url(ch.get("source") or target.get("source", ""), target.get("name", ""))
                                if fb:
                                    target["sourceUrl"] = fb
                                    updated_fields.append("来源链接(回退)")
                        elif is_homepage(existing_url):
                            # 现有是首页：AI 给深链则采用（探活），否则回退通用搜索
                            if link_alive(new_url):
                                target["sourceUrl"] = new_url
                                updated_fields.append("来源链接")
                            else:
                                fb = build_fallback_url(ch.get("source") or target.get("source", ""), target.get("name", ""))
                                if fb:
                                    target["sourceUrl"] = fb
                                    updated_fields.append("来源链接(回退)")
                        else:
                            # 现有是深链：信任现有，不覆盖（保护用户原好链接）
                            pass
                    if updated_fields:
                        detail = "更新：" + "、".join(updated_fields)
                        print(f"    [更新] {name}（{detail}）")
                        summary_changes.append({
                            "type": "update",
                            "name": name,
                            "category": CATEGORY_NAMES.get(cid, cid),
                            "detail": detail,
                        })
                        n_updated += 1
                    else:
                        print(f"    [无实质变更，跳过] {name}")

    # 无论是否有法规内容变更，都更新"最近更新时间"为本次运行日期
    # （对应需求：点击运行/定时任务执行后，立即刷新更新时间）
    data["lastUpdated"] = today
    with open(LAWS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 写出本次更新说明（供网页"更新说明"面板展示）
    summary = {
        "updatedAt": today,
        "hasUpdates": (n_added + n_abolished + n_updated) > 0,
        "counts": {"added": n_added, "abolished": n_abolished, "updated": n_updated},
        "changes": summary_changes,
    }
    try:
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  已写出更新说明 update-summary.json（hasUpdates={summary['hasUpdates']}）")
    except Exception as e:
        print(f"  写出 update-summary.json 失败：{e}")

    # 需求 7：政府更新了法规字段时，覆盖用户的手动修改并清除"已修改"标识
    prev_data = get_prev_laws_from_git()
    reconcile_user_overrides(prev_data, data)

    total = n_added + n_abolished + n_updated
    if total > 0:
        print(f"\n共更新 {total} 条（新增 {n_added} / 修改 {n_updated} / 废止 {n_abolished}），lastUpdated -> {today}")
    else:
        print(f"\n本次无法规内容变更，但已刷新更新时间 -> {today}")
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
