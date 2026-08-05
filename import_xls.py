#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导入脚本：把现有 laws.json + 两份 xls 合并成新结构 data.json
================================================================
- 现有 laws.json（111条：质量/环境职业/社会责任/反恐/信息安全）
- 文件1《产品标准清单、适用的法律法规清单》: sheet 质量 / EHS / 产品标准清单
- 文件2《合规性评价记录表》: 合规性评价结果+评价人 写入备注
- 全量合并、按法规/标准名称归一化去重（名称作主键）
- 所属领域：规则自动判（免费）
- 原文链接：保留现有精确链接；新条目生成官网搜索链接占位
- 旧字段 保管方式/保管期限/引入时间 丢弃
- 隐藏字段 适用地区：名称含"广东"标"广东"
输出：data.json（laws + standards 两个数组）
"""
import os, re, json, xlrd, urllib.parse
from collections import OrderedDict

ROOT = os.path.dirname(os.path.abspath(__file__))
LAWS_JSON = os.path.join(ROOT, "laws.json")
XLS_SRC = "D:/桌面文件/产品标准清单、适用的法律法规清单2026-1-5(1).xls"
XLS_EVAL = "D:/桌面文件/合规性评价记录表 2026.1.7(1).xls"
OUT = os.path.join(ROOT, "data.json")

# ---------- 工具 ----------
def excel_date(v):
    """Excel 序列号 -> YYYY-MM-DD；非数字原样返回字符串或空。"""
    if isinstance(v, float):
        v = int(v)
    if isinstance(v, int) and 30000 < v < 70000:
        from datetime import datetime, timedelta
        return (datetime(1899, 12, 30) + timedelta(days=v)).strftime("%Y-%m-%d")
    s = str(v).strip()
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else (s if s else "")

def full2half(s):
    return "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)

def norm(s):
    s = s.replace("\u3000", " ").replace("　", " ")
    s = full2half(s)
    s = re.sub(r"\s+", "", s)
    return s.lower().strip()

def domain_dept(url):
    u = (url or "").lower()
    m = {
        "npc.gov.cn": "全国人大常委会",
        "gov.cn": "国务院",
        "cac.gov.cn": "国家互联网信息办公室",
        "miit.gov.cn": "工业和信息化部",
        "samr.gov.cn": "国家市场监督管理总局",
        "std.samr.gov.cn": "国家市场监督管理总局",
        "mee.gov.cn": "生态环境部",
        "mem.gov.cn": "应急管理部",
        "customs.gov.cn": "海关总署",
        "mofcom.gov.cn": "商务部",
        "gov.cn/zhengce": "国务院",
    }
    for k, v in m.items():
        if k in u:
            return v
    return ""

def source_dept(source):
    m = {
        "中国人大网": "全国人大常委会", "中国政府网": "国务院",
        "国家网信办": "国家互联网信息办公室", "国家互联网信息办公室": "国家互联网信息办公室",
        "工业和信息化部": "工业和信息化部", "生态环境部": "生态环境部",
        "应急管理部": "应急管理部", "国家标准委": "国家市场监督管理总局",
        "国家标准化管理委员会": "国家市场监督管理总局", "国务院": "国务院",
        "商务部": "商务部", "海关总署": "海关总署",
    }
    return m.get((source or "").strip(), "")

def search_link(category, name):
    """按分类生成官网搜索链接占位（非直达正文）。"""
    q = urllib.parse.quote(name)
    if category == "信息安全":
        return "https://www.cac.gov.cn/search.htm?keyword=" + q
    if category == "反恐":
        return "https://www.gov.cn/zhengce/advanced_search?q=" + q
    # 质量 / 环境与职业健康 多在 gov.cn
    return "https://www.gov.cn/zhengce/advanced_search?q=" + q

def std_search_link(stdtype, name):
    q = urllib.parse.quote(name)
    m = {
        "国家标准": "https://std.samr.gov.cn/search?q=",
        "国际标准": "https://www.iso.org/search.html?q=",
        "欧盟标准": "https://eur-lex.europa.eu/search.html?q=",
        "美国FDA": "https://www.fda.gov/search?s=",
        "法国法令": "https://www.legifrance.gouv.fr/search?q=",
        "法国食品级法规通告": "https://www.legifrance.gouv.fr/search?q=",
        "德国LFGB": "https://www.gesetze-im-internet.de/englisch_lfgb/",
        "德国标准": "https://www.din.de/en/products-services/standards",
        "意大利标准": "https://www.uni.com/",
        "SVHC": "https://echa.europa.eu/search-for-chemicals?q=",
        "美国加州": "https://leginfo.legislature.ca.gov/",
        "巴西497法令": "https://www.planalto.gov.br/",
    }
    return m.get(stdtype, "https://www.baidu.com/s?wd=" + q + " 标准") + q

STD_PUBLISHER = {
    "国家标准": "国家标准化管理委员会", "行业标准": "相关行业主管部门",
    "国际标准": "国际标准化组织(ISO)", "欧盟标准": "欧盟", "美国FDA": "美国食品药品监督管理局",
    "法国法令": "法国", "法国食品级法规通告": "法国", "德国LFGB": "德国", "德国标准": "德国标准化学会(DIN)",
    "意大利标准": "意大利", "SVHC": "欧盟(ECHA)", "美国加州": "美国加州", "巴西497法令": "巴西",
    "巴西499法令": "巴西",
}

def best_tab(name):
    n = name
    if any(k in n for k in ["信息", "网络", "数据", "密码", "计算机", "隐私", "个人信息", "等级保护", "关键基础设施"]):
        return "信息安全"
    if any(k in n for k in ["反恐", "恐怖", "海关", "供应链", "贸易安全", "进出口"]):
        return "反恐"
    if any(k in n for k in ["职业", "工伤", "劳动", "健康", "消防", "职业病", "生产安全"]):
        return "环境与职业健康"
    if any(k in n for k in ["环境", "污染", "生态", "环保", "节能", "清洁", "排放", "土壤", "大气", "水污染"]):
        return "环境与职业健康"
    return "质量"

def infer_ehs_domains(name):
    d = []
    if any(k in name for k in ["环境", "污染", "生态", "环保", "节能", "清洁", "排放", "土壤", "大气", "水", "资源"]):
        d.append("环境")
    if any(k in name for k in ["职业", "工伤", "劳动", "健康", "消防", "职业病", "安全", "生产"]):
        d.append("职业健康安全")
    return d or ["环境"]

def extract_stdno(name):
    m = re.search(r"[A-Za-z]+(?:/[A-Za-z]+)?\.?\s*\d[\d.\-]+", name)
    if m:
        return re.sub(r"\s+", "", m.group(0))
    return ""

def stdtype_norm(remark):
    """从产品标准备注提取类型 + 状态。"""
    r = (remark or "").strip()
    status = "现行有效"
    if "即将实施" in r:
        status = "即将实施"
    elif "现行" in r:
        status = "现行有效"
    base = re.sub(r"[（(].*?[)）]", "", r).strip()
    mp = {
        "欧盟": "欧盟标准", "欧盟标准": "欧盟标准", "欧盟法规": "欧盟标准",
        "美国FDA": "美国FDA", "德国标准": "德国标准", "德国LFGB": "德国LFGB",
        "法国法令": "法国法令", "法国食品级法规通告": "法国食品级法规通告",
        "意大利标准": "意大利标准", "SVHC": "SVHC", "美国加州": "美国加州",
        "巴西497法令": "巴西497法令", "巴西499法令": "巴西499法令",
        "依据最新的SVHC清单": "SVHC",
        "国家标准": "国家标准", "国际标准": "国际标准", "行业标准": "行业标准",
        "法国": "法国法令", "JJF 1261.10-2023": "国家标准",
    }
    t = mp.get(base, base) if base else "国家标准"
    return t, status

# ---------- 读取现有 laws.json ----------
def load_existing():
    recs = []
    if not os.path.exists(LAWS_JSON):
        return recs
    data = json.load(open(LAWS_JSON, encoding="utf-8"))
    cat_map = {  # 旧 category id -> (新category, 基础domains)
        "infosec": ("信息安全", ["信息安全"]),
        "antiterror": ("反恐", ["反恐"]),
        "social": ("__social__", ["社会责任"]),
        "trisystem": ("__trisystem__", []),
    }
    for cat in data.get("categories", []):
        cid = cat.get("id", "")
        newcat, basedom = cat_map.get(cid, ("质量", ["质量"]))
        for law in cat.get("laws", []):
            name = law.get("name", "")
            if not name:
                continue
            eff = law.get("effectiveDate", "")
            status = {"在用": "现行有效", "即将实施": "即将实施", "已废止": "已废止"}.get(
                law.get("status", ""), "现行有效")
            src = law.get("source", "")
            link = law.get("sourceUrl", "")
            if newcat == "__social__":
                nc = best_tab(name); dom = ["社会责任"]
            elif newcat == "__trisystem__":
                nc = best_tab(name); dom = infer_ehs_domains(name) if nc == "环境与职业健康" else ([ "质量"] if nc=="质量" else [nc])
                if nc == "信息安全": dom = ["信息安全"]
                if nc == "反恐": dom = ["反恐"]
            else:
                nc = newcat; dom = basedom
            recs.append({
                "name": name, "docNumber": "", "dept": source_dept(src) or domain_dept(link),
                "effectiveDate": eff, "status": status, "domains": dom,
                "category": nc, "link": link, "remark": "",
                "region": "广东" if "广东" in name else "",
                "_origin": cid,
            })
    return recs

# ---------- 读取 xls 文件1 ----------
def load_xls_laws():
    recs = []
    wb = xlrd.open_workbook(XLS_SRC)
    for sheet, origin, cat in [("质量", "quality", "质量"), ("EHS", "ehs", "环境与职业健康")]:
        sh = wb.sheet_by_name(sheet)
        for r in range(3, sh.nrows):
            name = str(sh.cell_value(r, 1)).replace("\n", " ").strip()
            if not name or name == "名称":
                continue
            eff = excel_date(sh.cell_value(r, 2))
            clause = str(sh.cell_value(r, 3)).replace("\n", " ").strip()
            dept_rel = str(sh.cell_value(r, 4)).replace("\n", " ").strip()
            remark = str(sh.cell_value(r, 5)).replace("\n", " ").strip()
            rm = []
            if clause: rm.append("适用条款：" + clause)
            if dept_rel: rm.append("相关部门：" + dept_rel)
            if remark: rm.append(remark)
            if origin == "quality":
                dom = ["质量"]; nc = "质量"
            else:
                dom = infer_ehs_domains(name); nc = "环境与职业健康"
            recs.append({
                "name": name, "docNumber": "", "dept": domain_dept(""),
                "effectiveDate": eff, "status": "现行有效", "domains": dom,
                "category": nc, "link": "", "remark": "；".join(rm),
                "region": "广东" if "广东" in name else "",
                "_origin": origin,
            })
    return recs

def load_xls_standards():
    recs = []
    wb = xlrd.open_workbook(XLS_SRC)
    sh = wb.sheet_by_name("产品标准清单")
    for r in range(3, sh.nrows):
        name = str(sh.cell_value(r, 1)).replace("\n", " ").strip()
        if not name:
            continue
        eff = excel_date(sh.cell_value(r, 2))
        remark = str(sh.cell_value(r, 4)).replace("\n", " ").strip()
        stdtype, status = stdtype_norm(remark)
        recs.append({
            "name": name, "stdNo": extract_stdno(name), "stdType": stdtype,
            "publisher": STD_PUBLISHER.get(stdtype, ""), "effectiveDate": eff, "status": status,
            "link": std_search_link(stdtype, name), "remark": "",
            "region": "广东" if "广东" in name else "",
            "_origin": "std",
        })
    return recs

# ---------- 读取文件2 评价表 ----------
def load_eval():
    d = {}
    wb = xlrd.open_workbook(XLS_EVAL)
    sh = wb.sheet_by_index(0)
    for r in range(3, sh.nrows):
        name = str(sh.cell_value(r, 1)).replace("\n", " ").strip()
        if not name:
            continue
        std_req = str(sh.cell_value(r, 3)).replace("\n", " ").strip()
        evidence = str(sh.cell_value(r, 4)).replace("\n", " ").strip()
        result = str(sh.cell_value(r, 5)).replace("\n", " ").strip()
        evaluator = str(sh.cell_value(r, 6)).replace("\n", " ").strip()
        rm = str(sh.cell_value(r, 7)).replace("\n", " ").strip()
        parts = []
        if result: parts.append("合规评价：" + result)
        if evaluator: parts.append("评价人：" + evaluator)
        if std_req: parts.append("合规标准要求：" + std_req)
        if evidence: parts.append("措施证据：" + evidence)
        if rm: parts.append(rm)
        d[norm(name)] = "；".join(parts)
    return d

# ---------- 合并 ----------
def merge():
    laws = load_existing() + load_xls_laws()
    standards = load_xls_standards()
    eval_map = load_eval()

    law_idx = OrderedDict()
    for rec in laws:
        k = norm(rec["name"])
        if k in law_idx:
            old = law_idx[k]
            for f in ["docNumber", "dept", "effectiveDate", "link"]:
                if not old[f] and rec[f]:
                    old[f] = rec[f]
            if not old["status"] or old["status"] == "现行有效":
                if rec["status"] != "现行有效":
                    old["status"] = rec["status"]
            if rec["category"] in ("质量", "环境与职业健康") and old["category"] not in ("质量", "环境与职业健康"):
                old["category"] = rec["category"]
            old["domains"] = list(dict.fromkeys(old["domains"] + rec["domains"]))
            if rec["remark"]:
                old["remark"] = (old["remark"] + "；" + rec["remark"]).strip("；") if old["remark"] else rec["remark"]
            if rec["region"]:
                old["region"] = rec["region"]
        else:
            law_idx[k] = rec
    # 文件2 写入备注
    matched = 0
    for k, ev in eval_map.items():
        if k in law_idx:
            rec = law_idx[k]
            rec["remark"] = (rec["remark"] + "；【合规评价】" + ev).strip("；") if rec["remark"] else "【合规评价】" + ev
            matched += 1
    laws_out = []
    ABOLISH_EXACT = [
        "中华人民共和国环境保护法", "中华人民共和国环境影响评价法", "中华人民共和国清洁生产促进法",
        "中华人民共和国海洋环境保护法", "中华人民共和国大气污染防治法", "中华人民共和国水污染防治法",
        "中华人民共和国土壤污染防治法", "中华人民共和国固体废物污染环境防治法",
        "中华人民共和国噪声污染防治法", "中华人民共和国放射性污染防治法",
    ]
    def is_abolished(name):
        n = norm(name)
        for e in ABOLISH_EXACT:
            ne = norm(e)
            if n == ne or n == norm("《" + e + "》") or n.startswith(ne):
                return True
        return False
    for i, rec in enumerate(law_idx.values(), 1):
        rec.pop("_origin", None)
        if not rec.get("link"):
            rec["link"] = search_link(rec.get("category", "质量"), rec["name"])
        if rec.get("category") == "环境与职业健康" and is_abolished(rec["name"]):
            note = "（注：将于2026-08-15随《中华人民共和国生态环境法典》施行而废止）"
            if note not in rec["remark"]:
                rec["remark"] = (rec["remark"] + "；" + note).strip("；") if rec["remark"] else note
        rec["id"] = "L%04d" % i
        laws_out.append(rec)

    std_idx = OrderedDict()
    for rec in standards:
        k = norm(rec["name"])
        if k in std_idx:
            old = std_idx[k]
            for f in ["stdNo", "publisher", "effectiveDate", "link"]:
                if not old[f] and rec[f]:
                    old[f] = rec[f]
            old["stdType"] = rec["stdType"] or old["stdType"]
            if old["status"] == "现行有效" and rec["status"] != "现行有效":
                old["status"] = rec["status"]
        else:
            std_idx[k] = rec
    stds_out = []
    for i, rec in enumerate(std_idx.values(), 1):
        rec.pop("_origin", None)
        rec["id"] = "S%04d" % i
        stds_out.append(rec)

    out = {"lastUpdated": "2026-08-05", "laws": laws_out, "standards": stds_out}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"法律法规(去重后): {len(laws_out)} 条")
    print(f"产品标准(去重后): {len(stds_out)} 条")
    print(f"文件2 评价表匹配写入备注: {matched}/{len(eval_map)}")
    from collections import Counter
    print("法律法规 子分类分布:", dict(Counter(r["category"] for r in laws_out)))
    print("法律法规 状态分布:", dict(Counter(r["status"] for r in laws_out)))
    print("产品标准 类型分布:", dict(Counter(r["stdType"] for r in stds_out)))
    print("产品标准 状态分布:", dict(Counter(r["status"] for r in stds_out)))

if __name__ == "__main__":
    merge()
