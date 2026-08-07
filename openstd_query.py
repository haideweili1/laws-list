import urllib.request, urllib.parse, re, json, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def search_std(q):
    base = "https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&q=" + urllib.parse.quote(q)
    try:
        html = fetch(base)
    except Exception as e:
        return {"q": q, "error": str(e)}
    hcnos = re.findall(r"hcno[=:]?\s*['\"]?([0-9A-Fa-f]{32})", html)
    hcnos = list(dict.fromkeys(hcnos))
    # also try find newGbInfo links
    links = re.findall(r"newGbInfo\?hcno=([0-9A-Fa-f]{32})", html)
    hcnos = hcnos + [h for h in links if h not in hcnos]
    out = {"q": q, "list_url": base, "hcno_count": len(hcnos), "hcnos": hcnos[:5]}
    if hcnos:
        hcno = hcnos[0]
        detail = "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=" + hcno
        out["detail_url"] = detail
        try:
            d = fetch(detail)
            # try to find a fulltext/online read link
            ol = re.findall(r'href=["\']([^"\']*(?:pdf|online|read|gbwj|full)[^"\']*)["\']', d, re.I)
            out["detail_html_len"] = len(d)
            out["online_links"] = ol[:5]
            out["has_text"] = ("全文" in d) or ("标准号" in d)
        except Exception as e:
            out["detail_error"] = str(e)
    return out

for q in ["GB/T 20988", "GB/T 19000", "GB/T 19002"]:
    print(json.dumps(search_std(q), ensure_ascii=False))
    print("---")
