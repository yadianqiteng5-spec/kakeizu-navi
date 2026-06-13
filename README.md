# 🌳 家系図Navi｜相続・事業承継シミュレーター

[![Tests](https://github.com/yadianqiteng5-spec/kakeizu-navi/actions/workflows/test.yml/badge.svg)](https://github.com/yadianqiteng5-spec/kakeizu-navi/actions/workflows/test.yml)
[![Precision](https://img.shields.io/badge/精度検証-国税庁公表値と一致-brightgreen)](./tests/test_precision_regression.py)
[![Tests Count](https://img.shields.io/badge/tests-60%20passing-brightgreen)](./tests)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36%2B-FF4B4B)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-Proprietary-lightgrey)](#-ライセンス)
[![AI](https://img.shields.io/badge/AI-Claude%20%2B%20Gemini-9B59B6)](#)
[![Zero Retention](https://img.shields.io/badge/data-zero%20retention-1ABC9C)](#-プライバシーゼロリテンション設計)
[![Legal Safety](https://img.shields.io/badge/弁護士法72条-配慮済-2C3E50)](./core/legal_safety.py)

家族構成を入力するだけで法定相続分を計算し、事業承継リスクを診断するStreamlitアプリ。
○○Naviシリーズの第1弾。

🔗 **Live**: [https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/](https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/)

---

## ⚖️ 重要な免責事項

本アプリの結果は **一般的なシミュレーション** であり、**法的な助言ではありません**。
具体的な判断・手続きは、**弁護士・税理士・司法書士等の専門家**にご相談ください。

本アプリは **弁護士法72条**（非弁活動の禁止）に抵触しないよう、
特定事案への法律事務は一切行わない設計です。

---

## 🔒 プライバシー（ゼロ・リテンション設計）

- 入力された個人情報（家族構成・資産情報・音声等）は、**サーバーに一切保存されません**
- データはブラウザのセッション内のみで処理され、閉じた時点で完全消去
- AI 解析データは AI モデルの学習に利用されない設定で運用
- アップロード画像・音声はオンメモリ（`BytesIO`）で処理、ディスクには書き出さない

---

## 🚀 主要機能

| 機能 | 内容 |
|---|---|
| 入力 | テキスト・画像アップロード・音声録音 |
| AI解析 | Claude（テキスト/画像）／Gemini（音声・診断） |
| 中間編集 | AI抽出結果をユーザーが確認・修正可能 |
| 家系図描画 | Graphviz による自動レイアウト |
| 法定相続分計算 | 無限代襲・半血兄弟・直系尊属の繰り上がり・代襲（甥姪まで）対応 |
| 養子区分 | 実子／普通養子／特別養子（相続税法15条2項の養子算入制限対応） |
| 遺留分計算 | 民法1042条以下に準拠 |
| 同時死亡推定 | 民法32条の2 対応 |
| 相続放棄 | 枝ごと除外、代襲不発生 |
| 相続税概算 | 基礎控除・概算税額（参考値） |
| 生命保険非課税枠 | 500万円 × 法定相続人数 |
| 事業承継リスク | 自社株分散・配偶者集中の警告 |
| 遺言書ガイド | 遺留分配慮・遺言執行者指定の注意点 |
| 死後手続きタイムライン | 7日以内〜10ヶ月以内の手続き一覧 |
| PDF出力 | レポート形式で結果を保存 |
| AI診断 | Gemini で「最優先の一手」を提示 |

---

## ⚖️ カバー済み法律ケース（自動テスト済み）

`tests/test_inheritance.py` の **39ケース全通過**（国税庁速算表と複数の実例で**厳密一致**を確認） を確認済み。`python -X utf8 tests/test_inheritance.py` で再現可能。

| 分類 | ケース | 根拠条文 |
|---|---|---|
| **基本順位** | 配偶者 + 子（1/2 : 1/2） | 民法900条1号 |
| | 配偶者のみ（全部） | 民法900条 |
| | 配偶者 + 直系尊属（2/3 : 1/3） | 民法900条2号 |
| | 配偶者 + 兄弟姉妹（3/4 : 1/4） | 民法900条3号 |
| **代襲相続** | 子の死亡 → 孫が代襲（無限代襲） | 民法887条2項 |
| | 兄弟の死亡 → 甥姪が代襲（一代限り） | 民法889条2項 |
| | 相続放棄者の子は代襲しない | 民法939条 |
| **同時死亡推定** | 親と子の同時死亡 → 相互に相続権なし、代襲は成立 | 民法32条の2 |
| **半血兄弟** | 全血 : 半血 = 2 : 1 | 民法900条4号但書 |
| **直系尊属繰上** | 両親死亡 → 祖父母が相続 | 民法889条1項 |
| **特別養子** | 実親との親族関係は終了（実親から相続不可） | 民法817条の9 |
| | 養親からは通常通り相続 | 民法817条の2 |
| **普通養子** | 実親・養親いずれからも相続可能 | 民法809条 |
| **遺留分** | 兄弟姉妹のみが相続人 → 遺留分なし | 民法1042条 |
| | 直系尊属のみ → 総体的遺留分1/3 | 民法1042条1号 |
| | 配偶者・子がいる場合 → 総体的遺留分1/2 | 民法1042条2号 |
| **相続税** | 養子算入制限（実子あり=1名、なし=2名） | 相続税法15条2項 |
| | 基礎控除（3,000万円 + 600万円×法定相続人数） | 相続税法15条1項 |
| | 生命保険非課税枠（500万円×法定相続人数） | 相続税法12条 |
| **小規模宅地等** | 特定居住用 80%減（330㎡まで） | 租特法69条の4 |
| | 特定事業用 80%減（400㎡まで） | 租特法69条の4 |
| | 貸付事業用 50%減（200㎡まで） | 租特法69条の4 |
| **配偶者居住権** | 制度説明セクション（民法1028条以下） | 民法1028〜1041条 |
| **二次相続** | 配偶者取得比0%/50%/100% の合計税額比較 | 相続税法19条の2 |
| **生前贈与** | 暦年贈与 vs 相続時精算課税の節税比較 | 相続税法21条の5〜9 |
| **遺言書ドラフト** | Gemini で自筆証書遺言の雛形生成 | 民法968条 |
| **国際相続警告** | 外国籍・海外資産がある場合の注意喚起 | 通則法36条、相続税法1条の3 |

### 🎯 計算精度

- 相続税は **相続税法16条準拠の正規ロジック**（法定相続分按分→速算表→合算）
- 速算表は **国税庁公表値**（8段階・速算控除額付き）
- 単純ケースで**国税庁シミュレーターと一致**する精度を確認
  - 1億円・配偶者+子2名 → **630万円**（厳密一致）✓
  - 2億円・配偶者+子2名 → **2,700万円**（厳密一致）✓
  - 5億円・配偶者+子3名 → **1億1,924万円**（厳密一致）✓
- 任意の法定相続分（配偶者+子/配偶者+直系尊属/配偶者+兄弟/単独）に対応する `_calculate_total_tax_from_shares` を実装
- 暦年贈与は2024年改正の**7年持戻し**を反映（過大な節税効果を防止）

> ℹ️ 上記は **一般的なシミュレーション** を提供するものであり、個別事案への法的助言ではありません。
> 寄与分（民法904条の2）・特別受益（民法903条）・特別寄与料（民法1050条）などは未対応のため、
> 該当する事案では必ず弁護士・税理士にご相談ください。

---

## 🛠 技術スタック

- **Frontend/Backend**: Streamlit (Python 3.11+)
- **AI**: Anthropic Claude API（テキスト/画像）／Google Gemini API（音声/診断）
- **可視化**: Graphviz（家系図）、Plotly（相続分円グラフ）
- **PDF**: reportlab + 組み込みCIDフォント

---

## 💻 ローカル実行

```powershell
# 依存パッケージ
pip install -r requirements.txt

# APIキー設定（オプション）
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:GEMINI_API_KEY = "AIza..."

# 起動
streamlit run app.py
```

ブラウザで http://localhost:8501 にアクセス。

---

## 🛡️ 品質保証の仕組み

| 層 | 仕組み | タイミング |
|---|---|---|
| CI/CD | GitHub Actions（Python 3.11/3.12） | push/PR/月次cron |
| 精度リグレッション | 国税庁公表値との厳密照合 | テスト時 |
| pre-commit hook | `git config core.hooksPath .githooks` で有効化 | ローカルコミット時 |
| AI出力検証 | `core/ai_validation.py` のクロスバリデーション | Gemini診断/遺言書生成時 |

### 🔔 通知設定

CI/デプロイの通知設定は [`NOTIFICATIONS.md`](./NOTIFICATIONS.md) を参照:
- 📨 GitHubメール通知（標準・設定不要）
- 💬 Slack/Discord通知（Webhook URLをSecrets登録するだけ）
- 🚨 失敗時にIssue自動作成（`ci-failure` ラベル）
- 🌐 Streamlit Cloud デプロイ通知

---

## ☁️ デプロイ（Streamlit Community Cloud）

1. このリポジトリをフォーク／クローン
2. [share.streamlit.io](https://share.streamlit.io) にログイン
3. New app → リポジトリと `app.py` を指定
4. Settings → Secrets で以下を設定:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   GEMINI_API_KEY = "AIza..."
   ```
5. Deploy → 数分で公開完了

---

## 📁 プロジェクト構成

```
家計図ナビ/
├── app.py                       # メインアプリ
├── requirements.txt
├── core/
│   ├── family_tree.py           # データモデル（Person, Relationship）
│   ├── inheritance.py           # 法定相続分・遺留分・相続税計算
│   ├── claude_client.py         # Claude API 連携
│   ├── gemini_client.py         # Gemini API 連携（音声・診断）
│   ├── pdf_export.py            # PDF レポート出力
│   └── legal_safety.py          # 非弁活動回避モジュール
└── .streamlit/
    └── config.toml              # 本番用設定
```

---

## 📜 ライセンス

© 2026 Mirai Navi. All rights reserved.

家系図Navi は ○○Navi シリーズの登録商品です。
無断複製・商用利用は禁止されています。
