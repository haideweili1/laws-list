import json, re

data = json.load(open('data.json', encoding='utf-8'))

# 版权/国外标准编号前缀（这些标准文本受版权保护，只能给官方商店/出版信息页，无法免费取全文）
PREFIX = re.compile(r'^(IEC|UL|CSA|EN|BS EN|DIN|ASTM|ISO|C22\.2|BSI|ANSI|JIS|KS)', re.IGNORECASE)
# 立法全文（法规/法令/条例），不应标版权限制
LEGIS = re.compile(r'(法规|法令|条例|指令|regulation|directive)', re.IGNORECASE)

REMARK_TEXT = "受版权保护，仅提供官方商店/出版信息页（非全文），无法免费获取全文。"

n_std = 0
hit_ids = []
for it in data.get('standards', []):
    stdno = (it.get('stdNo') or '').strip()
    name = it.get('name') or ''
    # 命中条件：标准编号以版权标准前缀开头，且不是立法全文
    if PREFIX.match(stdno) and not LEGIS.search(name):
        # 不覆盖已有非空备注
        if not it.get('remark'):
            it['remark'] = REMARK_TEXT
            n_std += 1
            hit_ids.append(it.get('id'))

# laws 表里若有 IEC/UL 等（一般不会），同样处理
n_law = 0
for it in data.get('laws', []):
    docno = (it.get('docNumber') or '').strip()
    name = it.get('name') or ''
    if PREFIX.match(docno) and not LEGIS.search(name):
        if not it.get('remark'):
            it['remark'] = REMARK_TEXT
            n_law += 1
            hit_ids.append(it.get('id'))

json.dump(data, open('data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"wrote remark to standards={n_std}, laws={n_law}, total={n_std+n_law}")
print("sample ids:", hit_ids[:10], "..." if len(hit_ids) > 10 else "")
