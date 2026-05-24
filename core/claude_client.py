"""
Claude API連携モジュール
- テキスト・画像からの家族構成抽出
- 相続・事業承継診断
- セキュリティ: データは学習に利用されない旨をプロンプトに明記
"""
import os
import json
import re
from io import BytesIO
from typing import Optional
import base64

import anthropic


def _get_api_key() -> Optional[str]:
    """st.secrets → 環境変数 の順で ANTHROPIC_API_KEY を取得"""
    try:
        import streamlit as st
        try:
            val = st.secrets.get("ANTHROPIC_API_KEY")
            if val:
                return val
        except Exception:
            pass
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def _get_client() -> Optional[anthropic.Anthropic]:
    api_key = _get_api_key()
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def is_api_available() -> bool:
    return bool(_get_api_key())


# この指示をすべてのプロンプトの冒頭に付加する
_PRIVACY_PREAMBLE = (
    "【重要】ユーザーの個人情報を含む入力です。"
    "この情報はモデルの学習には一切使用しないでください。"
    "処理後のデータはいかなる形式でも保持・記録しないでください。\n\n"
)


def extract_family_from_text(text: str) -> Optional[dict]:
    """自然文から家族構成を抽出してJSONで返す"""
    client = _get_client()
    if not client:
        return None

    prompt = _PRIVACY_PREAMBLE + f"""以下のテキストから家族関係を抽出してください。

テキスト:
{text}

以下のJSON形式のみで返してください（説明文不要）:
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
      "notes": ""
    }}
  ],
  "relationships": [
    {{"person1_id": "p1", "person2_id": "p2", "rel_type": "spouse"}},
    {{"person1_id": "p1", "person2_id": "p3", "rel_type": "parent_child"}}
  ]
}}

ルール:
- is_propositus=true は被相続人（亡くなった方・相続される側）のみ
- is_alive=false は故人
- rel_type は "spouse"（配偶者）か "parent_child"（person1が親→person2が子）
- gender は "male" / "female" / "unknown"
- birth_year・assets_yen が不明なら null / 0
- has_business_shares は自社株・非上場株を保有していれば true"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return None


def extract_family_from_image(image_bytes: BytesIO, mime_type: str = "image/jpeg") -> Optional[dict]:
    """
    画像から家族構成を抽出してJSONで返す。
    呼び出し側は処理後に image_bytes を明示的に del すること。
    """
    client = _get_client()
    if not client:
        return None

    image_data = base64.standard_b64encode(image_bytes.getvalue()).decode("utf-8")

    prompt = _PRIVACY_PREAMBLE + """この画像に含まれる家族関係・家系図・戸籍情報を解析し、
以下のJSON形式のみで家族構成を抽出してください（説明文不要）:
{
  "persons": [...],
  "relationships": [...]
}
（フィールド仕様は標準的なものに従ってください: id, name, gender, birth_year,
 is_alive, is_propositus, assets_yen, has_business_shares, notes）"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        content = message.content[0].text
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass
    return None


def diagnose_succession(
    family_summary: str, assets_summary: str, shares_summary: str
) -> str:
    """相続・事業承継リスクを診断し最適な一手を提示する"""
    client = _get_client()
    if not client:
        return "ANTHROPIC_API_KEY が設定されていないため、AI診断は利用できません。"

    prompt = _PRIVACY_PREAMBLE + f"""あなたは相続・事業承継の専門家です。以下の情報をもとに診断してください。

【家族構成】
{family_summary}

【資産・事業の状況】
{assets_summary}

【法定相続分】
{shares_summary}

以下の形式で回答してください:

## リスク評価
- レベル: 高 / 中 / 低
- 理由:（簡潔に1〜2文）

## 今すぐ取り組むべき最優先の一手
（具体的なアクションを1つだけ、ズバリ提示してください）

## 注意事項
- 遺留分侵害のリスク
- 相続税の懸念点
- 専門家への相談推奨内容"""

    # 非弁活動回避: プロンプト制約を追加
    from core.legal_safety import PROMPT_SAFETY_INSTRUCTIONS, with_safety_footer
    prompt = PROMPT_SAFETY_INSTRUCTIONS + "\n\n" + prompt

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return with_safety_footer(message.content[0].text)
    except Exception as e:
        return f"診断中にエラーが発生しました: {str(e)}"
