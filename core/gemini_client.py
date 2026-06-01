"""
Gemini API連携モジュール（相続・事業承継診断）
- 環境変数 GEMINI_API_KEY または GOOGLE_API_KEY を読み込む
- 無料枠の gemini-2.5-flash を使用
"""
import os
import json
import re
from typing import Optional

_MODEL_NAME = "gemini-2.5-flash"
_FALLBACK_MODEL = "gemini-1.5-flash"


def _get_api_key() -> Optional[str]:
    """
    APIキーを取得（優先順位）:
    1. st.secrets["GEMINI_API_KEY"] - Streamlit Cloud Secrets / ローカル secrets.toml
    2. st.secrets["GOOGLE_API_KEY"] - 同上
    3. 環境変数 GEMINI_API_KEY
    4. 環境変数 GOOGLE_API_KEY
    """
    try:
        import streamlit as st
        for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            try:
                val = st.secrets.get(key)
                if val:
                    return val
            except Exception:
                pass
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def is_gemini_available() -> bool:
    """APIキーが設定されているかチェック"""
    return bool(_get_api_key())


# 直近のエラー（UI表示用・握り潰し防止）
last_error: Optional[str] = None


def get_last_error() -> Optional[str]:
    return last_error


# 相続は「死亡」を扱うため、セーフティフィルタの誤ブロックを防ぐ（事実ベースの法律情報）
_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

_resolved_model: Optional[str] = None   # 一度解決したモデル名をキャッシュ
_available_models: list = []            # list_models() で判明した利用可能モデル（診断用）


def available_models_str() -> str:
    """利用可能モデルの一覧文字列（エラー表示・診断用）"""
    if _available_models:
        names = [m.split("/")[-1] for m in _available_models]
        return ", ".join(names[:12])
    return "(取得できず)"


def _pick_model(genai, prefer: Optional[str] = None) -> str:
    """
    APIキーが実際に使えるモデルを list_models() で問い合わせて選ぶ。
    名前のズレ・モデル廃止で全滅しないための堅牢化。優先順位:
      1. secrets/env の GEMINI_MODEL
      2. 呼び出し側の希望(prefer)
      3. 新しめのflash系 → 旧flash → 任意のflash → 任意のgenerateContent対応
    """
    global _resolved_model, _available_models
    if _resolved_model:
        return _resolved_model

    override = _get_secret("GEMINI_MODEL")
    # 新しめ・現行で有効な可能性が高い順（廃止済みの1.5系は最後）
    prefs = [override, prefer,
             "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite",
             "gemini-flash-latest", "gemini-2.0-flash-001"]

    available = []
    try:
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                available.append(m.name)   # 例: "models/gemini-2.0-flash"
    except Exception:
        available = []
    _available_models = available

    def find(p):
        if not p:
            return None
        for a in available:
            if a == p or a == f"models/{p}" or a.split("/")[-1] == p:
                return a
        return None

    for p in prefs:
        hit = find(p)
        if hit:
            _resolved_model = hit
            return hit

    # 希望に合致しなければ、利用可能なflash系→任意を採用
    for a in available:
        if "flash" in a:
            _resolved_model = a
            return a
    if available:
        _resolved_model = available[0]
        return available[0]

    # list_models が取れない場合の最終手段（廃止済みの1.5系は避け現行系を既定に）
    _resolved_model = override or "gemini-2.0-flash"
    return _resolved_model


def _new_model(genai, name):
    """実際に使えるモデルを解決し、安全設定付きで GenerativeModel を返す。"""
    chosen = _pick_model(genai, prefer=name)
    return genai.GenerativeModel(chosen, safety_settings=_SAFETY_SETTINGS)


_PRIVACY_PREAMBLE = (
    "【重要・機密情報】これは個人の家族・資産情報です。"
    "モデル学習に使用しないでください。回答後にデータを保持・記録しないでください。\n\n"
)


def _safety_instructions() -> str:
    """非弁活動回避のためのプロンプト制約を返す"""
    from core.legal_safety import PROMPT_SAFETY_INSTRUCTIONS
    return PROMPT_SAFETY_INSTRUCTIONS


def diagnose_succession_gemini(
    family_summary: str,
    assets_summary: str,
    shares_summary: str,
    concerns: str = "",
) -> str:
    """
    Geminiで相続・事業承継リスクを診断し、最適な一手を提示する。
    無料枠の gemini-2.5-flash を使用。
    """
    api_key = _get_api_key()
    if not api_key:
        return (
            "❌ APIキーが設定されていません。\n\n"
            "環境変数 `GEMINI_API_KEY` または `GOOGLE_API_KEY` に\n"
            "Google AI Studio (https://aistudio.google.com/app/apikey) で取得した\n"
            "APIキーを設定してください。"
        )

    try:
        import google.generativeai as genai
    except ImportError:
        return (
            "❌ `google-generativeai` パッケージが未インストールです。\n\n"
            "次のコマンドでインストールしてください:\n"
            "```\npip install google-generativeai\n```"
        )

    concerns_block = f"\n\n【ユーザーの懸念事項】\n{concerns}" if concerns.strip() else ""

    prompt = _PRIVACY_PREAMBLE + _safety_instructions() + f"""

あなたは日本の相続・事業承継に**詳しい一般情報提供者**です（**弁護士・税理士ではありません**）。
以下の情報をもとに、リスクを推定し「最優先で検討すべき一般的なアクション」を提示してください。
個別事案への法的判断・代理・助言は行わないでください。

【家族構成】
{family_summary}

【資産・事業の状況】
{assets_summary}

【法定相続分】
{shares_summary}{concerns_block}

以下の形式で簡潔に回答してください:

## 🎯 リスク総合評価（一般的傾向）
- **レベル**: 高 / 中 / 低 （目安）
- **理由**: （1〜2文で簡潔に、「〜と考えられます」調で）

## ⚡ 最優先で検討すべき一般的なアクション
（具体的なアクションを1つだけ提示してください。「〜することが選択肢として考えられます」調で）

## 📋 補足情報（参考）
- **遺留分**: （配偶者・子の遺留分に関する一般的な注意点）
- **相続税対策**: （一般に活用できる特例・控除の参考情報）
- **どの専門家に相談すべきか**: （税理士／弁護士／司法書士のいずれが適しているか）

回答は日本語で、推定的表現（「〜と考えられます」「〜の可能性があります」）を使い、
最後に必ず「個別事案については専門家へのご相談が必要です」と明記してください。"""

    try:
        genai.configure(api_key=api_key)
        try:
            model = _new_model(genai, _MODEL_NAME)
            response = model.generate_content(prompt)
        except Exception:
            # 新モデルが利用不可な場合は安定版にフォールバック
            model = _new_model(genai, _FALLBACK_MODEL)
            response = model.generate_content(prompt)

        # 非弁活動回避: 統一フッターを付加
        from core.legal_safety import with_safety_footer
        return with_safety_footer(response.text or "")
    except Exception as e:
        return f"❌ Gemini API 呼び出し中にエラーが発生しました:\n\n`{str(e)}`"


# ─────────────────────────────────────────────────────────────────
# 音声→家族構成抽出（1ステップ）
# ─────────────────────────────────────────────────────────────────

_AUDIO_EXTRACT_PROMPT = _PRIVACY_PREAMBLE + """この音声を聞いて、話者が説明している家族関係・遺産情報を解析し、
以下のJSON形式のみで返してください（前置き・コードブロック・後書き不要、JSONオブジェクトのみ）:

{
  "transcript": "（音声の文字起こし全文）",
  "persons": [
    {
      "id": "p1",
      "name": "山田太郎",
      "gender": "male",
      "birth_year": 1950,
      "is_alive": false,
      "is_propositus": true,
      "assets_yen": 50000000,
      "has_business_shares": true,
      "is_renounced": false,
      "notes": ""
    }
  ],
  "relationships": [
    {"person1_id": "p1", "person2_id": "p2", "rel_type": "spouse"},
    {"person1_id": "p1", "person2_id": "p3", "rel_type": "parent_child"}
  ]
}

ルール:
- is_propositus=true は被相続人（亡くなった方・相続される側）のみ1名
- is_alive=false は故人
- rel_type は "spouse"（配偶者）または "parent_child"（person1が親→person2が子）
- gender は "male" / "female" / "unknown"
- birth_year・assets_yen が不明なら null / 0
- has_business_shares は自社株・非上場株を保有していれば true
- is_renounced は明確に「相続放棄した」と述べた場合のみ true"""


_TRANSCRIBE_PROMPT = _PRIVACY_PREAMBLE + """この音声を聞いて、話されている内容を**日本語で文字起こし**してください。
ルール:
- 文字起こしの本文のみを返してください（前置き・後書き・引用符・コードブロック不要）
- 話者が言った言葉をできるだけ忠実に書き起こす
- 句読点を適切に補い、読みやすくする
- 「えーと」「あのー」等のフィラーは省略可"""


_TEXT_EXTRACT_PROMPT_TMPL = _PRIVACY_PREAMBLE + """以下のテキストから家族関係を抽出してください。

テキスト:
{text}

以下のJSON形式のみで返してください（前置き・コードブロック不要、JSONオブジェクトのみ）:
{{
  "persons": [
    {{
      "id": "p1",
      "name": "山田太郎",
      "gender": "male",
      "birth_year": 1950,
      "is_alive": false,
      "is_propositus": true,
      "assets_yen": 50000000,
      "has_business_shares": true,
      "is_renounced": false,
      "notes": ""
    }}
  ],
  "relationships": [
    {{"person1_id": "p1", "person2_id": "p2", "rel_type": "spouse"}},
    {{"person1_id": "p1", "person2_id": "p3", "rel_type": "parent_child"}}
  ]
}}

ルール:
- is_propositus=true は被相続人（亡くなった方・相続される側）のみ1名
- is_alive=false は故人
- rel_type は "spouse"（配偶者）または "parent_child"（person1が親→person2が子）
- gender は "male" / "female" / "unknown"
- birth_year・assets_yen が不明なら null / 0
- has_business_shares は自社株・非上場株を保有していれば true
- is_renounced は明確に「相続放棄した」と述べた場合のみ true"""


def transcribe_audio(
    audio_bytes: bytes, mime_type: str = "audio/wav"
) -> Optional[str]:
    """
    音声を文字起こしのみ実行する（家族抽出はしない）。
    呼び出し側は audio_bytes を渡した後、変数を del して明示的に解放すること。
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        return None

    try:
        genai.configure(api_key=api_key)
        audio_part = {"mime_type": mime_type, "data": audio_bytes}

        try:
            model = _new_model(genai, _MODEL_NAME)
            response = model.generate_content([audio_part, _TRANSCRIBE_PROMPT])
        except Exception:
            model = _new_model(genai, _FALLBACK_MODEL)
            response = model.generate_content([audio_part, _TRANSCRIBE_PROMPT])

        return (response.text or "").strip() or None
    except Exception:
        return None


_IMAGE_EXTRACT_PROMPT = _PRIVACY_PREAMBLE + """この画像に含まれる家族関係・家系図・戸籍情報を解析し、
以下のJSON形式のみで家族構成を返してください（前置き・コードブロック不要、JSONオブジェクトのみ）:
{
  "persons": [
    {
      "id": "p1",
      "name": "山田太郎",
      "gender": "male",
      "birth_year": 1950,
      "is_alive": false,
      "is_propositus": true,
      "assets_yen": 50000000,
      "has_business_shares": true,
      "is_renounced": false,
      "notes": ""
    }
  ],
  "relationships": [
    {"person1_id": "p1", "person2_id": "p2", "rel_type": "spouse"},
    {"person1_id": "p1", "person2_id": "p3", "rel_type": "parent_child"}
  ]
}

ルール:
- is_propositus=true は被相続人（亡くなった方・相続される側）のみ1名
- is_alive=false は故人
- rel_type は "spouse"（配偶者）または "parent_child"（person1が親→person2が子）
- gender は "male" / "female" / "unknown"
- birth_year・assets_yen が不明なら null / 0
- has_business_shares は自社株・非上場株を保有していれば true"""


def extract_family_from_text_gemini(text: str) -> Optional[dict]:
    """テキストから家族構成を抽出（Gemini版）。失敗時は None（原因は get_last_error()）"""
    global last_error
    api_key = _get_api_key()
    if not api_key:
        last_error = "GEMINI_API_KEY が未設定です"
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        last_error = "google-generativeai パッケージが未インストールです"
        return None

    prompt = _TEXT_EXTRACT_PROMPT_TMPL.format(text=text)

    try:
        genai.configure(api_key=api_key)
        try:
            response = _new_model(genai, _MODEL_NAME).generate_content(prompt)
        except Exception:
            response = _new_model(genai, _FALLBACK_MODEL).generate_content(prompt)

        content = response.text or ""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            last_error = None
            return json.loads(json_match.group())
        last_error = "AIの応答からJSONを抽出できませんでした"
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"

    return None


def extract_family_from_image_gemini(image_bytes, mime_type: str = "image/jpeg") -> Optional[dict]:
    """
    画像から家族構成を抽出（Gemini版）。失敗時は None（原因は get_last_error()）。
    image_bytes は BytesIO または bytes を許容。呼び出し側は処理後に解放すること。
    """
    global last_error
    api_key = _get_api_key()
    if not api_key:
        last_error = "GEMINI_API_KEY が未設定です"
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        last_error = "google-generativeai パッケージが未インストールです"
        return None

    # BytesIO / bytes 両対応
    data = image_bytes.getvalue() if hasattr(image_bytes, "getvalue") else image_bytes
    image_part = {"mime_type": mime_type, "data": data}

    try:
        genai.configure(api_key=api_key)
        try:
            response = _new_model(genai, _MODEL_NAME).generate_content(
                [image_part, _IMAGE_EXTRACT_PROMPT]
            )
        except Exception:
            response = _new_model(genai, _FALLBACK_MODEL).generate_content(
                [image_part, _IMAGE_EXTRACT_PROMPT]
            )

        content = response.text or ""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            last_error = None
            return json.loads(json_match.group())
        last_error = "AIの応答からJSONを抽出できませんでした"
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"

    return None


def generate_will_draft_gemini(
    family_summary: str,
    assets_summary: str,
    distribution_intent: str,
) -> str:
    """
    自筆証書遺言の「雛形テンプレート」を生成する。
    弁護士法72条配慮: あくまで一般的な雛形であり、個別事案の助言は行わない。
    """
    api_key = _get_api_key()
    if not api_key:
        return "❌ APIキーが設定されていません。"

    try:
        import google.generativeai as genai
    except ImportError:
        return "❌ `google-generativeai` パッケージが未インストールです。"

    from core.legal_safety import PROMPT_SAFETY_INSTRUCTIONS, with_safety_footer

    prompt = (
        _PRIVACY_PREAMBLE
        + PROMPT_SAFETY_INSTRUCTIONS
        + f"""

あなたは日本の自筆証書遺言の**雛形テンプレート**を提供する一般情報提供者です。
**個別事案の法的判断・助言は行わず、必ず弁護士・公証人への相談を促すこと**。

【家族構成】
{family_summary}

【資産状況】
{assets_summary}

【遺言者の希望（参考）】
{distribution_intent if distribution_intent.strip() else "（特に指定なし — 一般的な雛形を提示してください）"}

以下の形式で出力してください:

## 📜 自筆証書遺言（雛形テンプレート）

```
遺言書

遺言者 ○○○○ は、本遺言書により次のとおり遺言する。

第1条（財産の特定と承継）
  遺言者は、下記の財産を ○○○○ に相続させる。
  記
  1. （財産の表示）
  ...

第2条（遺言執行者の指定）
  遺言者は、本遺言の遺言執行者として次の者を指定する。
  住所: ○○○○
  氏名: ○○○○

第3条（付言事項）
  （家族へのメッセージ等、任意）

令和○年○月○日

  住所: ○○○○○○
  氏名: ○○○○                印
```

## ⚠️ 自筆証書遺言の必須要件（民法968条）

- **全文・日付・氏名を自書**すること（パソコン・代筆は無効）
- **押印**すること（認印で可、ただし実印推奨）
- **加除・訂正**は変更場所を指示し、変更した旨を付記して署名押印が必要
- 財産目録は2019年改正により**パソコン作成可**（ただし各ページに署名押印）

## 📌 法務局保管制度のメリット（推奨）

- 紛失・偽造リスクを回避
- 検認手続き（家庭裁判所）が不要に
- 全国の遺言書保管所で **3,900円** で利用可能

## 🚨 必ず専門家にご相談ください

本雛形は一般的なテンプレートであり、以下のような個別事情がある場合は
**必ず弁護士・公証人にご相談ください**:

- 遺留分（民法1042条）への配慮が必要なケース
- 自社株・不動産・複雑な資産構成
- 相続人間に紛争の可能性があるケース
- 公正証書遺言の作成を検討する場合

最後に必ず「個別事案については弁護士・公証人へのご相談が必要です」と明記してください。"""
    )

    try:
        genai.configure(api_key=api_key)
        try:
            model = _new_model(genai, _MODEL_NAME)
            response = model.generate_content(prompt)
        except Exception:
            model = _new_model(genai, _FALLBACK_MODEL)
            response = model.generate_content(prompt)
        return with_safety_footer(response.text or "")
    except Exception as e:
        return f"❌ Gemini API 呼び出し中にエラーが発生しました:\n\n`{str(e)}`"


def extract_family_from_audio(
    audio_bytes: bytes, mime_type: str = "audio/wav"
) -> Optional[dict]:
    """
    音声バイナリを Gemini に送り、文字起こし＋家族構成抽出を1コールで実行する。
    呼び出し側は audio_bytes を渡した後、変数を del して明示的に解放すること。
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        return None

    try:
        genai.configure(api_key=api_key)

        # 音声はインライン送信（〜20MB程度まで対応）
        audio_part = {"mime_type": mime_type, "data": audio_bytes}

        try:
            model = _new_model(genai, _MODEL_NAME)
            response = model.generate_content([audio_part, _AUDIO_EXTRACT_PROMPT])
        except Exception:
            model = _new_model(genai, _FALLBACK_MODEL)
            response = model.generate_content([audio_part, _AUDIO_EXTRACT_PROMPT])

        content = response.text or ""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    return None
