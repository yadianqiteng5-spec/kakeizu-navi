"""
Claude API連携モジュール
- テキスト・画像からの家族構成抽出
- 相続・事業承継診断
- セキュリティ: データは学習に利用されない旨をプロンプトに明記

【堅牢性の設計】
- モデルIDは st.secrets / 環境変数 "ANTHROPIC_MODEL" で上書き可能
- 既定は複数候補のフォールバックチェーン（無効なモデルIDでも次を試す）
- エラーは握り潰さず last_error に保持し、UIで実原因を表示できるようにする
"""
import os
import json
import re
from io import BytesIO
from typing import Optional
import base64

import anthropic


# ─────────────────────────────────────────────────────────────
# 設定取得（st.secrets → 環境変数）
# ─────────────────────────────────────────────────────────────
def _get_secret(name: str) -> Optional[str]:
    try:
        import streamlit as st
        try:
            val = st.secrets.get(name)
            if val:
                return val
        except Exception:
            pass
    except Exception:
        pass
    return os.environ.get(name)


def _get_api_key() -> Optional[str]:
    return _get_secret("ANTHROPIC_API_KEY")


def _get_client() -> Optional[anthropic.Anthropic]:
    api_key = _get_api_key()
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def is_api_available() -> bool:
    return bool(_get_api_key())


# ─────────────────────────────────────────────────────────────
# モデル解決（上書き可能・フォールバックチェーン）
# ─────────────────────────────────────────────────────────────
# secrets/env の ANTHROPIC_MODEL があれば最優先。無くても下記候補を順に試す。
_FALLBACK_MODELS = [
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-20250929",
    "claude-3-7-sonnet-latest",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
]

_working_model: Optional[str] = None   # 一度成功したモデルを再利用（無駄な探索を避ける）
last_error: Optional[str] = None       # 直近のエラー（UI表示用）


def _candidate_models() -> list:
    override = _get_secret("ANTHROPIC_MODEL")
    models = []
    if override:
        models.append(override)
    models.extend(_FALLBACK_MODELS)
    # 重複除去（順序保持）
    seen, out = set(), []
    for m in models:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def get_last_error() -> Optional[str]:
    return last_error


def _create_message(client: anthropic.Anthropic, **kwargs):
    """
    モデル候補を順に試して messages.create を実行する。
    - モデルが見つからない(404)等は次の候補へフォールバック
    - 一度成功したモデルは _working_model に記憶して再利用
    - 全滅したら最後の例外を送出（呼び出し側で last_error に記録）
    """
    global _working_model, last_error

    # 成功実績モデルを先頭に、その後ろに全候補（重複除去）。
    # キャッシュ済みモデルが失敗しても同一呼び出し内で他候補へフォールバックする。
    ordered, seen = [], set()
    for m in ([_working_model] if _working_model else []) + _candidate_models():
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)
    models = ordered
    last_exc = None

    for model in models:
        if not model:
            continue
        try:
            msg = client.messages.create(model=model, **kwargs)
            _working_model = model      # 成功モデルを記憶
            last_error = None
            return msg
        except anthropic.NotFoundError as e:
            # モデルIDが無効 → 次の候補へ
            last_exc = e
            _working_model = None
            continue
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            # 認証・権限エラーはフォールバックしても無駄
            last_exc = e
            break
        except anthropic.APIStatusError as e:
            # その他のAPIエラー（レート制限・過負荷等）は次候補を試す価値あり
            last_exc = e
            continue
        except Exception as e:
            last_exc = e
            break

    last_error = f"{type(last_exc).__name__}: {last_exc}" if last_exc else "不明なエラー"
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("利用可能なモデルがありません")


def _parse_json_obj(content: str) -> Optional[dict]:
    json_match = re.search(r"\{[\s\S]*\}", content)
    if json_match:
        return json.loads(json_match.group())
    return None


# この指示をすべてのプロンプトの冒頭に付加する
_PRIVACY_PREAMBLE = (
    "【重要】ユーザーの個人情報を含む入力です。"
    "この情報はモデルの学習には一切使用しないでください。"
    "処理後のデータはいかなる形式でも保持・記録しないでください。\n\n"
)


def extract_family_from_text(text: str) -> Optional[dict]:
    """自然文から家族構成を抽出してJSONで返す。失敗時は None（原因は get_last_error()）"""
    global last_error
    client = _get_client()
    if not client:
        last_error = "ANTHROPIC_API_KEY が未設定です"
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
        message = _create_message(
            client,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text
        result = _parse_json_obj(content)
        if result is None:
            last_error = "AIの応答からJSONを抽出できませんでした"
        return result
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        return None


def extract_family_from_image(image_bytes: BytesIO, mime_type: str = "image/jpeg") -> Optional[dict]:
    """
    画像から家族構成を抽出してJSONで返す。
    呼び出し側は処理後に image_bytes を明示的に del すること。
    """
    global last_error
    client = _get_client()
    if not client:
        last_error = "ANTHROPIC_API_KEY が未設定です"
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
        message = _create_message(
            client,
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
        result = _parse_json_obj(content)
        if result is None:
            last_error = "AIの応答からJSONを抽出できませんでした"
        return result
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
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

    from core.legal_safety import PROMPT_SAFETY_INSTRUCTIONS, with_safety_footer
    prompt = PROMPT_SAFETY_INSTRUCTIONS + "\n\n" + prompt

    try:
        message = _create_message(
            client,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return with_safety_footer(message.content[0].text)
    except Exception as e:
        return f"診断中にエラーが発生しました: {type(e).__name__}: {e}"
