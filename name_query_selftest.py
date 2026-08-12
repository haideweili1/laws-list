# -*- coding: utf-8 -*-
"""name_query 离线自测（不联网）：用模拟搜索验证逻辑与审计强制重解析。"""
import importlib.util

spec = importlib.util.spec_from_file_location("ula", "update_laws_action.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

passed = 0


def check(cond, msg):
    global passed
    assert cond, "FAIL: " + msg
    passed += 1
    print("  PASS:", msg)


# 注：自测环境未设 SYNC_PROXY，故桩打在本地回退 _bing_site_search 上（生产走代理 /search-site）。
# 备 1：全国人大常委会的法，搜索命中 npc.gov.cn 且标题含法规名 -> 返回链接
m._bing_site_search = lambda domain, query, timeout=12: [
    {"title": "中华人民共和国招标投标法", "url": "https://www.npc.gov.cn/fl/1999/legal_123.html"}]
r = m.name_query({"name": "中华人民共和国招标投标法", "dept": "全国人大常委会", "link": ""}, "laws")
check(r["verified"] and "npc.gov.cn" in r["link"], "命中 npc.gov.cn 且 verified")


# 备 2：搜索结果域名不匹配官方站 -> 拒绝，留空（绝不采用）
m._bing_site_search = lambda domain, query, timeout=12: [
    {"title": "招标投标法", "url": "https://www.example.com/xxx"}]
r2 = m.name_query({"name": "中华人民共和国招标投标法", "dept": "全国人大常委会", "link": ""}, "laws")
check((not r2["verified"]) and r2["link"] == "", "域名不匹配官方站 -> 拒绝留空")


# 备 3：清单未出现的归口 -> 留空待补（绝不编造）
r3 = m.name_query({"name": "某新规", "dept": "未知部门XYZ", "link": ""}, "laws")
check((not r3["verified"]) and "留空待补" in r3["reason"], "未知归口 -> 留空待补")


# 备 4：应急管理部的法（对应审计非 GB 项），搜索命中 mem.gov.cn 且标题含法规名
m._bing_site_search = lambda domain, query, timeout=12: [
    {"title": "中华人民共和国安全生产法", "url": "https://www.mem.gov.cn/fws/fl/2021/axiaofa.html"}]
r4 = m.name_query({"name": "中华人民共和国安全生产法", "dept": "应急管理部", "link": ""}, "laws")
check(r4["verified"] and "mem.gov.cn" in r4["link"], "命中 mem.gov.cn 且 verified（审计非GB路径）")


# 备 5：_official_domains_for 覆盖 6 条非 GB 审计项的归口
for dept, dom in [("全国人大常委会", "npc.gov.cn"), ("国务院", "gov.cn"), ("应急管理部", "mem.gov.cn")]:
    doms = m._official_domains_for({"dept": dept}, "laws")
    check(doms and doms[0] == dom, "归口映射 %s -> %s" % (dept, dom))


# 备 6：_source_kind 对无号无法规 -> name_query
kind = m._source_kind({"name": "宪法", "link": ""}, "laws")
check(kind == "name_query", "_source_kind 无号无法规 -> name_query")


# 备 7：审计专项强制重解析（修掉“审计项仍走 reuse”的 bug）
called = {}


def fake_name_query(entry, table, max_results=6):
    called["entry"] = entry
    return {"link": "https://www.npc.gov.cn/x", "method": "name_query", "verified": True, "reason": "test"}


m.name_query = fake_name_query
m.load_link_audit_task()
target = {"id": "L0062", "name": "中华人民共和国招标投标法",
          "link": "https://www.beijing.gov.cn/wrong.pdf", "dept": "全国人大常委会"}
res = m.resolve_source_url_for_change("laws", {"name": "中华人民共和国招标投标法", "action": "update"}, target)
check(called.get("entry") is not None, "审计目标走到 name_query（未停留在 reuse）")
check(called["entry"].get("link") == "", "审计目标 entry.link 被强制清空")
check(res.get("method") == "name_query" and res.get("verified"), "审计目标解析结果来自 name_query")

print("\nname_query 自测通过 %d 项" % passed)
