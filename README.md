# 🌳 家系図Navi｜相続・事業承継シミュレーター

家族構成を入力するだけで法定相続分を計算し、事業承継リスクを診断するStreamlitアプリ。
○○Naviシリーズの第1弾。

🔗 **Live**: [https://kakeizu-navi.streamlit.app](https://kakeizu-navi.streamlit.app)（公開後にURL更新）

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

© 2026 DrumNavi. All rights reserved.

家系図Navi は ○○Navi シリーズの登録商品です。
無断複製・商用利用は禁止されています。
