# 家系図Navi デプロイ手順

Fly.io + Cloudflare（drumnavi.com）構成での公開手順です。

## 前提

- Fly.io アカウント取得済み
- Cloudflare で drumnavi.com 管理中
- GitHub アカウント

---

## 1. Fly CLI のインストール

```powershell
# PowerShell
iwr https://fly.io/install.ps1 -useb | iex
```

インストール後、PowerShell を再起動して以下で確認:

```powershell
fly version
```

---

## 2. Fly にログイン

```powershell
fly auth login
```

ブラウザが開いてログイン完了。

---

## 3. アプリ名の重複チェック・変更

`fly.toml` の `app = "kakeizu-navi"` は **Fly.io全体でユニーク** である必要があります。
すでに使われている場合は別名（例: `kakeizu-navi-drum` / `drumnavi-kakeizu` 等）に変更してください。

---

## 4. 初回デプロイ

家系図ナビのプロジェクトディレクトリで:

```powershell
cd "C:\Users\user\Desktop\家計図ナビ"
fly launch --no-deploy --copy-config --name kakeizu-navi --region nrt
```

`--copy-config` で既存の `fly.toml` を使用、`--no-deploy` でまずアプリ作成のみ。

---

## 5. APIキーを Secrets に登録

```powershell
fly secrets set ANTHROPIC_API_KEY="sk-ant-xxxxxxxx"
fly secrets set GEMINI_API_KEY="AIzaxxxxxxxx"
```

> Secrets は Fly.io 側で暗号化保管され、コードや GitHub には絶対に上がりません。
> アプリ内では `os.environ.get("GEMINI_API_KEY")` でそのまま読めます。

---

## 6. デプロイ実行

```powershell
fly deploy
```

完了すると以下のURLでアクセス可能:

```
https://kakeizu-navi.fly.dev
```

動作確認してください。

---

## 7. カスタムドメイン設定（kakeizu.drumnavi.com）

### 7-1. Fly側にドメイン登録

```powershell
fly certs add kakeizu.drumnavi.com
```

すると以下のような出力が出ます（重要なのは下2行）:

```
You can validate your ownership of kakeizu.drumnavi.com by:

1: Adding an AAAA record to your DNS service which reads:
    AAAA @ 2a09:8280:1::xx:xxxx

2: Adding an A record to your DNS service which reads:
    A @ 66.241.124.xxx

OR

3: Adding a CNAME record to your DNS service which reads:
    CNAME kakeizu.drumnavi.com → kakeizu-navi.fly.dev
```

**CNAME方式が一番簡単**なので、3 をメモしてください。

### 7-2. Cloudflare で CNAME 追加

drumnavi.com のダッシュボード → DNS → Records → **Add record**:

| 項目 | 設定値 |
|---|---|
| Type | **CNAME** |
| Name | `kakeizu` |
| Target | `kakeizu-navi.fly.dev` |
| Proxy status | **🔘 DNS only（グレー雲）** ← 重要 |
| TTL | Auto |

⚠️ Proxy を ON（オレンジ雲）にすると Fly.io の SSL 検証が失敗します。**まずグレー雲で動作確認 → SSL 確定後に必要ならオレンジ雲に変更**。

### 7-3. SSL証明書の発行確認

数分待ったあと:

```powershell
fly certs show kakeizu.drumnavi.com
```

`Configured = true`、`Issued certificate = true` になれば完了。

ブラウザで **https://kakeizu.drumnavi.com** にアクセス → 動作確認。

---

## 8. 運用コマンド

```powershell
# ログ確認
fly logs

# 状態確認
fly status

# 再起動
fly machine restart

# 設定変更後の再デプロイ
fly deploy

# Secrets 一覧（値は見えない）
fly secrets list

# スケール変更（常時稼働にしたい場合）
fly scale count 1 --min-machines-running 1

# メモリ増強
fly scale memory 1024
```

---

## 9. コスト目安

| 設定 | 月額（参考） |
|---|---|
| 512MB / auto_stop あり | $0〜$2（無料クレジット$5枠内） |
| 512MB / 常時稼働 | $3〜$4 |
| 1GB / 常時稼働 | $5〜$6 |
| アウトバウンド転送 | 100GB/月まで無料、超過は$0.02/GB |

→ MVP は無料枠内、本格運用しても月数百円〜千円程度。

---

## 10. トラブルシュート

### アプリが起動しない
```powershell
fly logs
```
で Python エラーやモジュール不足を確認。`requirements.txt` の漏れが多い。

### OOM (Out Of Memory)
```powershell
fly scale memory 1024
```
で 1GB に増強。

### SSL証明書が発行されない
Cloudflare が Proxy ON になっていないか確認。グレー雲にする。

### カスタムドメインで開けない
```powershell
fly certs show kakeizu.drumnavi.com
nslookup kakeizu.drumnavi.com
```
で DNS 反映状況を確認。Cloudflare 設定後 5〜15分かかることあり。

---

## 11. GitHub プライベートリポジトリ運用

ローカルから直接 `fly deploy` する分には GitHub 不要ですが、
CI/CD（GitHub Actions → 自動デプロイ）を組む場合は以下:

```powershell
# 初回のみ
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/kakeizu-navi.git
git push -u origin main
```

GitHub リポジトリは **Private** で作成してください。
