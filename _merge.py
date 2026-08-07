import json, glob, html, os

def is_search(u):
    if not u:
        return True
    s = u.lower()
    # 真正的搜索结果页：搜索框查询参数 / 搜索引擎 / 站点 search?q=
    if ('baidu.com/s' in s or 's?wd' in s or 'advanced_search' in s
            or '/search?' in s or '?wd=' in s or '?q=' in s or '?s=' in s
            or '&q=' in s or '&s=' in s):
        return True
    # 例外：标准委详情页、FDA 官方指引文档页（URL 含 /search 但是内容页）
    if 'std.samr.gov.cn/gb/search/gbDetailed' in s:
        return False
    if 'search-fda-guidance-documents' in s:
        return False
    return False

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

# load current data.json (exceptions already applied) and pre-session backup
data = json.load(open('data.json', encoding='utf-8'))
bak = json.load(open('data.json.bak', encoding='utf-8'))

def idx(d):
    m = {}
    for tbl in ('laws', 'standards'):
        for it in d.get(tbl, []):
            m[it.get('id')] = it
    return m

cur_map = idx(data)
bak_map = idx(bak)

# collect batch outputs
batch_files = sorted(glob.glob('_batches/_batch_*_out.json'))
batch_map = {}
for bf in batch_files:
    for o in json.load(open(bf, encoding='utf-8')):
        batch_map[o['id']] = o
print('batch output entries:', len(batch_map))

# apply to data.json
applied = skipped = 0
for iid, o in batch_map.items():
    it = cur_map.get(iid)
    if not it:
        print('  WARN id not in data:', iid)
        continue
    nl = o.get('new_link', '')
    if is_search(nl):
        skipped += 1
        continue
    it['link'] = nl
    applied += 1

json.dump(data, open('data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# verify
tot_search = sum(1 for tbl in ('laws', 'standards') for it in data.get(tbl, [])
                 if is_search(it.get('link', '')))
tot_all = sum(len(data.get(tbl, [])) for tbl in ('laws', 'standards'))
print(f'applied={applied} skipped(search-type new link)={skipped}')
print(f'TOTAL entries={tot_all}  remaining search-type links={tot_search}')

# build report
exceptions = ['L0005', 'L0006', 'L0007', 'S0034']
target_ids = list(batch_map.keys()) + exceptions
high = low = failed = 0
rows = []
for iid in target_ids:
    o = batch_map.get(iid)
    if o:
        nl = o.get('new_link', '')
        src = o.get('source_desc', '')
        q = o.get('quality', '')
        note = o.get('note', '')
        tbl = o.get('table', '')
        nm = o.get('name', '')
    else:
        it = cur_map.get(iid)
        nl = it.get('link', '')
        tbl = it.get('table', '') or ('standards' if iid.startswith('S') else 'laws')
        nm = it.get('name', '')
        src = '例外项升级为新版/权威解读'
        q = 'high'
        note = ''
    old = ''
    bk = bak_map.get(iid)
    if isinstance(bk, dict):
        old = bk.get('link', '')
    if is_search(nl):
        q = 'failed'
        failed += 1
    elif q == 'low':
        low += 1
    else:
        high += 1
    rows.append(dict(iid=iid, name=nm, tbl=tbl, old=old, new=nl, src=src, q=q, note=note))

print(f'report rows={len(rows)} high={high} low={low} failed={failed}')

json.dump(dict(total=len(rows), high=high, low=low, failed=failed,
               applied=applied, skipped=skipped, remaining_search=tot_search),
          open('_link_summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def esc(u):
    return html.escape(u or '')

body_rows = []
for i, r in enumerate(rows, 1):
    badge = {'high': 'good', 'low': 'warn', 'failed': 'bad'}[r['q']]
    btxt = {'high': '直达全文', 'low': '可用(第三方/非官方)', 'failed': '未改善(仍搜索页)'}[r['q']]
    body_rows.append(
        '<tr>'
        '<td class="c">{i}</td>'
        '<td><b>{nm}</b><br><span class="t">{tbl} ｜ {iid}</span></td>'
        '<td class="old"><a href="{old}" target="_blank">{old}</a><div class="tag bad">搜索兜底</div></td>'
        '<td class="new"><a href="{new}" target="_blank">{new}</a><div class="tag {badge}">{btxt}</div></td>'
        '<td class="s">{src}</td>'
        '<td class="n">{note}</td>'
        '</tr>'.format(i=i, nm=esc(r['name']), tbl=esc(r['tbl']), iid=esc(r['iid']),
                       old=esc(r['old']), new=esc(r['new']), badge=badge, btxt=btxt,
                       src=esc(r['src']), note=esc(r['note']) if r['note'] else '—'))

html_doc = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>法律法规清单 链接全量升级报告</title>
<style>
 body{font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:24px;color:#222;background:#fafafa}
 h1{font-size:20px} .sub{color:#666;font-size:13px;margin-bottom:8px}
 .stat{display:inline-block;margin:4px 14px 4px 0;font-size:13px} .stat b{font-size:18px}
 table{border-collapse:collapse;width:100%;background:#fff;font-size:12px}
 th,td{border:1px solid #e3e3e3;padding:6px 8px;vertical-align:top;text-align:left}
 th{background:#f0f4f8;position:sticky;top:0}
 td.c{text-align:center;width:28px;color:#888}
 a{color:#0b57d0;word-break:break-all} .old a{color:#b00020} .new a{color:#0a7d33}
 .tag{display:inline-block;margin-top:3px;font-size:10.5px;padding:1px 6px;border-radius:4px}
 .bad{background:#fde7e9;color:#b00020} .good{background:#e6f4ea;color:#0a7d33} .warn{background:#fff4e5;color:#a35400}
 .t{color:#999;font-size:10.5px} .s{color:#444;width:160px} .n{color:#a35400;width:190px}
 .legend{margin:8px 0 14px;font-size:12px}
</style></head><body>
<h1>法律法规清单 · 链接全量升级报告</h1>
<div class="sub">生成：2026-08-06 ｜ 数据源：data.json（已备份 data.json.bak）｜ 共升级 __N__ 条搜索兜底链接 → 直达全文/可用链接</div>
<div>
  <span class="stat">升级总数 <b>__N__</b></span>
  <span class="stat">高质量(官方直达) <b style="color:#0a7d33">__HIGH__</b></span>
  <span class="stat">可用(第三方/非官方) <b style="color:#a35400">__LOW__</b></span>
  <span class="stat">未改善(仍搜索页) <b style="color:#b00020">__FAILED__</b></span>
  <span class="stat">全库剩余搜索链接 <b>__REMAIN__</b></span>
</div>
<div class="legend">图例：<span class="tag bad">搜索兜底</span>=原来点开是搜索页；<span class="tag good">直达全文</span>=官方/权威点开即正文；<span class="tag warn">可用</span>=第三方或非官方但能看全文；<span class="tag bad">未改善</span>=本次未取到更好链接。</div>
<table>
<tr><th>#</th><th>法规/标准</th><th>原链接（搜索兜底）</th><th>新链接</th><th>来源说明</th><th>备注</th></tr>
__ROWS__
</table>
</body></html>"""
html_doc = (html_doc
            .replace('__N__', str(len(rows)))
            .replace('__HIGH__', str(high))
            .replace('__LOW__', str(low))
            .replace('__FAILED__', str(failed))
            .replace('__REMAIN__', str(tot_search))
            .replace('__ROWS__', ''.join(body_rows)))

open('_full_report.html', 'w', encoding='utf-8').write(html_doc)
print('report bytes:', len(html_doc))
