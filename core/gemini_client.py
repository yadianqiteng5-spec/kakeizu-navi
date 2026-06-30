"""
Gemini API連携モジュール（相続・事業承継診断）
- Secrets / 環境変数の GEMINI_API_KEY 等を読み込む（名前の大小ゆれに対応）
- 後継SDK **google-genai** を使用（旧 google-generativeai は EOL）
- 無料枠の gemini-2.5-flash を既定に、利用可能モデルを動的選択
- プライバシー指示・非弁制約は system_instruction で渡し、出力へ混入させない
"""
import os
import json
from typing import Optional

_MODEL_NAME = "gemini-2.5-flash"
_FALLBACK_MODEL = "gemini-2.0-flash"


# 受理するAPIキー名（大文字小文字のゆれにも対応）
_API_KEY_NAMES = ("GEMINI_API_KEY", "Gemini_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY")
_API_KEY_LOWER = ("gemini_api_key", "google_api_key", "google_genai_api_key")


def _get_api_key() -> Optional[str]:
    """
    APIキーを取得。st.secrets → 環境変数 の順。
    名前は GEMINI_API_KEY / Gemini_API_KEY / GOOGLE_API_KEY 等の大小ゆれを許容する。
    """
    # 1. Streamlit Secrets（明示名 → 大小無視スキャン）
    try:
        import streamlit as st
        for key in _API_KEY_NAMES:
            try:
                val = st.secrets.get(key)
                if val:
                    return val
            except Exception:
                pass
        try:
            for k in st.secrets:
                if str(k).lower() in _API_KEY_LOWER and st.secrets[k]:
                    return st.secrets[k]
        except Exception:
            pass
    except Exception:
        pass
    # 2. 環境変数（明示名 → 大小無視スキャン）
    for key in _API_KEY_NAMES:
        v = os.environ.get(key)
        if v:
            return v
    for k, v in os.environ.items():
        if str(k).lower() in _API_KEY_LOWER and v:
            return v
    return None


def _get_secret(name: str) -> Optional[str]:
    """st.secrets → 環境変数 の順で任意の設定値を取得（GEMINI_MODEL 等）。"""
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


def is_gemini_available() -> bool:
    """APIキーが設定されているかチェック"""
    return bool(_get_api_key())


# 直近のエラー（UI表示用・握り潰し防止）
last_error: Optional[str] = None


def get_last_error() -> Optional[str]:
    return last_error


# 相続は「死亡」を扱うため、セーフティフィルタの誤ブロックを防ぐ（事実ベースの法律情報）
def _safety_settings():
    from google.genai import types
    return [
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ]


_available_models: list = []            # list() で判明した利用可能モデル（診断用）
_available_fetched: bool = False        # モデル一覧の取得済みフラグ
_resolved_models: dict = {}             # prefer 別に解決したモデル名をキャッシュ


def available_models_str() -> str:
    """利用可能モデルの一覧文字列（エラー表示・診断用）"""
    if _available_models:
        names = [m.split("/")[-1] for m in _available_models]
        return ", ".join(names[:12])
    return "(取得できず)"


def _get_client():
    """google-genai Client を返す。"""
    from google import genai
    return genai.Client(api_key=_get_api_key())


def _pick_model(client, prefer: Optional[str] = None) -> str:
    """
    APIキーが実際に使えるモデルを client.models.list() で問い合わせて選ぶ。
    名前のズレ・モデル廃止で全滅しないための堅牢化。優先順位:
      1. secrets/env の GEMINI_MODEL
      2. 呼び出し側の希望(prefer)
      3. 新しめのflash系 → 旧flash → 任意のflash → 任意のgenerateContent対応
    """
    global _available_models, _available_fetched
    key = prefer or "_default_"
    if key in _resolved_models:
        return _resolved_models[key]

    override = _get_secret("GEMINI_MODEL")
    prefs = [override, prefer,
             "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite",
             "gemini-flash-latest", "gemini-2.0-flash-001"]

    # モデル一覧は一度だけ取得して共有
    if not _available_fetched:
        avail = []
        try:
            for m in client.models.list():
                acts = getattr(m, "supported_actions", None) or []
                if "generateContent" in acts:
                    avail.append(m.name)   # 例: "models/gemini-2.0-flash"
        except Exception:
            avail = []
        _available_models = avail
        _available_fetched = True
    available = _available_models

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
            _resolved_models[key] = hit
            return hit

    # 希望に合致しなければ、利用可能なflash系→任意を採用
    for a in available:
        if "flash" in a:
            _resolved_models[key] = a
            return a
    if available:
        _resolved_models[key] = available[0]
        return available[0]

    # list() が取れない場合の最終手段
    fallback = override or prefer or _MODEL_NAME
    _resolved_models[key] = fallback
    return fallback


def _run(contents, prefer: str = _MODEL_NAME, system_instruction: Optional[str] = None):
    """
    contents を generate_content に渡し response を返す。
    プライバシー/非弁制約は system_instruction で渡す（出力に混ざらない）。
    プライマリモデルが失敗したらフォールバックモデルを直接試す。失敗時は例外を送出。
    """
    from google.genai import types
    client = _get_client()
    cfg = types.GenerateContentConfig(
        safety_settings=_safety_settings(),
        system_instruction=system_instruction or None,
    )
    primary = _pick_model(client, prefer=prefer)
    try:
        return client.models.generate_content(model=primary, contents=contents, config=cfg)
    except Exception as primary_exc:
        # フォールバック: primary と異なる flash 系で再試行。失敗時は真因(primary_exc)を保全して送出
        fallback = next(
            (m for m in _available_models if "flash" in m and m != primary),
            _FALLBACK_MODEL,
        )
        if fallback == primary:
            raise
        try:
            return client.models.generate_content(model=fallback, contents=contents, config=cfg)
        except Exception:
            raise primary_exc


def _inline_part(data: bytes, mime_type: str):
    """画像・音声などのインラインバイナリを Part 化する。"""
    from google.genai import types
    return types.Part.from_bytes(data=data, mime_type=mime_type)


def _extract_json(content: str) -> Optional[dict]:
    """AI応答から最初のJSONオブジェクトを括弧の対応で抽出して dict を返す（失敗時 None）。
    末尾に説明文や ``` フェンスが付いても、最初の { から対応する } までで正しく切り出す
    （旧来の貪欲正規表現 `{...}` が JSON＋後続の日本語（波括弧含む）で壊れる問題を解消）。"""
    if not content:
        return None
    start = content.find("{")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(content)):
        c = content[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(content[start:i + 1])
                except Exception:
                    return None
    return None


def _strip_echo(text: str) -> str:
    """system_instruction（プライバシー/内部指示）がモデルにより稀に出力へ復唱される行を除去する。
    相続診断・遺言の本文には通常現れない内部フレーズのみを対象とし、本文は誤除去しない。"""
    bad = ("モデル学習", "回答後にデータを保持", "データを保持・記録", "内部指示",
           "これは個人の家族・資産情報")
    kept = [ln for ln in (text or "").split("\n") if not any(b in ln for b in bad)]
    return "\n".join(kept).lstrip("\n")


# system_instruction として渡す指示（出力には出さない）
_PRIVACY_PREAMBLE = (
    "これは個人の家族・資産情報です。モデル学習に使用しないでください。"
    "回答後にデータを保持・記録しないでください。"
)


def _advisory_system() -> str:
    """診断・遺言生成向け: プライバシー指示＋非弁活動回避制約。"""
    from core.legal_safety import PROMPT_SAFETY_INSTRUCTIONS
    return _PRIVACY_PREAMBLE + "\n\n" + PROMPT_SAFETY_INSTRUCTIONS


def diagnose_succession_gemini(
    family_summary: str,
    assets_summary: str,
    shares_summary: str,
    concerns: str = "",
    facts_summary: str = "",
) -> str:
    """
    Geminiで相続・事業承継リスクを診断し、最適な一手を提示する（gemini-2.5-flash）。
    facts_summary に自社エンジンの確定計算値を渡すと、一般論でなく
    その家族の数値に根拠づいた具体的な助言になる。
    （上位モデルを使う場合は Secrets/env の GEMINI_MODEL で指定可能）
    """
    if not _get_api_key():
        return (
            "❌ APIキーが設定されていません。\n\n"
            "環境変数 `GEMINI_API_KEY` または `GOOGLE_API_KEY` に\n"
            "Google AI Studio (https://aistudio.google.com/app/apikey) で取得した\n"
            "APIキーを設定してください。"
        )

    try:
        import google.genai  # noqa: F401
    except ImportError:
        return (
            "❌ `google-genai` パッケージが未インストールです。\n\n"
            "次のコマンドでインストールしてください:\n"
            "```\npip install google-genai\n```"
        )

    concerns = (concerns or "")[:2000]   # 入力長の上限
    concerns_block = f"\n\n【ユーザーの懸念事項】\n{concerns}" if concerns.strip() else ""
    facts_block = (
        f"\n\n【確定計算値（自社エンジンによる正確な数値・これを根拠に）】\n{facts_summary}"
        if facts_summary.strip() else ""
    )

    prompt = f"""あなたは日本の相続・事業承継に精通した一般情報提供者です（弁護士・税理士ではありません）。
下記の【確定計算値】を**必ず根拠として引用**し、一般論ではなく**この家族の数値・構成に即した、具体的で実行可能な助言**を、優先順位をつけて提示してください。
個別事案への法的判断・代理・断定的助言は避け、推定的表現（「〜と考えられます」「〜が選択肢として考えられます」）を用いてください。

【家族構成】
{family_summary}

【資産・事業の状況】
{assets_summary}

【法定相続分】
{shares_summary}{facts_block}{concerns_block}

以下の形式で、各項目とも**具体的な数値・人物名に触れながら**回答してください:

## 🎯 リスク総合評価
- **レベル**: 高 / 中 / 低（目安）
- **理由**: この家族固有の事情（誰に何が集中・税額・遺留分など）を挙げて1〜2文で

## ⚡ 最優先で検討すべき一手
最もインパクトの大きいアクションを**1つだけ**、なぜ最優先かの理由とともに。「〜することが選択肢として考えられます」調で。

## 📋 次に検討したいこと（2〜3点）
- **遺留分**: 上記の遺留分額に触れ、侵害リスクと配慮の方向性
- **相続税**: 上記の概算税額を踏まえ、活用しうる特例・控除（配偶者控除／小規模宅地／生命保険非課税枠／二次相続の観点）
- **事業承継**（自社株がある場合のみ）: 分散リスクと集中の方向性、事業承継税制の検討余地

## 👤 まず相談すべき専門家
税理士／弁護士／司法書士のうち、この家族で**最初に相談すべき専門家**を理由とともに1〜2名。

最後に必ず「個別事案については専門家へのご相談が必要です」と明記してください。"""

    try:
        response = _run(prompt, system_instruction=_advisory_system())
        # 非弁活動回避: 統一フッターを付加
        from core.legal_safety import with_safety_footer
        return with_safety_footer(_strip_echo(response.text or ""))
    except Exception as e:
        detail = f"\n\n`{e}`" if os.environ.get("KAKEIZU_DEBUG") else ""
        return "❌ AI生成に失敗しました。時間をおいて再試行するか、デモデータをお試しください。" + detail


# ── 音声文字起こしプロンプト ──────────────────────────────────────
_TRANSCRIBE_PROMPT = """この音声を聞いて、話されている内容を**日本語で文字起こし**してください。
ルール:
- 文字起こしの本文のみを返してください（前置き・後書き・引用符・コードブロック不要）
- 話者が言った言葉をできるだけ忠実に書き起こす
- 句読点を適切に補い、読みやすくする
- 「えーと」「あのー」等のフィラーは省略可"""


_TEXT_EXTRACT_PROMPT_TMPL = """以下のテキストから家族関係を抽出してください。

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
    音声を文字起こしのみ実行する（家族抽出はしない）。失敗原因は get_last_error() で取得可。
    呼び出し側は audio_bytes を渡した後、変数を del して明示的に解放すること。
    """
    global last_error
    if not _get_api_key():
        last_error = "GEMINI_API_KEY が未設定です"
        return None

    try:
        import google.genai  # noqa: F401
    except ImportError:
        last_error = "google-genai パッケージが未インストールです"
        return None

    try:
        audio_part = _inline_part(audio_bytes, mime_type)
        response = _run([audio_part, _TRANSCRIBE_PROMPT], system_instruction=_PRIVACY_PREAMBLE)
        last_error = None
        return (response.text or "").strip() or None
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        return None


_IMAGE_EXTRACT_PROMPT = """この画像に含まれる家族関係・家系図・戸籍情報を解析し、
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
    if not _get_api_key():
        last_error = "GEMINI_API_KEY が未設定です"
        return None

    try:
        import google.genai  # noqa: F401
    except ImportError:
        last_error = "google-genai パッケージが未インストールです"
        return None

    text = (text or "")[:8000]   # 入力長の上限（巨大入力によるトークンコスト/遅延の暴走を防止）
    prompt = _TEXT_EXTRACT_PROMPT_TMPL.format(text=text)

    try:
        response = _run(prompt, system_instruction=_PRIVACY_PREAMBLE)
        data = _extract_json(response.text or "")
        if data is not None:
            last_error = None
            return data
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
    if not _get_api_key():
        last_error = "GEMINI_API_KEY が未設定です"
        return None

    try:
        import google.genai  # noqa: F401
    except ImportError:
        last_error = "google-genai パッケージが未インストールです"
        return None

    # BytesIO / bytes 両対応
    data = image_bytes.getvalue() if hasattr(image_bytes, "getvalue") else image_bytes

    try:
        image_part = _inline_part(data, mime_type)
        response = _run([image_part, _IMAGE_EXTRACT_PROMPT], system_instruction=_PRIVACY_PREAMBLE)
        data = _extract_json(response.text or "")
        if data is not None:
            last_error = None
            return data
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
    if not _get_api_key():
        return "❌ APIキーが設定されていません。"

    try:
        import google.genai  # noqa: F401
    except ImportError:
        return "❌ `google-genai` パッケージが未インストールです。"

    from core.legal_safety import with_safety_footer

    distribution_intent = (distribution_intent or "")[:4000]   # 入力長の上限

    prompt = f"""あなたは日本の自筆証書遺言の**雛形テンプレート**を提供する一般情報提供者です。
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

    try:
        response = _run(prompt, system_instruction=_advisory_system())
        return with_safety_footer(_strip_echo(response.text or ""))
    except Exception as e:
        detail = f"\n\n`{e}`" if os.environ.get("KAKEIZU_DEBUG") else ""
        return "❌ AI生成に失敗しました。時間をおいて再試行するか、デモデータをお試しください。" + detail
