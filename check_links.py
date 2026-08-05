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
import re
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


# 用于把页面标题里的网站名剥掉，判断是否只剩“首页/官网”等空壳标题
_SITE_NAMES = [
    "中国人大网", "中国政府网", "国家互联网信息办公室", "中央网络安全和信息化委员会办公室",
    "工业和信息化部", "商务部", "国务院", "生态环境部", "应急管理部",
    "国家标准化管理委员会", "国家标准委", "国家市场监督管理总局", "国家新闻出版署",
    "最高人民法院", "最高人民检察院", "公安部", "司法部", "人力资源社会保障部",
    "自然资源部", "住房城乡建设部", "交通运输部", "海关总署",
]
_GENERIC_TITLES = {"首页", "网站首页", "欢迎访问", "welcome", "index", "百度一下", "百度"}


def _get_title(text):
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    return (m.group(1).strip() if m else "")


def _norm_title(title):
    t = (title or "").strip()
    for s in _SITE_NAMES:
        t = t.replace(s, "")
    return t.strip().strip("_-｜|· ").strip()


def is_homepage_shell(title, text):
    """首页壳检测：返回 200 但内容其实是官网首页/通用页（如旧法律迁走后，
    同网址吐出“中国人大网”首页标题、无具体法规正文）。这种 urllib 看不到跳转，
    必须靠标题/内容识别。"""
    norm = _norm_title(title)
    if not norm:
        return True
    if norm.lower() in _GENERIC_TITLES:
        return True
    return False


def _probe(url, timeout=10):
    """返回 (status, final_url, title)。status: ok / dead / jump_home / homepage / error。
    - dead: HTTP>=400（含404）
    - jump_home: HTTP 层重定向到域名根（网址变了）
    - homepage: HTTP 200 但内容是“首页壳”（网址没变，靠标题识别）—— 即用户看到的“跳回首页”
    - error: 异常（可能网络受限/反爬），需人工判断
    error 可能意味着网络不可达（沙箱环境）或站点反爬，需人工判断。"""
    url = (url or "").strip()
    if not url:
        return "empty", url, ""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": _UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            final = r.geturl()
            code = getattr(r, "status", 200)
            if code >= 400:
                return "dead", final, ""
            if is_homepage(final) and not is_homepage(url):
                return "jump_home", final, ""
            # 内容体检：识别“首页壳”假正常
            text = r.read().decode("utf-8", "ignore")
            title = _get_title(text)
            if is_homepage_shell(title, text):
                return "homepage", final, title
            return "ok", final, title
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "dead", url, ""
        return "error", url, ""  # 403 等反爬，标记 error 由人判断
    except Exception:
        return "error", url, ""


_SITE_SEARCH = [
    ("中国人大网", "https://www.npc.gov.cn/npc/c2/huiyi/search?keyword="),
    ("中国政府网", "https://www.gov.cn/zhengce/advanced_search?q="),
    ("国家网信办", "https://www.cac.gov.cn/search.htm?keyword="),
    ("国家互联网信息办公室", "https://www.cac.gov.cn/search.htm?keyword="),
    ("工信部", "https://www.miit.gov.cn/search?q="),
    ("工业和信息化部", "https://www.miit.gov.cn/search?q="),
    ("国家标准委", "https://std.samr.gov.cn/search?q="),
    ("国家标准化管理委员会", "https://std.samr.gov.cn/search?q="),
    ("生态环境部", "https://www.mee.gov.cn/search?q="),
    ("应急管理部", "https://www.mem.gov.cn/search?q="),
    ("国务院", "https://www.gov.cn/zhengce/advanced_search?q="),
    ("商务部", "https://www.gov.cn/zhengce/advanced_search?q="),
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
    counts = {"ok": 0, "dead": 0, "jump_home": 0, "homepage": 0, "error": 0, "empty": 0}
    total = sum(len(cat.get("laws", [])) for cat in data.get("categories", []))
    done = 0
    for cat in data.get("categories", []):
        cname = cat.get("name", cat.get("id", ""))
        for law in cat.get("laws", []):
            done += 1
            url = (law.get("sourceUrl") or "").strip()
            name = law.get("name", "")
            source = law.get("source", "")
            if not url:
                counts["empty"] += 1
                results.append({"category": cname, "name": name, "source": source,
                                "sourceUrl": "", "status": "empty",
                                "finalUrl": "", "title": "", "suggestion": ""})
                continue
            status, final, title = _probe(url)
            counts[status] = counts.get(status, 0) + 1
            sug = ""
            if status in ("dead", "jump_home", "homepage"):
                sug = build_fallback_url(source, name)
            results.append({"category": cname, "name": name, "source": source,
                            "sourceUrl": url, "status": status,
                            "finalUrl": final, "title": title, "suggestion": sug})
            print(f"  [{done}/{total}] {status:8s} {name[:24]}", flush=True)

    report = {"total": len(results), "counts": counts, "links": results}
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    bad = counts["dead"] + counts["jump_home"] + counts["homepage"]
    print(f"共检查链接 {len(results)} 条：")
    print(f"  ✅ 正常: {counts['ok']}")
    print(f"  ❌ 404 失效: {counts['dead']}")
    print(f"  ⚠️ 跳回首页(网址跳转): {counts['jump_home']}")
    print(f"  ⚠️ 首页壳假正常(同网址吐首页): {counts['homepage']}")
    print(f"  ⚠️ 访问异常(error，可能网络受限或反爬): {counts['error']}")
    print(f"  ➖ 无链接: {counts['empty']}")
    print(f"需关注的失效/跳首页链接共 {bad} 条，已写入 {REPORT_PATH}")
    if counts["error"] and counts["error"] >= len(results) * 0.5:
        print("\n提示：error 占比很高，可能是当前网络环境无法访问政府网站（如沙箱限制），"
              "建议在能联网的本机运行本脚本。")


if __name__ == "__main__":
    main()
