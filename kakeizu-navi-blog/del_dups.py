import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_to_livedoor import wsse_header, load_config
from urllib import request, error
uid, key, blog = load_config()
DEL = ["meigi-yokin-souzoku","meigi-yokin-sozoku","meigi-yokin-sozoku-2","meigi-yokin-sozoku-3"]
posted = json.load(open("posted.json", encoding="utf-8"))
manifest = json.load(open("articles/manifest.json", encoding="utf-8"))
for slug in DEL:
    url = posted.get(slug)
    if not url:
        print("skip(なし)", slug); continue
    req = request.Request(url, method="DELETE")
    req.add_header("X-WSSE", wsse_header(uid, key))
    req.add_header("Authorization", 'WSSE profile="UsernameToken"')
    try:
        with request.urlopen(req, timeout=30) as r:
            print("DEL", r.status, slug)
    except error.HTTPError as e:
        print("ERR", e.code, slug); continue
    posted.pop(slug, None)
    time.sleep(1)
manifest = [m for m in manifest if m["slug"] not in DEL]
json.dump(posted, open("posted.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(manifest, open("articles/manifest.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("残り manifest:", len(manifest), "/ posted:", len(posted))
