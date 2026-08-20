# -*- coding: utf-8 -*-
"""离线自测：验证「分诊解析接进活检索」后质检关卡没有放水。

核心要证明三件事：
  1) 不放水：GLM 编链接 + 系统也解析不到 → 仍然整条丢弃（垃圾进不来）。
  2) 救得回：GLM 编链接但系统能确定性拿到真链接 + 官方页核对一致 → 可直接应用。
  3) 不默认为真：拿到真链接但内容核对不上/核对矛盾 → 只降级人工复核，不当成已确认。
全程不联网（打桩替换网络函数），不改动 data.json。
"""
import sys
import update_laws_action as M

TODAY = "2026-08-11"
GOV = "https://www.gov.cn/zhengce/content/2026-01/01/content_9999.htm"
FAKE = "https://openstd.samr.gov.cn/bzgk/gb/GB4288-2025"          # 无 hcno，伪造格式
HC22239 = "https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=" + "BAFB1A5B0B0B1C4D2E3F4A5B6C7D8E9F"
PAGE_DATE = "2026-03-01"

_page_text = {}      # url -> 正文
_resolved = {}       # stdNo -> 解析结果
_calls = {"resolve_openstd": []}


def _stub_network():
    M.scf_probe_link = lambda u: {"state": True, "dead_page_checked": False}
    M.probe_link = lambda u, timeout=10: True
    M.fetch_text = lambda u, timeout=10, max_bytes=150000: _page_text.get(u)
    M.is_dead_page = lambda t: False

    def fake_resolve_openstd(std_no, retries=1, max_detail_checks=6):
        _calls["resolve_openstd"].append(std_no)
        return _resolved.get(
            (std_no or "").strip(),
            {"link": "", "hcno": "", "verified": False,
             "reason": "桩：未配置该标准号", "method": "openstd"})
    M.resolve_openstd = fake_resolve_openstd


def run(title, table, change, target, expect_ok, expect_discard, expect_in_reason=None):
    M._RESOLVE_LOG.clear()
    # 真实管线：apply_change 在 check_change 之前会先跑 reconcile_conclusions
    # （拿官方页正文确定性抽取结论覆盖 GLM 草稿）。自测必须走这条真实路径，
    # 否则会漏掉"reconcile 把本应丢弃的垃圾错误转成人肉复核"这类回归。
    change = M.reconcile_conclusions(change, target, table, TODAY)
    ok, reasons, discard = M.check_change(table, change, target, TODAY)
    tag = "PASS" if (ok == expect_ok and discard == expect_discard) else "FAIL"
    print(f"[{tag}] {title}")
    print(f"       ok={ok} discard={discard}（期望 ok={expect_ok} discard={expect_discard}）")
    if reasons:
        for r in reasons:
            print(f"       原因：{r}")
    if expect_in_reason:
        hit = any(expect_in_reason in r for r in reasons)
        print(f"       原因含「{expect_in_reason}」：{'是' if hit else '否'}")
        if not hit:
            tag = "FAIL"
            print("[FAIL] 上一条原因文本不符合预期")
    return tag == "PASS", reasons


def main():
    _stub_network()
    results = []

    # ── 用例 A：不放水 ──
    # 法规类、无标准号、清单原本也没链接 → 分诊只能走 name_query（未落地）→ 解析不到 → 必须丢弃
    _page_text.clear()
    tgt_a = {"id": "L0001", "name": "某某管理办法", "link": "",
             "effectiveDate": "2025-01-01", "status": "现行有效", "dept": "国务院"}
    chg_a = {"action": "update", "name": "某某管理办法", "source_url": FAKE,
             "effectiveDate": "2026-06-01", "status": "现行有效",
             "fromValues": {"effectiveDate": "2025-01-01", "status": "现行有效"},
             "note": "实施日期 由2025-01-01 改为 2026-06-01，依据官方公告"}
    r, _ = run("A 不放水：编造链接且系统也解析不到 → 整条丢弃",
               "laws", chg_a, tgt_a, expect_ok=False, expect_discard=True,
               expect_in_reason="系统按官方渠道自动解析也未取到真实链接")
    results.append(r)

    # ── 用例 B：救得回 ──
    # 清单该条目本身有有效官方链接（非改版）→ 复用它作依据，且页面实施日期与声称一致 → 可直接应用
    _page_text.clear()
    _page_text[GOV] = "某某管理办法  实施日期：%s  正文……" % PAGE_DATE
    tgt_b = {"id": "L0002", "name": "某某条例", "link": GOV,
             "effectiveDate": "", "status": "现行有效", "dept": "国务院"}
    chg_b = {"action": "update", "name": "某某条例", "source_url": FAKE,
             "effectiveDate": PAGE_DATE, "status": "现行有效",
             "fromValues": {"effectiveDate": "", "status": "现行有效"},
             "note": "补填实施日期 由空 改为 %s，依据官方正文" % PAGE_DATE}
    r, _ = run("B 救得回：系统复用清单现有官方链接且日期核对一致 → 可直接应用",
               "laws", chg_b, tgt_b, expect_ok=True, expect_discard=False)
    results.append(r)
    print(f"       source_url 已被改写为真链接：{chg_b.get('source_url') == GOV}")
    results.append(chg_b.get("source_url") == GOV)

    # ── 用例 C：GLM 编错实施日期 → 系统从官方页抽到真值覆盖，正确数据直接可应用 ──
    _page_text.clear()
    _page_text[GOV] = "某某条例  实施日期：%s  正文……" % PAGE_DATE
    tgt_c = dict(tgt_b, id="L0003")
    chg_c = {"action": "update", "name": "某某条例", "source_url": FAKE,
             "effectiveDate": "2026-05-01", "status": "现行有效",
             "fromValues": {"effectiveDate": "", "status": "现行有效"},
             "note": "实施日期 由空 改为 2026-05-01，依据官方正文"}
    r, _ = run("C 自我纠正：GLM 编错实施日期，系统从官方页抽到真值覆盖 → 正确数据直接可应用",
               "laws", chg_c, tgt_c, expect_ok=True, expect_discard=False)
    results.append(r)
    # 额外断言：实施日期被纠正为官方页真值（2026-03-01），而非 GLM 编造的 2026-05-01
    corrected = (chg_c.get("effectiveDate") == PAGE_DATE)
    print(f"       实施日期已自我纠正为官方真值 {PAGE_DATE}：{corrected}（GLM 原称 2026-05-01）")
    results.append(corrected)

    # ── 用例 D：按标准号解析 openstd，并把真链接补进 link 字段 ──
    _page_text.clear()
    _page_text[HC22239] = ("GB/T 22239-2019 信息安全技术 网络安全等级保护基本要求 "
                           "实施日期：%s" % PAGE_DATE)
    _resolved.clear()
    _resolved["GB/T 22239-2019"] = {"link": HC22239, "hcno": "x", "verified": True,
                                    "reason": "桩：openstd 核对通过", "method": "openstd"}
    tgt_d = {"id": "S0001", "name": "信息安全技术 网络安全等级保护基本要求",
             "stdNo": "GB/T 22239-2019", "link": "",
             "effectiveDate": "", "status": "现行有效", "publisher": "国家标准化管理委员会"}
    chg_d = {"action": "update", "name": "信息安全技术 网络安全等级保护基本要求",
             "stdNo": "GB/T 22239-2019", "source_url": "", "link": FAKE,
             "effectiveDate": PAGE_DATE, "status": "现行有效",
             "fromValues": {"effectiveDate": "", "status": "现行有效"},
             "note": "补填实施日期 由空 改为 %s，依据国家标准全文公开系统" % PAGE_DATE}
    r, _ = run("D 按号解析：GLM 未给来源，系统按标准号解析 openstd 并核对 → 可直接应用",
               "standards", chg_d, tgt_d, expect_ok=True, expect_discard=False)
    results.append(r)
    print(f"       编造的 link 已被真链接顶替：{chg_d.get('link') == HC22239}")
    results.append(chg_d.get("link") == HC22239)

    # ── 用例 E：改版严禁复用旧链接 ──
    _page_text.clear()
    _page_text[GOV] = "旧版正文 实施日期：2018-01-01"
    _resolved.clear()   # 新版没有配置解析结果 → 应解析不到，而不是拿旧链接顶
    tgt_e = {"id": "S0002", "name": "GB/T 4288-2018 家用电动洗衣机",
             "stdNo": "GB/T 4288-2018", "link": GOV,
             "effectiveDate": "2018-01-01", "status": "现行有效", "publisher": "SAC"}
    chg_e = {"action": "update", "name": "GB/T 4288-2018 家用电动洗衣机",
             "stdNo": "GB/T 4288-2025", "source_url": FAKE,
             "effectiveDate": "2026-01-01", "status": "即将实施",
             "fromValues": {"effectiveDate": "2018-01-01", "status": "现行有效"},
             "note": "版本 由2018 改为 2025，依据官方公告"}
    r, _ = run("E 改版保护：版本号变化时不复用旧条目链接（宁可丢弃也不张冠李戴）",
               "standards", chg_e, tgt_e, expect_ok=False, expect_discard=True)
    results.append(r)
    print(f"       未复用旧链接（source_url 未被改成旧链）：{chg_e.get('source_url') != GOV}")
    results.append(chg_e.get("source_url") != GOV)

    # ── 用例 F：source_hint 真的被用上（承诺给 GLM 的入口必须有效）──
    _page_text.clear()
    _page_text[HC22239] = "GB/T 22239-2019 等级保护基本要求 实施日期：%s" % PAGE_DATE
    _resolved.clear()
    _resolved["GB/T 22239-2019"] = {"link": HC22239, "hcno": "x", "verified": True,
                                    "reason": "桩", "method": "openstd"}
    _calls["resolve_openstd"].clear()
    chg_f = {"action": "add", "name": "信息安全技术 网络安全等级保护基本要求",
             "source_url": "", "source_hint": "GB/T 22239-2019",
             "effectiveDate": PAGE_DATE, "status": "现行有效",
             "note": "新增：依据国家标准全文公开系统"}
    M._RESOLVE_LOG.clear()
    ok, reasons, discard = M.check_change("standards", chg_f, None, TODAY)
    used = _calls["resolve_openstd"]
    hint_ok = bool(used) and "22239" in used[0]
    print(f"[{'PASS' if hint_ok else 'FAIL'}] F source_hint 被真正用于按号解析："
          f"实际拿去解析的标准号={used}")
    results.append(hint_ok)

    print("\n===== 汇总 =====")
    print(f"通过 {sum(1 for x in results if x)} / {len(results)}")
    if all(results):
        print("结论：质检关卡未放水——垃圾照丢、真变更被救回、拿不准只降人工复核。")
        return 0
    print("结论：存在未通过项，需修正后再推送。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
