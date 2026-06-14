# -*- coding: utf-8 -*-
"""公開済み記事の投稿日を1日ずつずらす（最新=base-date、古いものほど過去へ）。
使い方:
  python set_dates.py --dry-run                 # 日付プランだけ表示
  python set_dates.py --only about              # 1本だけ適用(テスト)
  python set_dates.py                           # 全件適用
  python set_dates.py --base-date 2026-06-06    # 最新記事の日付を指定
"""
import sys, os, json, time, argparse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_to_livedoor import wsse_header, load_config, FUNNEL_HTML
from urllib import request, error
from xml.sax.saxutils import escape

BASE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(BASE, "articles")


def build_dated_entry(title, body_html, author, category, dt_iso):
    cat = ('  <category term="%s" />\n' % escape(category)) if category else ""
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">\n'
            '  <title>%s</title>\n'
            '  <author><name>%s</name></author>\n'
            '  <published>%s</published>\n'
            '  <updated>%s</updated>\n'
            '%s'
            '  <content type="text/html"><![CDATA[%s]]></content>\n'
            '  <app:control><app:draft>no</app:draft></app:control>\n'
            '</entry>' % (escape(title), escape(author), dt_iso, dt_iso, cat, body_html))


def put(url, xml, uid, key):
    req = request.Request(url, data=xml.encode("utf-8"), method="PUT")
    req.add_header("X-WSSE", wsse_header(uid, key))
    req.add_header("Authorization", 'WSSE profile="UsernameToken"')
    req.add_header("Content-Type", "application/atom+xml;type=entry;charset=utf-8")
    try:
        with request.urlopen(req, timeout=30) as r:
            return str(r.status)
    except error.HTTPError as e:
        return "ERR %s %s" % (e.code, e.read().decode("utf-8", "ignore")[:150])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-date", default="2026-06-06", help="最新記事の日付(=今日)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()

    uid, key, blog = load_config()
    manifest = json.load(open(os.path.join(ADIR, "manifest.json"), encoding="utf-8"))
    posted = json.load(open(os.path.join(BASE, "posted.json"), encoding="utf-8"))
    ordered = [m for m in manifest if m["slug"] in posted]
    N = len(ordered)
    base = datetime.date.fromisoformat(a.base_date)
    print("対象 %d本 / 最新=%s 〜 最古=%s\n"
          % (N, base.isoformat(), (base - datetime.timedelta(days=N - 1)).isoformat()))

    ok = 0
    for i, m in enumerate(ordered):
        d = base - datetime.timedelta(days=(N - 1 - i))
        dt_iso = "%sT10:00:00+09:00" % d.isoformat()
        if a.only and m["slug"] != a.only:
            continue
        if a.dry_run:
            print("%s  %s" % (d.isoformat(), m["slug"]))
            continue
        body = open(os.path.join(ADIR, m["file"]), encoding="utf-8").read() + FUNNEL_HTML
        xml = build_dated_entry(m["title"], body, uid, m.get("category"), dt_iso)
        st = put(posted[m["slug"]], xml, uid, key)
        flag = "OK " if st.startswith("2") else "NG "
        print("%s%s  %s" % (flag, d.isoformat(), m["slug"][:34]))
        if flag == "OK ":
            ok += 1
        time.sleep(1.2)
    if not a.dry_run:
        print("\n完了: %d 件 更新" % ok)


if __name__ == "__main__":
    main()
