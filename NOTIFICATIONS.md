# 通知・デプロイ反映ガイド

家系図Navi の CI/CD 通知と本番反映手順（実装に即した正確版）。

---

## 📨 現在有効な通知（追加設定なしで動くもの）

`.github/workflows/test.yml` は **push / PR / 毎月1日（cron）** でテストを実行します。

- ❌ **失敗時**: GitHub 標準のメール通知が届きます（GitHub の Actions 通知が有効な場合）。
- 📋 **結果サマリー**: 各実行の **GitHub → Actions → 該当 run → Summary** に成功/失敗が出力されます。

通知頻度の調整: <https://github.com/settings/notifications> の「Actions」セクション。

> ⚠️ 失敗時の **Issue 自動作成・Slack/Discord 通知は現状ワークフローに実装されていません**
> （以前のドキュメントには記載がありましたが、対応するステップは存在しません）。欲しい場合は下記「拡張」を参照。

---

## 🚀 本番への反映（Streamlit Community Cloud）

本番は **Streamlit Community Cloud**。**自動デプロイは効かないため、push 後に手動 Reboot が必要**です。

1. `git push origin main`
2. アプリ右下の **「Manage app」** → **⋮** → **「Reboot app」**（または share.streamlit.io のアプリ ⋮ → Reboot）
3. 1〜2分で最新 main が反映

> ⚠️ 隣の **「Delete app」は絶対に押さない**こと。

Streamlit Cloud のメール通知: アプリ Settings → "Email notifications" を ON にするとデプロイ結果が届きます。

---

## 🔧 通知を拡張する場合（任意・現状未実装）

Slack/Discord 通知や失敗時 Issue 自動作成が必要なら、`test.yml` の `if: failure()` ステップに
各アクション（Slack/Discord Webhook 送信、`peter-evans/create-issue` 等）と必要な `permissions`
（例: `issues: write`）を**追加実装**する必要があります（現状は未設定）。

---

## 🔔 トラブルシュート

| 症状 | 対処 |
|---|---|
| CI 失敗メールが来ない | GitHub アカウントのメール/スパム確認、Settings → Notifications → Actions を確認 |
| 本番に反映されない | push 後に Streamlit の Manage app → **Reboot app** を実行（自動反映は効かない） |
| 月次 cron の結果を見たい | GitHub → Actions → 該当の scheduled run の **Summary** を確認 |
