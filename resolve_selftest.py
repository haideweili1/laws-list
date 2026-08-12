#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地离线自检：验证「链接分诊解析框架」的确定性与安全性（不动线上/不调用 GLM）。
运行：python resolve_selftest.py
说明：本环境 urllib 无法驱动 openstd 的 JS 检索（其搜索结果由前端 XHR 加载），
故 openstd 的"按号查 hcno"需在落地时走国内代理的浏览器能力；但本自检验证：
  (1) 分诊路由正确（reuse / openstd / cfsa / name_query）；
  (2) 详情页核对机制正确（已知 hcno 详情页确含标准号，证明"解析→核对"可靠）；
  (3) 安全性：解析器要么返回经验证的真链接，要么返回空（绝不编造 URL）。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import update_laws_action as M

ok_all = True
def check(name, cond, extra=""):
    global ok_all
    ok_all = ok_all and cond
    print(f"  [{'OK' if cond else 'FAIL'}] {name} {extra}")

print("=== 自检1：分诊路由（按条目类别自动选源，不写死标准号）===")
entry_reuse = {"name": "信息安全技术 网络安全等级保护基本要求",
               "stdNo": "GB/T 22239-2019",
               "link": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BAFB47E8874764186BDB7865E8344DAF"}
r = M.resolve_link_for_entry(entry_reuse, "standards", verify_existing=False)
check("有现有有效链接->reuse", r["method"] == "reuse_existing" and r["link"],
      f"(method={r['method']})")

entry_openstd = {"name": "信息安全技术 网络安全等级保护基本要求", "stdNo": "GB/T 22239-2019", "link": ""}
r = M.resolve_link_for_entry(entry_openstd, "standards", verify_existing=False)
check("有 GB 号无链接->openstd", r["method"] == "openstd", f"(method={r['method']})")

entry_food = {"name": "食品安全国家标准 食品接触用塑料材料及制品", "stdNo": "GB 4806.7-2023", "link": ""}
r = M.resolve_link_for_entry(entry_food, "standards", verify_existing=False)
check("食安国标->cfsa 占位且留空(不编造)", r["method"] == "cfsa" and not r["link"],
      f"(method={r['method']}, link={'空' if not r['link'] else '非空'})")

entry_law = {"name": "某行业安全生产管理办法", "stdNo": "", "link": ""}
r = M.resolve_link_for_entry(entry_law, "laws", verify_existing=False)
check("无号法规->name_query 占位且留空(不编造)", r["method"] == "name_query" and not r["link"],
      f"(method={r['method']}, link={'空' if not r['link'] else '非空'})")

print("\n=== 自检2：详情页核对机制（解析出的 hcno 详情页确含标准号）===")
# 用 data.json 中已知的真实 hcno 直接抓详情页，证明"解析->核对"这一环可靠
for stdno, hcno in [("GB/T 22239-2019", "BAFB47E8874764186BDB7865E8344DAF"),
                    ("GB/T 45654-2025", "F67D3F376E0A0A0FF5317FB36B32A30A")]:
    url = M._OPENSTD_DETAIL + hcno
    txt = M.fetch_text(url, timeout=15)
    norm = re.sub(r"[^A-Z0-9]", "", stdno.upper())
    hit = bool(txt) and norm in re.sub(r"[^A-Z0-9]", "", txt.upper())
    check(f"详情页含 {stdno}", hit, f"(len={len(txt) if txt else 0})")

print("\n=== 自检3：解析闭环（模拟检索结果+真实详情页核对，验证 搜索→hcno→核对 逻辑）===")
# 本环境 urllib 无法驱动 openstd 的 JS 检索（搜索结果由前端 XHR 加载），
# 故这里用"包含真实 hcno 的模拟检索页"喂给解析器，验证其后半段（取 hcno→抓真实详情页→核对标准号）逻辑。
# 详情页是真实从官网抓的，确保核对环节不是空谈。
fake_results = {
    "GB/T 22239-2019": "BAFB47E8874764186BDB7865E8344DAF",
    "GB/T 45654-2025": "F67D3F376E0A0A0FF5317FB36B32A30A",
}
orig_search = M._openstd_search_session
def fake_search(q):
    qn = re.sub(r"[^A-Z0-9]", "", q.upper())
    for stdno, hcno in fake_results.items():
        if qn and qn in re.sub(r"[^A-Z0-9]", "", stdno.upper()):
            return "<script>showInfo('%s')</script>" % hcno
    return "<html>无结果</html>"
M._openstd_search_session = fake_search
try:
    for stdno, hcno in fake_results.items():
        r = M.resolve_openstd(stdno)
        safe = (r["verified"] and r["hcno"].upper() == hcno.upper()) or (not r["link"])
        check(f"resolve_openstd({stdno}) 解析出正确 hcno 并核对通过",
              r["verified"] and r["hcno"].upper() == hcno.upper(),
              f"(hcno={r['hcno']}, verified={r['verified']})")
finally:
    M._openstd_search_session = orig_search
print("  （注：落地时'模拟检索'替换为国内代理的浏览器检索即可；解析后的详情页核对复用本已验证的官网抓取）")

print("\n=== 自检完成 ===", "全部通过" if ok_all else "存在失败项")
sys.exit(0 if ok_all else 1)
