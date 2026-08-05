#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建脚本：把大 data.json 拆成多个小分片 + 精简 index.html（去掉 690KB 内联数据，改为分块加载）
目的：避免 GitHub Pages 对大文件（>~300KB）在国内节点被截断导致网页空白。
用法：python build_site.py
"""
import json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
DATA_DIR = os.path.join(ROOT, "data")
INDEX = os.path.join(ROOT, "index.html")

# 每个分片目标大小（字节）。45KB，远低于 GitHub Pages 截断阈值，留足安全余量。
TARGET = 45000

def main():
    d = json.load(open(DATA_JSON, encoding="utf-8"))
    laws = d.get("laws", [])
    stds = d.get("standards", [])
    last_updated = d.get("lastUpdated", "")
    print("源数据: laws=%d standards=%d" % (len(laws), len(stds)))

    # 合并成带类型标记的序列，按字节大小切分
    seq = [{"t": "laws", "v": r} for r in laws] + [{"t": "standards", "v": r} for r in stds]
    chunks = []
    cur = []
    cur_size = 0
    for r in seq:
        s = len(json.dumps(r, ensure_ascii=False))
        if cur and cur_size + s > TARGET:
            chunks.append(cur)
            cur = []
            cur_size = 0
        cur.append(r)
        cur_size += s
    if cur:
        chunks.append(cur)

    # 写出分片 + 清单
    os.makedirs(DATA_DIR, exist_ok=True)
    # 清理旧分片（沙箱回收站不可用时忽略，残留文件不会被 manifest 引用，无害）
    for f in os.listdir(DATA_DIR):
        if f.startswith("part") and f.endswith(".json"):
            try:
                os.remove(os.path.join(DATA_DIR, f))
            except OSError:
                pass
    parts = []
    for i, ch in enumerate(chunks):
        cl = [c["v"] for c in ch if c["t"] == "laws"]
        cs = [c["v"] for c in ch if c["t"] == "standards"]
        fn = "data/part%03d.json" % i
        with open(os.path.join(ROOT, fn), "w", encoding="utf-8") as fp:
            json.dump({"laws": cl, "standards": cs}, fp, ensure_ascii=False)
        parts.append(fn)
        print("  写出 %s  laws=%d standards=%d" % (fn, len(cl), len(cs)))
    manifest = {"parts": parts, "lastUpdated": last_updated}
    with open(os.path.join(ROOT, "data/manifest.json"), "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False)
    print("  写出 data/manifest.json  parts=%d" % len(parts))

    # 精简 index.html
    html = open(INDEX, encoding="utf-8").read()
    # 1) 删除所有 <script>window.DATA = {...}</script> 内联数据块
    before = len(html)
    html = re.sub(r"<script>\s*window\.DATA\s*=\s*\{.*?\}\s*</script>", "", html, flags=re.DOTALL)
    removed = before - len(html)
    print("  移除内联数据块字节数: %d" % removed)

    # 2) 替换 init() 的数据加载逻辑为分块加载
    old_init = '''async function init(){
  // 优先用内联数据（data-inline.js），即使 data.json 在线不可达/CDN缓存也能正常显示
  DATA = window.DATA || {laws:[],standards:[],lastUpdated:""};
  try{
    const r=await fetch("data.json?t="+Date.now());
    if(r.ok){ const d=await r.json(); if(d && (d.laws||d.standards)) DATA=d; }
  }catch(e){ /* 保留内联数据，不影响显示 */ }
  $("#lastUpdated").textContent=DATA.lastUpdated||"-";'''
    new_init = '''async function init(){
  // 分块加载：把大文件拆成多个小文件，避免 GitHub Pages 对大文件在国内节点被截断
  DATA={laws:[],standards:[],lastUpdated:""};
  try{
    const m=await fetch("data/manifest.json?t="+Date.now()).then(r=>r.ok?r.json():null);
    if(m&&m.parts&&m.parts.length){
      const parts=await Promise.all(m.parts.map(p=>fetch(p+"?t="+Date.now()).then(r=>r.ok?r.json():null).catch(()=>null)));
      for(const c of parts){ if(c){ if(Array.isArray(c.laws))DATA.laws=DATA.laws.concat(c.laws); if(Array.isArray(c.standards))DATA.standards=DATA.standards.concat(c.standards); } }
      if(m.lastUpdated)DATA.lastUpdated=m.lastUpdated;
    }
  }catch(e){}
  if(!DATA.laws.length && !DATA.standards.length){
    try{ const r=await fetch("data.json?t="+Date.now()); if(r.ok){ const d=await r.json(); if(d&&(d.laws||d.standards))DATA=d; } }catch(e){}
  }
  $("#lastUpdated").textContent=DATA.lastUpdated||"-";'''
    if old_init in html:
        html = html.replace(old_init, new_init)
        print("  已替换 init() 为分块加载")
    else:
        print("  [警告] 未匹配到旧 init()，请检查 index.html")

    open(INDEX, "w", encoding="utf-8").write(html)
    print("  写出 index.html  新大小: %d 字节 (%.1f KB)" % (len(html), len(html)/1024))

if __name__ == "__main__":
    main()
