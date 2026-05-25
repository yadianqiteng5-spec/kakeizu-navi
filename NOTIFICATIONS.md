# 通知設定ガイド

家系図Navi の CI/CD・デプロイ通知の設定方法。

---

## 📨 標準で有効な通知（設定不要）

### 1. GitHubメール通知

GitHubアカウントに登録したメールアドレスに以下が自動送信されます:

- ✅ **CI成功時**: 月次cron実行・各PR等で成功時のみメール送信オプション
- ❌ **CI失敗時**: 即座にメール通知（デフォルトで有効）
- 🚨 **失敗時Issue自動作成**: `ci-failure` ラベル付きで起票され、Issue購読中なら追加メール

**通知設定の調整**:
- https://github.com/settings/notifications
- 「Actions」セクションで送信頻度を変更可能

---

## 💬 オプション通知（任意設定）

### 2. Slack通知

1. **Slack側でWebhookを作成**:
   - https://api.slack.com/apps → Create New App → "Incoming Webhooks"
   - 投稿先チャンネルを選び `https://hooks.slack.com/services/T.../B.../...` をコピー

2. **GitHub Secrets に登録**:
   ```
   Settings → Secrets and variables → Actions → New repository secret
   Name:  SLACK_WEBHOOK_URL
   Value: https://hooks.slack.com/services/...
   ```

3. **次のpushから自動でSlackに通知**:
   - 成功時: 緑色アタッチメント
   - 失敗時: 赤色アタッチメント + 詳細ログへのリンクボタン

### 3. Discord通知

1. **Discord側でWebhookを作成**:
   - サーバー設定 → 連携サービス → ウェブフックを作成
   - URLをコピー

2. **GitHub Secrets に登録**:
   ```
   Name:  DISCORD_WEBHOOK_URL
   Value: https://discord.com/api/webhooks/...
   ```

3. **次のpushから自動でDiscordに通知**:
   - Embedで結果表示、テスト/Lintの状態を inline で表示

---

## 🌐 Streamlit Cloud デプロイ通知

Streamlit Community Cloud は **GitHub への push を検知して自動再デプロイ** します。

### 標準通知（設定不要）
- Streamlit Cloud → アプリの Settings → "Email notifications" を ON にすると、
  デプロイ成功/失敗時にメール通知

### 手動確認
- https://share.streamlit.io/ → アプリを選択 → "Manage app" でログ確認

---

## 🔔 通知が来ない場合

| 症状 | 対処 |
|---|---|
| メールが来ない | GitHubアカウントのメール確認・スパム振り分け確認 |
| Slack通知が来ない | `SLACK_WEBHOOK_URL` が正しく設定されているか確認 |
| GitHub Issuesが作られない | リポジトリ設定で Actions の write 権限が有効か確認 |
| Streamlit Cloudが再デプロイされない | アプリのSettings → "Reboot app" |

---

## 📊 通知の使い分け推奨

| シーン | 推奨通知 |
|---|---|
| 個人開発（少人数） | GitHubメール標準のみで十分 |
| チーム開発 | Slack/Discord通知を追加 |
| 本番運用（重要） | Slack + メール + 月次cron結果を確認 |
| 法改正検知（重要） | 月次cron結果の Issue を必ず確認 |
