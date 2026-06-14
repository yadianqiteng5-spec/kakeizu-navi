#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
livedoor Blog AtomPub 一括投稿スクリプト（家系図Navi 送客記事用）

特徴:
- 認証情報(APIキー等)はスクリプトに書かず、config.ini か環境変数から読み込む。
- 既定は「下書き(draft)」投稿。確認してから --publish で公開。
- articles/manifest.json と articles/*.html を読み、各記事末尾にLP送客CTAを自動付与。

使い方:
  python post_to_livedoor.py --dry-run            # 投稿せずXMLを確認
  python post_to_livedoor.py --limit 1            # 1本だけ下書き投稿（テスト）
  python post_to_livedoor.py                      # 全部 下書き投稿
  python post_to_livedoor.py --publish            # 全部 公開
  python post_to_livedoor.py --only iryubun --publish   # slug指定で1本だけ公開
"""
import argparse, base64, configparser, hashlib, json, os, sys, time
from datetime import datetime, timezone
from urllib import request, error
from xml.sax.saxutils import escape

ROOT = "https://livedoor.blogcms.jp/atompub"
LP_URL = "https://yadianqiteng5-spec.github.io/kakeizu-navi-lp/"
DEFAULT_BLOG = "infinity_peace24"  # ブログのハンドル名（環境変数 LIVEDOOR_BLOG で上書き可）

# 全記事末尾に自動付与する送客ブロック（LPへの動線）
FUNNEL_HTML = """
<div style='border:1px solid #ddd;border-radius:10px;padding:16px;background:#fafafa;margin-top:24px;'>
  <p style='font-weight:bold;font-size:1.1em;margin-top:0;'>「うちの場合、誰がいくら相続する？」を今すぐ確認</p>
  <p>家系図Naviは、家族構成を入力するだけで<strong>法定相続分・相続税の概算・遺留分</strong>までAIが自動計算する無料ツールです。登録不要・ログイン不要、入力データはブラウザ内だけで処理（サーバー保存なし）。</p>
  <p><a href='%s' target='_blank' rel='noopener' style='display:inline-block;padding:12px 22px;background:#2f6df0;color:#fff;border-radius:30px;text-decoration:none;font-weight:bold;'>&#9654; 無料で相続シミュレーションを試す</a></p>
</div>
<p style='font-size:0.85em;color:#777;margin-top:14px;'>&#8251; 本記事は一般的な制度の解説です。具体的な金額・手続きは税理士・弁護士等の専門家にご確認ください。</p>
""" % LP_URL


def reg_env(name):
    """Windowsの環境変数(User/Machine)をレジストリから直接読む。未設定ならNone。"""
    try:
        import winreg
    except Exception:
        return None
    for root, sub in [(winreg.HKEY_CURRENT_USER, r"Environment"),
                      (winreg.HKEY_LOCAL_MACHINE,
                       r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")]:
        try:
            k = winreg.OpenKey(root, sub)
            v, _ = winreg.QueryValueEx(k, name)
            winreg.CloseKey(k)
            if v:
                return v
        except OSError:
            pass
    return None


def load_config():
    uid = os.environ.get("LIVEDOOR_ID")
    key = os.environ.get("LIVEDOOR_APIKEY")
    blog = os.environ.get("LIVEDOOR_BLOG")
    base = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.join(base, "config.ini")
    if (not uid or not key or not blog) and os.path.exists(cfg):
        cp = configparser.ConfigParser()
        cp.read(cfg, encoding="utf-8")
        s = cp["livedoor"]
        uid = uid or s.get("id")
        key = key or s.get("apikey")
        blog = blog or s.get("blog")
    # 環境変数が渡っていなければレジストリから直接読む（パス移動やプロセス継承に強い）
    uid = uid or reg_env("LIVEDOOR_ID") or DEFAULT_BLOG
    key = key or reg_env("LIVEDOOR_APIKEY") or reg_env("Livedoor API")
    blog = blog or reg_env("LIVEDOOR_BLOG") or DEFAULT_BLOG
    missing = [n for n, v in [("id", uid), ("apikey", key)] if not v or v.startswith("your_") or v == "xxxxxxxxxx"]
    if missing:
        sys.exit("[設定不足] " + ", ".join(missing) + " が未設定です。"
                 "『手順0_環境変数を設定.bat』を実行してください（環境変数 LIVEDOOR_ID / LIVEDOOR_APIKEY）。")
    return uid, key, blog


def wsse_header(uid, key):
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = os.urandom(16)
    digest = hashlib.sha1(nonce + created.encode() + key.encode()).digest()
    return ('UsernameToken Username="%s", PasswordDigest="%s", Nonce="%s", Created="%s"'
            % (uid, base64.b64encode(digest).decode(),
               base64.b64encode(nonce).decode(), created))


def build_entry(title, body_html, author, category=None, draft=True):
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cat = ('  <category term="%s" />\n' % escape(category)) if category else ""
    draft_v = "yes" if draft else "no"
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">\n'
            '  <title>%s</title>\n'
            '  <author><name>%s</name></author>\n'
            '  <updated>%s</updated>\n'
            '%s'
            '  <content type="text/html"><![CDATA[%s]]></content>\n'
            '  <app:control><app:draft>%s</app:draft></app:control>\n'
            '</entry>'
            % (escape(title), escape(author), updated, cat, body_html, draft_v))


def post_entry(uid, key, blog, xml, dry=False):
    url = "%s/%s/article" % (ROOT, blog)
    if dry:
        print("\n--- DRY RUN: %s ---\n%s\n" % (url, xml))
        return ("DRY", "")
    req = request.Request(url, data=xml.encode("utf-8"), method="POST")
    req.add_header("X-WSSE", wsse_header(uid, key))
    req.add_header("Authorization", 'WSSE profile="UsernameToken"')
    req.add_header("Content-Type", "application/atom+xml;type=entry;charset=utf-8")
    try:
        with request.urlopen(req, timeout=30) as r:
            return (r.status, r.headers.get("Location", ""))
    except error.HTTPError as e:
        return ("ERR %s" % e.code, e.read().decode("utf-8", "ignore")[:300])
    except Exception as e:
        return ("ERR", str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="公開する（既定は下書き）")
    ap.add_argument("--dry-run", action="store_true", help="投稿せずXMLを表示")
    ap.add_argument("--limit", type=int, default=0, help="先頭N本だけ")
    ap.add_argument("--only", default=None, help="slug指定で1本だけ")
    ap.add_argument("--delete", default=None, help="指定したentry URLの記事を削除")
    ap.add_argument("--force", action="store_true", help="公開済みでも再投稿する")
    ap.add_argument("--update", default=None, help="slug指定で公開済み記事を上書き更新(PUT)")
    args = ap.parse_args()

    uid, key, blog = load_config()

    if args.delete:
        req = request.Request(args.delete, method="DELETE")
        req.add_header("X-WSSE", wsse_header(uid, key))
        req.add_header("Authorization", 'WSSE profile="UsernameToken"')
        try:
            with request.urlopen(req, timeout=30) as r:
                print("DELETE ->", r.status, args.delete)
        except error.HTTPError as e:
            print("DELETE ERR", e.code, e.read().decode("utf-8", "ignore")[:200])
        return
    base = os.path.dirname(os.path.abspath(__file__))
    adir = os.path.join(base, "articles")
    posted_path = os.path.join(base, "posted.json")
    posted = {}
    if os.path.exists(posted_path):
        try:
            posted = json.load(open(posted_path, encoding="utf-8"))
        except Exception:
            posted = {}

    allitems = json.load(open(os.path.join(adir, "manifest.json"), encoding="utf-8"))

    if args.update:
        it = next((x for x in allitems if x.get("slug") == args.update), None)
        if not it:
            sys.exit("slug が manifest にありません: " + args.update)
        url = posted.get(args.update)
        if not url:
            sys.exit("slug が posted.json にありません（未公開）: " + args.update)
        body = open(os.path.join(adir, it["file"]), encoding="utf-8").read()
        xml = build_entry(it["title"], body + FUNNEL_HTML, uid, it.get("category"), draft=False)
        req = request.Request(url, data=xml.encode("utf-8"), method="PUT")
        req.add_header("X-WSSE", wsse_header(uid, key))
        req.add_header("Authorization", 'WSSE profile="UsernameToken"')
        req.add_header("Content-Type", "application/atom+xml;type=entry;charset=utf-8")
        try:
            with request.urlopen(req, timeout=30) as r:
                print("UPDATE -> %s %s (%s)" % (r.status, args.update, url))
        except error.HTTPError as e:
            print("UPDATE ERR", e.code, e.read().decode("utf-8", "ignore")[:300])
        return

    items = allitems
    if args.only:
        items = [x for x in items if x.get("slug") == args.only]
    # 公開済み台帳にあるものはスキップ（--force で再投稿）
    if not args.force and not args.dry_run:
        before = len(items)
        items = [x for x in items if x.get("slug") not in posted]
        if before - len(items) > 0:
            print("（公開済みのためスキップ: %d本）" % (before - len(items)))
    if args.limit:
        items = items[:args.limit]
    if not items:
        print("新規の投稿対象はありません（すべて公開済み）。")
        return

    draft = not args.publish
    print("ブログ: %s / 新規対象: %d本 / モード: %s\n"
          % (blog, len(items), "公開" if args.publish else "下書き"))

    ok = 0
    for i, it in enumerate(items, 1):
        body = open(os.path.join(adir, it["file"]), encoding="utf-8").read()
        xml = build_entry(it["title"], body + FUNNEL_HTML, uid,
                          it.get("category"), draft)
        st, info = post_entry(uid, key, blog, xml, args.dry_run)
        flag = "OK " if (str(st).startswith("2") or st == "DRY") else "NG "
        print("%s[%d/%d] %-34s -> %s %s" % (flag, i, len(items), it["title"][:32], st, info))
        if flag == "OK ":
            ok += 1
            if not args.dry_run:
                posted[it["slug"]] = info  # entry URLを台帳へ記録
                json.dump(posted, open(posted_path, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
        if not args.dry_run:
            time.sleep(1.5)  # サーバー負荷軽減

    print("\n完了: %d/%d 成功（%s）" % (ok, len(items), "公開" if args.publish else "下書き"))
    if draft and not args.dry_run:
        print("→ livedoor管理画面の[下書き]を確認し、問題なければ --publish で公開してください。")


if __name__ == "__main__":
    main()
