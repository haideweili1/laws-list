# -*- coding: utf-8 -*-
"""存量去重体检（一次性清历史债）+ 安全合并。

通用规则（不点名任何具体条目）：
- 按「归一化名称」找重复：去空格、去书名号《》、引号、全角转半角后相等的，视为同一条法规/标准。
  「X规定」与「《X规定》」归一化后都变成「X规定」→ 判为重复。
- 仅在【同一张表内】合并（laws 与 standards 之间不互并，避免跨表误并）。
- 合并策略：保留「更规范/字段更全」的一条；被删条目的独有字段回填进保留条（不丢信息）。
- 安全网：若两条都有标准号且标准号不同，视为不同标准（同名巧合），跳过不并、仅报告。

用法：
  python3 dedup_scan.py            # DRY：仅报告，不写
  DRY=0 python3 dedup_scan.py      # 应用合并（先自动备份 data.json 为 data.json.dedup_bak）
"""
import os
import sys
import json
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import update_laws_action as M  # 复用 _norm_txt 归一化逻辑

DATA_PATH = os.path.join(ROOT, "data.json")


def _richness(item):
    """条目非空字段数（用于选保留条）。"""
    tbl, e = item
    return sum(1 for k, v in e.items() if v not in (None, "", [], {}))


def _score(item):
    """选保留条的综合打分：字段越全越好；带书名号《》扣分；gateway/big5/镜像等劣质链接重扣。"""
    tbl, e = item
    s = _richness(item)
    if "《" in (e.get("name") or ""):
        s -= 5
    link = (e.get("link") or "").lower()
    if not link.strip():
        s -= 3
    elif "big5" in link or "/gate/" in link or "mirror" in link:
        s -= 10
    return s


def main():
    dry = os.environ.get("DRY", "1") not in ("0", "false", "no")
    data = json.load(open(DATA_PATH, encoding="utf-8"))

    plan = []          # (keep_item, drop_item, note)
    skipped = []       # (item_a, item_b, reason) 同名但疑似不同条目，跳过
    for tbl in ("laws", "standards"):
        by_norm = {}
        for e in data[tbl]:
            n = M._norm_txt(e.get("name"))
            if n:
                by_norm.setdefault(n, []).append((tbl, e))
        for n, group in by_norm.items():
            if len(group) < 2:
                continue
            # 同一归一化名下，按 (stdNo 是否有/是否一致) 分组，避免把两份不同标准误并
            # 选保留条：综合打分（字段全 + 无书名号 + 官方正文链接受青睐；gateway/big5 镜像链接受重罚）
            keep = max(group, key=_score)
            for it in group:
                if it is keep:
                    continue
                ks = (keep[1].get("stdNo") or "").strip()
                ds = (it[1].get("stdNo") or "").strip()
                if ks and ds and ks != ds:
                    skipped.append((keep, it, "两标准号不同(%s≠%s)，疑似不同标准，跳过" % (ks, ds)))
                    continue
                plan.append((keep, it, n))

    print("===== 存量去重体检 =====")
    print("扫描：laws=%d  standards=%d" % (len(data["laws"]), len(data["standards"])))
    print("命中重复对：%d 对；疑似但跳过：%d 对" % (len(plan), len(skipped)))

    if skipped:
        print("\n----- 疑似同名但跳过（人工确认）-----")
        for keep, it, reason in skipped:
            print("  《%s》 保留=%s(%s)  跳过=%s(%s)  %s" % (
                M._norm_txt(keep[1].get("name")), keep[1].get("id"), keep[1].get("name"),
                it[1].get("id"), it[1].get("name"), reason))

    if not plan:
        print("\n未发现需合并的重复条目。")
        return 0

    print("\n----- 待合并重复对 -----")
    for keep, it, n in plan:
        backfill = [k for k in it[1] if it[1].get(k) not in (None, "", [], {})
                    and keep[1].get(k) in (None, "", [], {})]
        print("组《%s》:" % n)
        print("  保留 id=%s 名=%r 字段数=%d" % (keep[1].get("id"), keep[1].get("name"), _richness(keep)))
        print("  删除 id=%s 名=%r 字段数=%d" % (it[1].get("id"), it[1].get("name"), _richness(it)))
        if backfill:
            print("    → 删除条独有字段回填进保留条：%s" % backfill)

    if dry:
        print("\n=== DRY 模式：未写入。确认无误后执行 DRY=0 python3 dedup_scan.py 应用合并 ===")
        return 0

    # 应用：先备份
    bak = DATA_PATH + ".dedup_bak"
    if not os.path.exists(bak):
        shutil.copy(DATA_PATH, bak)
    print("\n备份：%s" % bak)

    drop_ids = set()
    for keep, it, n in plan:
        ktbl, ke = keep
        dtbl, de = it
        for k in list(de.keys()):
            if de.get(k) not in (None, "", [], {}) and ke.get(k) in (None, "", [], {}):
                ke[k] = de[k]
        drop_ids.add((dtbl, de.get("id")))

    for tbl in ("laws", "standards"):
        data[tbl] = [e for e in data[tbl] if (tbl, e.get("id")) not in drop_ids]

    json.dump(data, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n=== 已合并 %d 条重复，写入 data.json（laws=%d standards=%d）===" % (
        len(drop_ids), len(data["laws"]), len(data["standards"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
