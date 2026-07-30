#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律法规清单自动更新脚本（在 GitHub Actions 环境中运行）
=========================================================
- 使用 智谱 GLM（国内可访问、有免费额度）自带的 web_search 联网检索能力
- 检索最近两周中国新发布 / 修订 / 废止的法律法规
- 更新同目录下的 laws.json 并交回 GitHub Actions 提交

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
import traceback
from datetime import date

try:
    from zhipuai import ZhipuAI
except ImportError:
    print("缺少 zhipuai 库，请先执行: pip install zhipuai")
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
LAWS_PATH = os.path.join(ROOT, "laws.json")
USER_EDITS_PATH = os.path.join(ROOT, "user-edits.json")

# 参与"政府更新 vs 用户手动修改"比对的字段
FIELDS = ["name", "source", "sourceUrl", "effectiveDate", "introducedDate",
          "status", "storageMethod", "retentionPeriod"]

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


def main():
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("缺少环境变量 ZHIPU_API_KEY，跳过更新（保持原数据）。")
        sys.exit(0)

    model = os.environ.get("MODEL") or "glm-4-air"
    client = ZhipuAI(api_key=api_key)

    try:
        with open(LAWS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取 laws.json 失败: {e}")
        sys.exit(1)

    cat_by_id = {c["id"]: c for c in data["categories"]}
    today = date.today().isoformat()
    total_changes = 0

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
                total_changes += 1
            else:
                target = _name_match(name, cat["laws"])
                if not target:
                    print(f"    未匹配到现有法规，跳过：{name}")
                    continue
                if action == "abolish":
                    target["status"] = "废止"
                    print(f"    [废止] {name}")
                else:
                    if ch.get("effectiveDate"):
                        target["effectiveDate"] = ch["effectiveDate"]
                    if ch.get("sourceUrl"):
                        target["sourceUrl"] = ch["sourceUrl"]
                    if ch.get("source"):
                        target["source"] = ch["source"]
                    print(f"    [更新] {name}")
                total_changes += 1

    # 无论是否有法规内容变更，都更新"最近更新时间"为本次运行日期
    # （对应需求：点击运行/定时任务执行后，立即刷新更新时间）
    data["lastUpdated"] = today
    with open(LAWS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 需求 7：政府更新了法规字段时，覆盖用户的手动修改并清除"已修改"标识
    prev_data = get_prev_laws_from_git()
    reconcile_user_overrides(prev_data, data)

    if total_changes > 0:
        print(f"\n共更新 {total_changes} 条，lastUpdated -> {today}")
    else:
        print(f"\n本次无法规内容变更，但已刷新更新时间 -> {today}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"\n[致命错误] 更新脚本异常退出: {repr(e)}", file=sys.stderr)
        sys.exit(1)
