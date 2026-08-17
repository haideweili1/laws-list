import json
from urllib.parse import urlparse

d = json.load(open('data.json', encoding='utf-8'))
laws = d['laws']
stds = d['standards']

CN_SUFFIX = ['gov.cn', 'samr.gov.cn', 'openstd.samr.gov.cn', 'std.samr.gov.cn', 'npc.gov.cn',
    'nhc.gov.cn', 'cfsa.net.cn', 'sppt.cfsa.net.cn', 'miit.gov.cn', 'mem.gov.cn', 'mot.gov.cn',
    'mps.gov.cn', 'customs.gov.cn', 'aqsiq.gov.cn', 'snca.gov.cn', 'cnas.org.cn', 'cca.org.cn',
    'chinacdc.cn', 'mii.gov.cn', 'most.gov.cn', 'mee.gov.cn', 'nea.gov.cn', 'ndrc.gov.cn',
    'mof.gov.cn', 'chinatax.gov.cn', 'sac.gov.cn', 'cqc.com.cn', 'cma.cn', 'moe.gov.cn',
    'mohurd.gov.cn', 'mnr.gov.cn', 'cmastd.cn', 'cnemc.cn']
FOREIGN_DOM = ['iec.ch', 'webstore.iec.ch', 'iso.org', 'ul.com', 'ulstandards.com', 'csagroup.org',
    'webstore.ansi.org', 'standards.ieee.org', 'beuth.de', 'din.de', 'shop.bsigroup.com', 'bsigroup.com',
    'nen.nl', 'snz.org.nz', 'standards.govt.nz', 'sai-global.com', 'standards.org.au', 'ons.gov.uk',
    'legislation.gov.uk', 'gov.uk', 'eur-lex.europa.eu', 'ec.europa.eu', 'ema.europa.eu', 'echa.europa.eu',
    'fda.gov', 'ecfr.gov', 'federalregister.gov', 'nist.gov', 'osha.gov', 'epa.gov', 'energy.gov',
    'transportation.gov', 'congress.gov', 'gpo.gov', 'nap.edu', 'law.resource.org', 'oecd.org', 'who.int',
    'fao.org', 'ilo.org', 'un.org', 'wto.org', 'codex', 'jisc.go.jp', 'kats.go.kr', 'rssb.co.uk', 'etsi.org',
    'cen.eu', 'cenelec.eu', 'en-standard.eu', 'standards.gov', 'ansi.org', 'afnor.org', 'bac-lac.gc.ca',
    'legislation.qld.gov.au', 'comlaw.gov.au', 'legislation.nsw.gov.au', 'nzlegislation.govt.nz',
    'csa.ca', 'europa.eu', 'gov.au', 'go.jp', 'gc.ca', 'gesetze-im-internet.de', 'inmetro.gov.br',
    'oag.ca.gov', 'vde.com', 'ecolex.org', 'ipcc-nggip.iges.or.jp', 'uni.com', 'webstore.uni.com',
    'intertek.com', 'standards.iteh.ai', 'iteh.ai', 'contactalimentaire.fr', 'sist.org.cn', 'sist.si',
    'thnet.gov.cn']
THIRD = ['doc88.com', 'docin.com', 'baidu.com', 'foodcontactscience.com', 'pkulaw', 'gdzjsc', 'sohu.com',
    'wendang', 'wenku', 'zhihu.com', '51cto', 'cnblogs', 'csdn', 'jb51', 'sina', 'qq.com', '163.com',
    '360doc', 'thepaper', 'infzm', 'cnki', 'wanfang', 'marmot', 'anycached', '91bzx', 'hao86', 'chinalaw',
    'lexis', 'westlaw', 'google.com', 'bing.com', 'yahoo', 'wikipedia', 'weixin', 'mp.weixin', 'yigou968.com',
    'xunxiang.site', 'faxin.cn', 'findlaw.cn', 'wikisource.org', 'ttbz.org.cn', 'bzwxw', 'gongbao',
    'chinacourt', 'spc.net.cn', 'std-cn', 'sist.org.cn']

def host(l):
    try:
        return urlparse(l).netloc.lower()
    except Exception:
        return ''

def judge(link):
    if not link:
        return '无链接'
    h = host(link)
    if not h:
        return '其他(非http)'
    for c in CN_SUFFIX:
        if c in h:
            return '国内官方'
    for f in FOREIGN_DOM:
        if f in h:
            return '国外官方'
    for t in THIRD:
        if t in h:
            return '疑似第三方'
    return '需您判断'

rows = []
for it in laws + stds:
    j = judge(it.get('link', ''))
    if j != '国内官方':
        rows.append({
            'id': it['id'],
            'name': it.get('name', '')[:54],
            'link': it.get('link', '') or '',
            'cat': j,
            'tbl': 'laws' if it['id'].startswith('L') else 'standards',
        })

from collections import Counter
c = Counter(r['cat'] for r in rows)
print("分类统计:", dict(c), "总计", len(rows))

# 打印疑似第三方段到 stdout
third = [r for r in rows if r['cat'] == '疑似第三方']
print("\n===== 疑似第三方/镜像 共 %d 条 =====" % len(third))
for r in third:
    print(f"{r['id']} | {r['name']} | {r['link']} | {r['tbl']}")

# 写报告
with open('_nonofficial_review.md', 'w', encoding='utf-8') as f:
    f.write("# 非国内官方链接逐条清单（供您看质量、决定是否替换）\n\n")
    f.write(f"> 清单共 {len(laws)+len(stds)} 条，其中**非国内官方链接 {len(rows)} 条**。\n")
    f.write("- **国外官方**（EN/IEC/UL/CSA/VDE/各国政府等发布机构）：一般无需替换；\n")
    f.write("- **疑似第三方/镜像**（文档站、厂商站等）：建议优先换官方源；\n")
    f.write("- **需您判断(域名)**：域名我无法归类，请点开链接看是否官方正文；\n")
    f.write("- **无链接**：待补官方源。\n\n")
    sections = [
        ('疑似第三方', '### 一、疑似第三方 / 文档镜像（建议优先替换）'),
        ('需您判断', '### 二、需您判断（域名见链接，请点开确认）'),
        ('无链接', '### 三、无链接（需补官方源）'),
        ('国外官方', '### 四、国外官方发布机构（通常可保留）'),
    ]
    for key, title in sections:
        sub = [r for r in rows if r['cat'] == key]
        if not sub:
            continue
        f.write(f"\n{title} — {len(sub)} 条\n\n")
        f.write("| 序号 | 名称 | 当前链接 | 表 |\n|---|---|---|---|\n")
        for r in sub:
            f.write(f"| {r['id']} | {r['name']} | {r['link'] if r['link'] else '（空）'} | {r['tbl']} |\n")
print("\n报告已写入 _nonofficial_review.md")
