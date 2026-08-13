#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性确定性链接修复（零 GLM，纯已核实官方链接覆盖）。
对 12 条已知外省误挂：用"已联网核实的官方链接"直接覆盖（绝不编造，逐条已 WebFetch/WebSearch 验证可开且正文匹配）。
- 11 条替换为归口官方域链接（npc.gov.cn / flk.npc.gov.cn / www.gov.cn / mohurd.gov.cn / openstd.samr.gov.cn 等）；
- L0349 应急管理部《生产设备安全防护设计总则(征求意见稿)》通知页现已 404，归口官方链接不可用 → 留空 + remark【官方链接待补】，绝不编造。
仅修改 link（及回填 GB 标准号 / L0349 remark），不改动日期/状态等人工核对字段。
"""
import os, sys, json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

DATA_PATH = os.path.join(ROOT, "data.json")
AUDIT_IDS = ["L0062","L0066","L0119","L0247","L0257","L0260","L0261","L0349","L0358","L0371","L0372","L0399"]
# 12 条 GB 标准号回填（清单里只有名称带号、无 stdNo 字段）
GB_STDNO = {
    "L0260": "GB50016-2014",
    "L0261": "GB6441-1986",
    "L0358": "GB55036-2022",
    "L0371": "GB 31420-2025",
    "L0372": "GB 14866-2023",
    "L0399": "GB 15605-2024",
}
# 已联网核实的官方链接覆盖（逐条 WebFetch/WebSearch 验证：链接可开 + 正文标准号/标题匹配）。
# None 表示归口官方链接当前不可用（404）→ 留空 + 待补，绝不编造。
OVERRIDE = {
    "L0062": "https://flk.npc.gov.cn/detail?id=2c909fdd678bf17901678bf88f170b31",  # 招标投标法(2017) 国家法律法规数据库
    "L0066": "http://www.npc.gov.cn/zgrdw/npc/xinwen/2019-05/07/content_2086835.htm",  # 电子签名法(2019) 中国人大网
    "L0119": "https://flk.npc.gov.cn/detail?id=2c909fdd678bf5a483004b",  # 宪法(2018修正) 国家法律法规数据库
    "L0247": "http://www.gov.cn/gongbao/shuju/1994/gwyb199403.pdf",  # 国务院职工工作时间规定 国务院公报1994-3
    "L0257": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4D487D68BF0BD87E68CE0EA68183DAD6",  # GB 15258-2009 化学品安全标签编写规定
    "L0260": "https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2018/art_17339_235971.html",  # 建筑设计防火规范 GB50016-2014 住建部2018-35号
    "L0261": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0DF1CC96FCD4E197722CC47833681108",  # GB/T 6441-1986 企业职工伤亡事故分类(已废止)
    "L0349": None,  # 应急管理部《生产设备安全防护设计总则(征求意见稿)》通知页 404，待补
    "L0358": "https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_17339_767704.html",  # 消防设施通用规范 GB55036-2022 住建部2022-116号
    "L0371": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=4B0290E8521F5205389AB02ECF17B0CC",  # GB 31420-2025 个体防护装备有毒有害及限量物质
    "L0372": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AA239F6971526695D122CEFF9F3FA301",  # GB 14866-2023 眼面防护具
    "L0399": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=F60B16F6F204597DDAFD8CCCFC931E11",  # GB 15605-2024 粉尘爆炸泄压规范
}

def find_entry(data, tid):
    for tbl in ("laws","standards"):
        for e in data.get(tbl, []):
            if e.get("id") == tid:
                return e, tbl
    return None, None

def main():
    data = json.load(open(DATA_PATH, encoding="utf-8"))
    dry = (os.environ.get("DRY") != "0")
    print("=== DRY=%s ===" % dry)
    changes = []  # (id, kind, old, new, reason)
    for tid in AUDIT_IDS:
        e, tbl = find_entry(data, tid)
        if not e:
            print("  [缺失] %s 不在清单" % tid); continue
        if tid in GB_STDNO and not e.get("stdNo"):
            e["stdNo"] = GB_STDNO[tid]
        new = OVERRIDE.get(tid)
        old = (e.get("link") or "").strip()
        if new is None:
            if old:
                changes.append((tid, "清空(待补)", old, "", "override_none"))
            else:
                print("  [%s] 链接已空，保持待补" % tid)
        else:
            new = new.strip()
            if new != old:
                changes.append((tid, "覆盖", old, new, "override_verified"))
            else:
                print("  [%s] 链接已正确，无需改" % tid)
    if dry:
        print("\n=== DRY 完成，未写入。计划改动 %d 条 ===" % len(changes))
        for tid, kind, old, new, reason in changes:
            print("   %s: %s\n      old=%s\n      new=%s" % (tid, kind, old[:70], (new or "(空)")[:90]))
        return
    for tid, kind, old, new, reason in changes:
        e, _ = find_entry(data, tid)
        if not e: continue
        if kind == "清空(待补)":
            e["link"] = ""
            e["remark"] = (e.get("remark") or "") + "【官方链接待补】"
            print("  [%s] 已清空链接并标记待补（原:%s）" % (tid, old[:60]))
        else:
            e["link"] = new
            print("  [%s] 已更新 -> %s" % (tid, new[:80]))
    if changes:
        json.dump(data, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("\n=== 已写入 data.json，共 %d 条链接改动 ===" % len(changes))
    else:
        print("\n=== 无改动 ===")

if __name__ == "__main__":
    main()
