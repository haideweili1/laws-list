#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存量坏链"逐个替换"脚本（配合 check_links.py 使用）
==================================================
- 读 link-report.json，把 status 为 dead / jump_home / homepage 的条目，
  将其 sourceUrl 替换为报告里的 suggestion（回退链接）。
- 输出 laws_fixed.json（**不覆盖原 laws.json**，供你逐条审阅后再决定替换）。
- 控制台逐条打印"旧链 -> 新链"，满足"逐个看"的需求。
- status 为 error 的（访问异常，可能误判）不自动改，仅提示人工复核。

用法（本机）：
  1) python check_links.py      # 先生成 link-report.json
  2) python fix_links.py        # 再生成 laws_fixed.json + 打印替换清单
  3) 审阅 laws_fixed.json，确认无误后把它的内容覆盖 laws.json，用 GitHub Desktop 推送
     （仅改数据文件，不需要 workflow 权限）
"""
import os
import json
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LAWS_PATH = os.path.join(ROOT, "laws.json")
REPORT_PATH = os.path.join(ROOT, "link-report.json")
FIXED_PATH = os.path.join(ROOT, "laws_fixed.json")


def main():
    if not os.path.exists(REPORT_PATH):
        print(f"未找到 {REPORT_PATH}，请先运行 check_links.py 生成报告")
        sys.exit(1)
    if not os.path.exists(LAWS_PATH):
        print(f"未找到 {LAWS_PATH}")
        sys.exit(1)

    with open(REPORT_PATH, encoding="utf-8") as f:
        report = json.load(f)
    with open(LAWS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # 建索引 (分类名, 法规名) -> law 对象
    index = {}
    for cat in data.get("categories", []):
        cname = cat.get("name", "")
        for law in cat.get("laws", []):
            index[(cname, law.get("name", ""))] = law

    fixed = 0
    skipped_error = 0
    unmatched = 0

    for item in report.get("links", []):
        st = item.get("status")
        sug = (item.get("suggestion") or "").strip()
        if st in ("dead", "jump_home", "homepage") and sug:
            key = (item.get("category", ""), item.get("name", ""))
            law = index.get(key)
            if law is None:
                unmatched += 1
                print(f"  [未匹配，跳过] {item.get('name')}（分类={item.get('category')}）")
                continue
            old = law.get("sourceUrl", "")
            law["sourceUrl"] = sug
            fixed += 1
            print(f"  [替换] {item.get('name')}")
            print(f"       旧: {old}")
            print(f"       新: {sug}")
        elif st == "error":
            skipped_error += 1
            # 访问异常（可能反爬/网络受限），不自动改，列出供人工复核
            print(f"  [人工复核] {item.get('name')} 访问异常(error)，未自动修改")

    with open(FIXED_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n共替换 {fixed} 条坏链 -> 已写入 {FIXED_PATH}")
    if unmatched:
        print(f"（其中 {unmatched} 条因分类/名称未匹配而跳过，可人工核对）")
    if skipped_error:
        print(f"另有 {skipped_error} 条 error（访问异常，可能误判），未自动修改，请人工复核 link-report.json")
    print("\n审阅 laws_fixed.json 后，确认无误可将它覆盖 laws.json 并推送"
          "（仅数据文件，无需 workflow 权限）。")


if __name__ == "__main__":
    main()
