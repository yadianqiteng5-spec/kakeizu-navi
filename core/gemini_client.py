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
            model = genai.GenerativeModel(_MODEL_NAME)
            response = model.generate_content(prompt)
        except Exception:
            # 新モデルが利用不可な場合は安定版にフォールバック
            model = genai.GenerativeModel(_FALLBACK_MODEL)
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
            model = genai.GenerativeModel(_MODEL_NAME)
            response = model.generate_content([audio_part, _TRANSCRIBE_PROMPT])
        except Exception:
            model = genai.GenerativeModel(_FALLBACK_MODEL)
            response = model.generate_content([audio_part, _TRANSCRIBE_PROMPT])

        return (response.text or "").strip() or None
    except Exception:
        return None


def extract_family_from_text_gemini(text: str) -> Optional[dict]:
    """テキストから家族構成を抽出（Gemini版）"""
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        return None

    prompt = _TEXT_EXTRACT_PROMPT_TMPL.format(text=text)

    try:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel(_MODEL_NAME)
            response = model.generate_content(prompt)
        except Exception:
            model = genai.GenerativeModel(_FALLBACK_MODEL)
            response = model.generate_content(prompt)

        content = response.text or ""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    return None


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
            model = genai.GenerativeModel(_MODEL_NAME)
            response = model.generate_content([audio_part, _AUDIO_EXTRACT_PROMPT])
        except Exception:
            model = genai.GenerativeModel(_FALLBACK_MODEL)
            response = model.generate_content([audio_part, _AUDIO_EXTRACT_PROMPT])

        content = response.text or ""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    return None
