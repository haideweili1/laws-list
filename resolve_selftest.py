import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_laws_action as M

ok = True
def check(name, cond, extra=""):
    global ok
    ok = ok and cond
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ("" if not extra else "  " + extra))

print("=== 自检1：分诊路由不编造、按类别分流 ===")
# 有有效链接 -> reuse（用真实已知 hcno 链接测试）
e1 = {"name": "等级保护", "link": "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BAFB47E8874764186BDB7865E8344DAF", "stdNo": "GB/T 22239-2019"}
r1 = M.resolve_link_for_entry(e1, "standards")
check("有链接 -> reuse 且链接原样", r1.get("method") == "reuse_existing" and r1.get("link"), f"({r1.get('method')})")
# 有号 GB -> openstd
e2 = {"name": "等级保护", "link": "", "stdNo": "GB/T 22239-2019"}
r2 = M.resolve_link_for_entry(e2, "standards")
check("有 GB 号 -> openstd 分支", r2.get("method") == "openstd", f"({r2.get('method')})")
# 食安 GB 4806 -> cfsa
e3 = {"name": "食品接触", "link": "", "stdNo": "GB 4806.7-2023"}
r3 = M.resolve_link_for_entry(e3, "standards")
check("食安 GB4806 -> cfsa 分支", r3.get("method") == "cfsa", f"({r3.get('method')})")
# 无号法规 -> name_query
e4 = {"name": "XX安全管理办法", "link": "", "stdNo": ""}
r4 = M.resolve_link_for_entry(e4, "laws")
check("无号法规 -> name_query 分支", r4.get("method") == "name_query", f"({r4.get('method')})")
# 所有分支要么有链接、要么留空，绝不编造
all_safe = all((rr.get("link") == "" or rr.get("link", "").startswith("http")) for rr in [r1, r2, r3, r4])
check("所有分支不编造 URL（空或 http 开头）", all_safe)

print("\n=== 自检2：详情页核对机制（已知 hcno 详情页确含标准号）===")
for stdno, hcno in [("GB/T 22239-2019", "BAFB47E8874764186BDB7865E8344DAF"),
                    ("GB/T 45654-2025", "F67D3F376E0A0A0FF5317FB36B32A30A")]:
    text = M.fetch_text(M._OPENSTD_DETAIL + hcno, timeout=15)
    norm = re.sub(r"[^A-Z0-9]", "", stdno.upper())
    has = bool(text) and norm in re.sub(r"[^A-Z0-9]", "", text.upper())
    check(f"详情页核对 {stdno}", has, f"(len={len(text) if text else 0})")

print("\n=== 自检3：真实端到端 openstd 解析（搜索->hcno->核对）===")
for stdno in ["GB/T 22239-2019", "GB/T 45654-2025"]:
    r = M.resolve_openstd(stdno)
    check(f"resolve_openstd({stdno}) 解析出真链接并校验",
          r["verified"] and r["hcno"],
          f"(verified={r['verified']}, hcno={r['hcno'][:8]}..., reason={r['reason']})")

print("\n结果:", "ALL PASS ✅" if ok else "SOME FAIL ❌")
sys.exit(0 if ok else 1)
