#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存量法规链接一次性体检脚本（独立工具，不依赖 zhipuai）
==================================================
- 扫描 laws.json 中全部 sourceUrl，逐个 HTTP 探活（跟随重定向）
- 判定每条链接：✅ 正常 / ❌ 404 失效 / ⚠️ 跳回首页 / ⚠️ 访问异常
- 产出 link-report.json 报告（不修改 laws.json，便于人工审阅后修复）

用法（任选其一）：
  1) 本机直接跑：  python check_links.py
  2) GitHub Actions 上跑：把本文件推上去，在仓库 Actions 页手动 Run 一个临时 job（或本地执行）

设计：仅一次性探活，不增加日常消耗；符合"免费 + 低资源"原则。
"""
import os
import json
import sys
import urllib.request
import urllib.parse
import ssl

ROOT = os.path.dirname(os.path.abspath(__file__))
LAWS_PATH = os.path.join(ROOT, "laws.json")
REPORT_PATH = os.path.join(ROOT, "link-report.json")

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


def _probe(url, timeout=8):
    """返回 (status, final_url)。status: ok / dead / jump_home / error。
    error 可能意味着网络不可达（沙箱环境）或站点反爬，需人工判断。"""
    url = (url or "").strip()
    if not url:
        return "empty", url
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
                return "dead", final
            if is_homepage(final) and not is_homepage(url):
                return "jump_home", final
            return "ok", final
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "dead", url
        return "error", url  # 403 等反爬，标记 error 由人判断
    except Exception:
        return "error", url


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
    name = (name or "").strip()
    if not name:
        return ""
    for key, base in _SITE_SEARCH:
        if key in (source or ""):
            return base + urllib.parse.quote(name)
    return "https://www.baidu.com/s?wd=" + urllib.parse.quote(name + " 正文")


def main():
    if not os.path.exists(LAWS_PATH):
        print(f"未找到 {LAWS_PATH}")
        sys.exit(1)
    with open(LAWS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    results = []
    counts = {"ok": 0, "dead": 0, "jump_home": 0, "error": 0, "empty": 0}
    for cat in data.get("categories", []):
        cname = cat.get("name", cat.get("id", ""))
        for law in cat.get("laws", []):
            url = (law.get("sourceUrl") or "").strip()
            name = law.get("name", "")
            source = law.get("source", "")
            if not url:
                counts["empty"] += 1
                results.append({"category": cname, "name": name, "source": source,
                                "sourceUrl": "", "status": "empty",
                                "finalUrl": "", "suggestion": ""})
                continue
            status, final = _probe(url)
            counts[status] = counts.get(status, 0) + 1
            sug = ""
            if status in ("dead", "jump_home"):
                sug = build_fallback_url(source, name)
            results.append({"category": cname, "name": name, "source": source,
                            "sourceUrl": url, "status": status,
                            "finalUrl": final, "suggestion": sug})

    report = {"total": len(results), "counts": counts, "links": results}
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    bad = counts["dead"] + counts["jump_home"]
    print(f"共检查链接 {len(results)} 条：")
    print(f"  ✅ 正常: {counts['ok']}")
    print(f"  ❌ 404 失效: {counts['dead']}")
    print(f"  ⚠️ 跳回首页: {counts['jump_home']}")
    print(f"  ⚠️ 访问异常(error，可能网络受限或反爬): {counts['error']}")
    print(f"  ➖ 无链接: {counts['empty']}")
    print(f"需关注的失效/跳首页链接共 {bad} 条，已写入 {REPORT_PATH}")
    if counts["error"] and counts["error"] >= len(results) * 0.5:
        print("\n提示：error 占比很高，可能是当前网络环境无法访问政府网站（如沙箱限制），"
              "建议在能联网的本机运行本脚本。")


if __name__ == "__main__":
    main()
