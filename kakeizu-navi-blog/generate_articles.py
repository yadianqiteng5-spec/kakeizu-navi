# -*- coding: utf-8 -*-
"""
記事 自動生成（Gemini API）→ articles/*.html ＋ manifest.json に追加
- APIキーは環境変数 Gemini_API_KEY から読み込み（スクリプトに書かない）
- 既存タイトルと重複しないテーマをAIに考えさせ、本文を生成
使い方:
  python generate_articles.py --auto 5      # 新規テーマを5本ぶん生成
  python generate_articles.py --topics topics.txt   # 指定テーマで生成
モデル変更:  環境変数 GEMINI_MODEL（既定 gemini-2.5-flash）
"""
import argparse, json, os, re, sys, time
from urllib import request, error

LP_URL = "https://yadianqiteng5-spec.github.io/kakeizu-navi-lp/"
CATEGORIES = ["相続の基礎知識", "相続税の節税", "相続でもめない", "生前対策", "遺言", "事業承継"]
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
BASE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(BASE, "articles")
MANIFEST = os.path.join(ADIR, "manifest.json")


def _reg_env(name):
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


def gemini_key():
    k = (os.environ.get("Gemini_API_KEY") or os.environ.get("GEMINI_API_KEY")
         or _reg_env("Gemini_API_KEY") or _reg_env("GEMINI_API_KEY"))
    if not k:
        sys.exit("[設定不足] 環境変数 Gemini_API_KEY が見つかりません。")
    return k


def gemini(prompt, schema, key, temp=0.7):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
           % (MODEL, key))
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temp,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    req = request.Request(url, data=json.dumps(body).encode("utf-8"),
                          method="POST", headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except error.HTTPError as e:
        sys.exit("Gemini APIエラー %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))


def load_manifest():
    return json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else []


def next_index():
    mx = 0
    for f in os.listdir(ADIR):
        m = re.match(r"(\d+)-", f)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx + 1


def propose_topics(n, existing_titles, key):
    schema = {"type": "object", "properties": {"topics": {"type": "array", "items": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "category": {"type": "string"}},
        "required": ["title", "category"]}}}, "required": ["topics"]}
    prompt = (
        "あなたは相続・終活分野のSEO編集者です。無料の相続シミュレーター『家系図Navi』へ"
        "検索流入から送客するブログ記事のテーマを%d個提案してください。\n"
        "・日本の相続/相続税/遺言/生前贈与/事業承継に関する、検索需要の高い具体的テーマ\n"
        "・categoryは次から選ぶ: %s\n"
        "・以下の既存タイトルと内容が重複しないこと:\n%s"
        % (n, " / ".join(CATEGORIES), "\n".join("- " + t for t in existing_titles))
    )
    return gemini(prompt, schema, key, temp=0.9)["topics"]


def write_article(topic, key):
    schema = {"type": "object", "properties": {
        "title": {"type": "string"},
        "slug": {"type": "string"},
        "category": {"type": "string"},
        "body_html": {"type": "string"}}, "required": ["title", "slug", "category", "body_html"]}
    prompt = (
        "日本の相続に関するSEOブログ記事を1本、HTML本文だけで書いてください。\n"
        "テーマ: %s（カテゴリ: %s）\n\n"
        "【厳守ルール】\n"
        "1. ですます調。専門用語はかみくだいて、一般読者向けにやさしく。\n"
        "2. 出力はHTMLの本文フラグメントのみ（<h1>やCTAボックスは入れない／末尾CTAは別途自動付与される）。\n"
        "3. 構成: 導入<p>（その中に必ず1つ、家系図NaviへのリンクをHTMLで入れる→ "
        "<a href='%s' target='_blank' rel='noopener'>…</a>）→ <h2>見出し3〜4個</h2>＋<p>/<ul>。\n"
        "4. 日本の法律・税制の一般的に確立した内容のみ。年で変わる細かい数値は断定を避け、"
        "『要件あり』『専門家に確認』等の留保を入れる。誤情報を書かない。\n"
        "5. 800〜1200字程度。マークダウンや```は使わない。HTMLタグのみ。\n"
        "6. titleはSEOを意識し先頭付近にキーワード。slugは英小文字とハイフンのみの短い文字列。\n"
        "7. categoryは指定のものを使う。"
        % (topic["title"], topic.get("category", CATEGORIES[0]), LP_URL)
    )
    art = gemini(prompt, schema, key, temp=0.7)
    if art.get("category") not in CATEGORIES:
        art["category"] = topic.get("category", CATEGORIES[0])
    return art


def slugify(s, used):
    s = re.sub(r"[^a-z0-9-]", "", s.lower().replace(" ", "-")).strip("-") or "article"
    base = s
    i = 2
    while s in used:
        s = "%s-%d" % (base, i)
        i += 1
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", type=int, default=0, help="新規テーマをN本AIに考えさせ生成")
    ap.add_argument("--topics", default=None, help="テーマ一覧ファイル(1行1テーマ)")
    ap.add_argument("--max-total", type=int, default=0, help="記事総数がこの数以上なら生成しない（暴走防止）")
    args = ap.parse_args()

    manifest = load_manifest()
    if args.max_total and len(manifest) >= args.max_total:
        print("総数 %d 本が上限 %d に到達。生成をスキップします。" % (len(manifest), args.max_total))
        return
    key = gemini_key()
    existing_titles = [m["title"] for m in manifest]
    used_slugs = set(m["slug"] for m in manifest)

    # テーマ収集
    topics = []
    if args.topics and os.path.exists(args.topics):
        for line in open(args.topics, encoding="utf-8"):
            t = line.strip()
            if t and not t.startswith("#"):
                topics.append({"title": t, "category": CATEGORIES[0]})
    if args.auto > 0:
        print("AIに新規テーマを%d本提案させています..." % args.auto)
        topics += propose_topics(args.auto, existing_titles, key)
    if not topics:
        sys.exit("テーマがありません。--auto N か --topics file を指定してください。")

    idx = next_index()
    added = 0
    for t in topics:
        print("生成中: %s" % t["title"])
        try:
            art = write_article(t, key)
        except SystemExit as e:
            print("  スキップ（%s）" % e); continue
        slug = slugify(art.get("slug", ""), used_slugs)
        used_slugs.add(slug)
        fname = "%02d-%s.html" % (idx, slug)
        open(os.path.join(ADIR, fname), "w", encoding="utf-8").write(art["body_html"])
        manifest.append({"slug": slug, "title": art["title"],
                         "category": art["category"], "file": fname})
        json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("  追加: %s" % fname)
        idx += 1
        added += 1
        time.sleep(1)

    print("\n生成完了: %d本を manifest に追加しました。" % added)
    print("→ 公開するには: python post_to_livedoor.py --publish")


if __name__ == "__main__":
    main()
