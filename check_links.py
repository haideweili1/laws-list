#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存量法规/标准链接一次性体检脚本（独立工具，不依赖 zhipuai）
========================================================
- 扫描 data.json 中 laws + standards 两张表的 link 字段，逐个 HTTP 探活（跟随重定向）
- 判定每条链接：✅ 正常 / ❌ 失效(>=400或404) / ⚠️ 跳回首页(网址变了) / ⚠️ 首页壳假正常(同网址吐首页) / ⚠️ 访问异常(网络/反爬)
- 产出 link-report.json（机器可读）+ link-report.md（给人审阅），不修改 data.json

用法：
  python check_links.py            # 本机/CI 跑全部 553 条
  python check_links.py --quick 20 # 只抽前 20 条试跑（调试用）

设计：仅一次性探活，不增加日常消耗；符合“免费 + 低资源”原则。
"""
import os
import re
import json
import sys
import time
import argparse
import urllib.request
import urllib.parse
import ssl

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data.json")
REPORT_JSON = os.path.join(ROOT, "link-report.json")
REPORT_MD = os.path.join(ROOT, "link-report.md")

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
    """首页壳检测：返回 200 但内容其实是官网首页/通用页（旧法律迁走后同网址吐出
    “中国人大网”首页标题、无具体法规正文）。urllib 看不到跳转，靠标题识别。"""
    norm = _norm_title(title)
    if not norm:
        return True
    if norm.lower() in _GENERIC_TITLES:
        return True
    return False


def _probe(url, timeout=8):
    """返回 (status, final_url, title)。status: ok / dead / jump_home / homepage / error / empty。

    判定口径（尽量保守，避免把"反爬拦截"误报成"链接失效"）：
      - dead : HTTP 404/410，或 DNS 解析失败 / 连接被拒（域名确实不可达）
      - error: HTTP 401/403/429/5xx（政府网站反爬或限流，沙箱被拦，状态未知，需本机复测）
               或 超时 / SSL 错误（可能为网络抖动）
      - ok / jump_home / homepage : 正常 / 跳回首页 / 首页壳假正常
    """
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
            if code in (404, 410):
                return "dead", final, ""
            if code >= 400:
                # 403/401/429/5xx 等：保守视为"访问异常"，不判死
                return "error", final, ""
            if is_homepage(final) and not is_homepage(url):
                return "jump_home", final, ""
            text = r.read().decode("utf-8", "ignore")
            title = _get_title(text)
            if is_homepage_shell(title, text):
                return "homepage", final, title
            return "ok", final, title
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return "dead", url, ""
        return "error", url, ""  # 403/401/429/5xx 反爬/限流，状态未知
    except urllib.error.URLError as e:
        # 域名无法解析 / 连接被拒 = 真失效；超时/SSL = 网络抖动，归 error
        msg = str(getattr(e, "reason", e)).lower()
        if any(k in msg for k in ("name or service not known", "getaddrinfo", "connection refused", "failed to resolve")):
            return "dead", url, ""
        return "error", url, ""
    except Exception:
        return "error", url, ""


# 来源(发布部门/发布单位) -> 该站站内搜索前缀（均经沙箱实测返回 200 可用）。
# 已弃用的失效端点：gov.cn/zhengce/advanced_search、std.samr.gov.cn/search、cac.gov.cn/search.htm（实测 404）。
# 人大网/海关/商务部搜索沙箱不可达，统一用 "BAIDU" 标记回退百度（用户浏览器可正常搜到正文）。
_SITE_SEARCH = [
    ("人大", "BAIDU"),
    ("国务院", "https://www.gov.cn/search?q="),
    ("政府", "https://www.gov.cn/search?q="),
    ("网信", "BAIDU"),
    ("互联网信息", "BAIDU"),
    ("市场监督", "https://www.samr.gov.cn/search?q="),   # 用 www 而非 std 子域(std 实测404)
    ("标准化", "https://www.samr.gov.cn/search?q="),
    ("工业和信息化", "https://www.miit.gov.cn/search?q="),
    ("工信部", "https://www.miit.gov.cn/search?q="),
    ("生态环境", "https://www.mee.gov.cn/search?q="),
    ("海关", "BAIDU"),
    ("商务", "BAIDU"),
    ("应急", "https://www.mem.gov.cn/search?q="),
    ("公安", "https://www.mps.gov.cn/search?q="),
    ("ISO", "https://www.iso.org/search.html?q="),
    ("欧盟", "BAIDU"),
    ("欧洲", "BAIDU"),
]


def build_fallback_url(source, name):
    name = (name or "").strip()
    if not name:
        return ""
    for key, base in _SITE_SEARCH:
        if key in (source or ""):
            if base == "BAIDU":
                return "https://www.baidu.com/s?wd=" + urllib.parse.quote(name + " 正文")
            return base + urllib.parse.quote(name)
    return "https://www.baidu.com/s?wd=" + urllib.parse.quote(name + " 正文")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", type=int, default=0, help="只探活前 N 条（调试）")
    args = ap.parse_args()

    if not os.path.exists(DATA_PATH):
        print(f"未找到 {DATA_PATH}")
        sys.exit(1)
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    targets = []
    for it in data.get("laws", []):
        targets.append(("法规", it, it.get("dept", "")))
    for it in data.get("standards", []):
        targets.append(("标准", it, it.get("publisher", "")))

    if args.quick:
        targets = targets[: args.quick]

    results = []
    counts = {"ok": 0, "dead": 0, "jump_home": 0, "homepage": 0, "error": 0, "empty": 0}
    total = len(targets)
    done = 0
    for table, it, source in targets:
        done += 1
        name = it.get("name", "")
        url = (it.get("link") or "").strip()
        if not url:
            counts["empty"] += 1
            results.append({"table": table, "name": name, "source": source,
                            "link": "", "status": "empty",
                            "finalUrl": "", "title": "", "suggestion": ""})
            continue
        status, final, title = _probe(url)
        counts[status] = counts.get(status, 0) + 1
        sug = ""
        if status in ("dead", "jump_home", "homepage"):
            sug = build_fallback_url(source, name)
        results.append({"table": table, "name": name, "source": source,
                        "link": url, "status": status,
                        "finalUrl": final, "title": title, "suggestion": sug})
        flag = {"ok": "✅", "dead": "❌", "jump_home": "↪️", "homepage": "🏠", "error": "⚠️", "empty": "➖"}.get(status, "?")
        print(f"  [{done}/{total}] {flag}{status:8s} [{table}] {name[:22]}", flush=True)

    report = {"total": len(results), "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
              "counts": counts, "links": results}
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 生成 Markdown 给人审阅
    bad = [r for r in results if r["status"] in ("dead", "jump_home", "homepage")]
    lines = []
    lines.append(f"# 法律法规 / 产品标准 链接体检报告")
    lines.append("")
    lines.append(f"- 生成时间：{report['generatedAt']}")
    lines.append(f"- 检查总数：**{total}** 条（法规 + 标准）")
    lines.append(f"- ✅ 正常：{counts['ok']} ｜ ❌ 失效：{counts['dead']} ｜ ↪️ 跳回首页：{counts['jump_home']} ｜ 🏠 首页壳假正常：{counts['homepage']} ｜ ⚠️ 访问异常：{counts['error']} ｜ ➖ 无链接：{counts['empty']}")
    lines.append(f"- **需关注的失效/跳首页链接共 {len(bad)} 条**")
    if counts["error"] and counts["error"] >= total * 0.5:
        lines.append("")
        lines.append("> ⚠️ 提示：访问异常(error)占比较高，可能是当前网络环境无法访问政府网站（如沙箱限制/反爬），"
                     "这部分结果仅供参考，建议在能正常联网的本机重跑本脚本以确认。")
    lines.append("")
    lines.append("## 需处理清单（按状态分组）")
    lines.append("")
    for st, label in [("dead", "❌ 失效(404/>=400)"), ("jump_home", "↪️ 跳回首页(网址变了)"),
                      ("homepage", "🏠 首页壳假正常(同网址吐首页)")]:
        grp = [r for r in results if r["status"] == st]
        if not grp:
            continue
        lines.append(f"### {label} — {len(grp)} 条")
        lines.append("")
        lines.append("| 类型 | 名称 | 来源 | 当前链接 | 建议去处 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in grp:
            link = r["link"] or "（无）"
            sug = r["suggestion"] or "—"
            # Markdown 里长链接截断展示，避免表格撑爆
            link_disp = link if len(link) <= 60 else link[:57] + "..."
            sug_disp = sug if len(sug) <= 60 else sug[:57] + "..."
            lines.append(f"| {r['table']} | {r['name']} | {r['source'] or '—'} | {link_disp} | {sug_disp} |")
        lines.append("")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n共检查链接 {len(results)} 条：")
    print(f"  ✅ 正常: {counts['ok']}")
    print(f"  ❌ 失效: {counts['dead']}")
    print(f"  ↪️ 跳回首页: {counts['jump_home']}")
    print(f"  🏠 首页壳假正常: {counts['homepage']}")
    print(f"  ⚠️ 访问异常(可能网络受限或反爬): {counts['error']}")
    print(f"  ➖ 无链接: {counts['empty']}")
    print(f"需关注的失效/跳首页链接共 {len(bad)} 条，已写入 {REPORT_JSON} 和 {REPORT_MD}")


if __name__ == "__main__":
    main()
