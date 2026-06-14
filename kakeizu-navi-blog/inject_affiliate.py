# -*- coding: utf-8 -*-
# 全記事にPR表記＋税理士ドットコム(アクセストレード)広告を挿入。投稿日は保持。再実行しても二重挿入しない。
import sys, os, json, time, re, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_to_livedoor import wsse_header, load_config, FUNNEL_HTML
from set_dates import build_dated_entry, put
from urllib import request

BASE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(BASE, "articles")
RK = "0100npm600otmq"  # 識別用（二重挿入チェック）

PR = ('<p style="font-size:0.8em;color:#888;margin:0 0 12px;">'
      '※本記事はプロモーション（アフィリエイト広告）を含みます。</p>')

AFFIL = ('<div style="border:1px solid #e6e6e6;border-radius:10px;padding:16px;background:#fbfbf6;margin-top:20px;">'
  '<p style="font-weight:bold;font-size:1.05em;margin:0 0 6px;">&#128204; 相続税の不安は、専門家に相談を</p>'
  '<p style="font-size:0.92em;color:#555;margin:0 0 12px;">'
  '「うちは申告が必要？」「もっと節税できる？」——気になることは、相続に強い税理士に相談するのが確実です。'
  '全国の税理士を無料で探せる<strong>税理士ドットコム</strong>なら、自分に合う専門家が見つかります。</p>'
  '<p style="text-align:center;margin:0;">'
  '<a href="https://h.accesstrade.net/sp/cc?rk=0100npm600otmq" rel="nofollow" referrerpolicy="no-referrer-when-downgrade" target="_blank">'
  '<img src="https://h.accesstrade.net/sp/rr?rk=0100npm600otmq" alt="税理士ドットコム" border="0" width="468" height="60" style="max-width:100%;height:auto;"></a></p></div>')


def get_xml(url, uid, key):
    req = request.Request(url, method="GET")
    req.add_header("X-WSSE", wsse_header(uid, key))
    req.add_header("Authorization", 'WSSE profile="UsernameToken"')
    with request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--last", type=int, default=0, help="末尾N本だけ対象（新着用）")
    a = ap.parse_args()
    uid, key, blog = load_config()
    manifest = json.load(open(os.path.join(ADIR, "manifest.json"), encoding="utf-8"))
    posted = json.load(open(os.path.join(BASE, "posted.json"), encoding="utf-8"))
    items = [m for m in manifest if m["slug"] in posted]
    if a.only:
        items = [m for m in items if m["slug"] == a.only]
    if a.last:
        items = items[-a.last:]
    if a.limit:
        items = items[:a.limit]

    ok = skip = 0
    for m in items:
        url = posted[m["slug"]]
        try:
            xml = get_xml(url, uid, key)
        except Exception as e:
            print("GET ERR", m["slug"], e); continue
        if RK in xml:
            print("skip(挿入済) %s" % m["slug"][:34]); skip += 1; continue
        pm = re.search(r"<published>(.*?)</published>", xml)
        pub = pm.group(1) if pm else None
        if not pub:
            print("no published, skip", m["slug"]); continue
        body = PR + open(os.path.join(ADIR, m["file"]), encoding="utf-8").read() + FUNNEL_HTML + AFFIL
        new = build_dated_entry(m["title"], body, uid, m.get("category"), pub)
        st = put(url, new, uid, key)
        flag = "OK " if str(st).startswith("2") else "NG "
        print("%s%s  %s" % (flag, pub[:10], m["slug"][:30]))
        if flag == "OK ":
            ok += 1
        time.sleep(1.0)
    print("\n挿入 %d / スキップ %d / 合計対象 %d" % (ok, skip, len(items)))


if __name__ == "__main__":
    main()
