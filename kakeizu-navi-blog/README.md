# 家系図Navi 送客記事 → livedoor 自動投稿

livedoor Blog の **AtomPub API** に、SEO記事を一括投稿するスクリプトです。
各記事の末尾に、LP（家系図Navi）への送客CTAを自動で付けます。

- LP: https://yadianqiteng5-spec.github.io/kakeizu-navi-lp/
- 認証情報（APIキー）は **あなたのPCのconfig.iniにだけ**置きます。スクリプト本体には含みません。

---

## セットアップ（初回だけ）

認証情報は **Windowsの環境変数** に保存します（config.iniは不要）。
ブログのハンドル名は **infinity_peace24** をスクリプトに既定設定済みです。

### 1. APIキー（AtomPub用パスワード）を発行
livedoor管理画面 → **ブログ設定 → その他 → APIキー** →「発行する」。
表示された10桁の英数字をメモ（これがパスワードの代わり）。

### 2. 環境変数に保存
**`手順0_環境変数を設定.bat`** をダブルクリックし、
　1) livedoor ID　2) APIキー　を入力するだけ。
　→ `LIVEDOOR_ID` / `LIVEDOOR_APIKEY` / `LIVEDOOR_BLOG` が永続保存されます。

> 入力したAPIキーは **あなたのPCの環境変数にだけ**保存され、外部には出ません。
> 設定後は **一度ウィンドウを閉じて**から手順1を実行してください（環境変数の反映のため）。

### 3. Python確認
Python 3 が入っていればOK（標準ライブラリのみ使用・追加インストール不要）。

### （参考）環境変数を使わない場合
`config.ini` を置けばそちらも読みます（環境変数が優先）。書式は:
```
[livedoor]
id = あなたのlivedoor ID
apikey = 発行した10桁のキー
blog = infinity_peace24
```

---

## 使い方

すべて `kakeizu-navi-blog` フォルダ内で実行します。

```bash
# (a) まず投稿XMLを画面確認（投稿しない）
python post_to_livedoor.py --dry-run

# (b) テストで1本だけ「下書き」投稿
python post_to_livedoor.py --limit 1

# → livedoor管理画面の[下書き]を開いて表示崩れ・リンクを確認

# (c) 全部「下書き」投稿
python post_to_livedoor.py

# (d) 問題なければ「公開」
python post_to_livedoor.py --publish

# slug指定で1本だけ公開
python post_to_livedoor.py --only iryubun --publish
```

- 既定は **下書き**。`--publish` を付けたときだけ公開されます。
- 投稿間隔は1.5秒（サーバー負荷軽減）。

---

## ★ 全自動で量産＆公開（おすすめ）

**`記事を量産して公開.bat` をダブルクリック** → 本数を入力するだけ。
AI（Gemini）が新テーマを考えて記事を生成 → そのままlivedoorへ公開します。

- 認証情報（livedoor APIキー／Geminiキー）は環境変数から自動取得（画面に出ません）
- `posted.json`（公開済み台帳）により、**何度実行しても既存記事は重複しません**
- テーマを自分で決めたい場合は `topics.txt` に書いて:
  `python generate_articles.py --topics topics.txt` → `python post_to_livedoor.py --publish`

コマンドで使う場合:
```
python generate_articles.py --auto 5     # AIが5テーマ考えて生成
python post_to_livedoor.py --publish     # 新規ぶんだけ公開（既存はスキップ）
```

> 注意（YMYL）: 生成記事は一般的な相続情報です。各記事末尾に免責を自動付与していますが、
> 公開前に内容を確認したい場合は `post_to_livedoor.py`（--publishなし＝下書き）で投稿し、
> 管理画面で確認してください。

---

## 記事を手書きで増やす場合

`articles/` に HTMLファイルを追加し、`articles/manifest.json` に1行足すだけ。

```json
{
  "slug": "seizen-zoyo-2024",
  "title": "生前贈与110万円はもう古い？2024年改正で変わったこと",
  "category": "生前対策",
  "file": "05-seizen-zoyo.html"
}
```

HTMLは本文だけ（`<h2>`見出し＋段落）。末尾のCTA・免責は自動付与されます。
タイトル先頭付近にキーワード、本文に`<h2>`、LPへの内部リンク&mdash;&mdash;の型を踏襲すればSEOに有利です。

---

## 仕様メモ（出典）

- 投稿先: `https://livedoor.blogcms.jp/atompub/＜blog＞/article`
- 認証: WSSE（`PasswordDigest = base64(sha1(nonce + created + APIキー))`）
- 下書き/公開: `<app:control><app:draft>yes|no</app:draft></app:control>`
- 注意: AtomPub APIでは **タグ付与・「続きを書く」・限定公開** は設定できません（本文・カテゴリ・公開状態のみ）。
