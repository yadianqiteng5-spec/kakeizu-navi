# 直近N本を、指定開始日から1日ずつの過去日付に設定（既存と被らせない用）
import sys, os, json, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_to_livedoor import wsse_header, load_config, FUNNEL_HTML
from set_dates import build_dated_entry, put

BASE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(BASE, "articles")
N = int(sys.argv[1])
start = datetime.date.fromisoformat(sys.argv[2])

uid, key, blog = load_config()
manifest = json.load(open(os.path.join(ADIR, "manifest.json"), encoding="utf-8"))
posted = json.load(open(os.path.join(BASE, "posted.json"), encoding="utf-8"))
ordered = [m for m in manifest if m["slug"] in posted]
targets = ordered[-N:]
print("対象 %d本: %s 〜 %s" % (len(targets), start.isoformat(),
      (start + datetime.timedelta(days=len(targets)-1)).isoformat()))
for i, m in enumerate(targets):
    d = start + datetime.timedelta(days=i)
    dt_iso = d.isoformat() + "T10:00:00+09:00"
    body = open(os.path.join(ADIR, m["file"]), encoding="utf-8").read() + FUNNEL_HTML
    xml = build_dated_entry(m["title"], body, uid, m.get("category"), dt_iso)
    st = put(posted[m["slug"]], xml, uid, key)
    flag = "OK " if str(st).startswith("2") else "NG "
    print("%s%s  %s" % (flag, d.isoformat(), m["slug"][:34]))
    time.sleep(1.2)
