"""
家系図Navi - 相続・事業承継シミュレーター
ゼロ・リテンションアーキテクチャ: データはセッション内のみ、サーバーへの保存なし
"""
import streamlit as st
import base64
import os
from io import BytesIO
from pathlib import Path

# ── アイコン読み込み（PIL Image オブジェクトとして page_icon に渡す）───────
_ICON_DIR = Path(__file__).parent / "static"
_ICON_SVG_PATH = _ICON_DIR / "icon.svg"
_ICON_MASKABLE_PATH = _ICON_DIR / "icon_maskable.svg"


def _load_icon_for_page():
    """ファビコン用にPIL Imageを返す（SVGをPNGにレンダリング、失敗時は絵文字）"""
    try:
        from PIL import Image
        png_path = _ICON_DIR / "icon.png"
        if png_path.exists():
            return Image.open(png_path)
    except Exception:
        pass
    # フォールバック: 絵文字
    return "🌳"


# ── ページ設定 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="家系図Navi｜相続・事業承継シミュレーター",
    page_icon=_load_icon_for_page(),
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── PWAアイコン & manifest 注入（デスクトップにインストール時に反映） ────
def _inject_pwa_assets():
    """SVGアイコンをbase64で埋め込み、PWA manifestを動的生成して<head>に挿入"""
    try:
        if not _ICON_SVG_PATH.exists():
            return
        svg_data = _ICON_SVG_PATH.read_text(encoding="utf-8")
        svg_b64 = base64.b64encode(svg_data.encode("utf-8")).decode("ascii")
        svg_uri = f"data:image/svg+xml;base64,{svg_b64}"

        maskable_data = (
            _ICON_MASKABLE_PATH.read_text(encoding="utf-8")
            if _ICON_MASKABLE_PATH.exists() else svg_data
        )
        maskable_b64 = base64.b64encode(maskable_data.encode("utf-8")).decode("ascii")
        maskable_uri = f"data:image/svg+xml;base64,{maskable_b64}"

        # PNGアイコンも data URI で埋め込み（PWA互換性のため）
        png_icons = []
        for size_label, fname in [("192x192", "icon_192.png"), ("512x512", "icon_512.png")]:
            png_path = _ICON_DIR / fname
            if png_path.exists():
                png_b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
                png_icons.append({
                    "src": f"data:image/png;base64,{png_b64}",
                    "sizes": size_label,
                    "type": "image/png",
                    "purpose": "any maskable",
                })

        # PWA manifest を data URI として生成
        import json as _json
        manifest = {
            "name": "家系図Navi",
            "short_name": "家系図Navi",
            "description": "相続・事業承継シミュレーター",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#27AE60",
            "theme_color": "#16A085",
            "icons": png_icons + [
                {"src": svg_uri, "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
                {"src": maskable_uri, "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
            ],
        }
        manifest_b64 = base64.b64encode(
            _json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        manifest_uri = f"data:application/manifest+json;base64,{manifest_b64}"

        # JSスコープに渡すPNG URI（最初の2つを利用）
        png_uri_192 = png_icons[0]["src"] if len(png_icons) >= 1 else svg_uri
        png_uri_512 = png_icons[1]["src"] if len(png_icons) >= 2 else svg_uri
        icon_uri = png_uri_192
        apple_uri = png_uri_512
        icon_type = "image/png" if png_icons else "image/svg+xml"

        st.markdown(
            f"""<script>
            (function() {{
                const head = window.parent.document.head;
                const links = [
                    ['icon',             '{icon_uri}',     '{icon_type}'],
                    ['apple-touch-icon', '{apple_uri}',    '{icon_type}'],
                    ['shortcut icon',    '{icon_uri}',     '{icon_type}'],
                    ['manifest',         '{manifest_uri}', 'application/manifest+json'],
                ];
                links.forEach(([rel, href, type]) => {{
                    // 既存の同名linkを削除して新規挿入
                    head.querySelectorAll(`link[rel="${{rel}}"]`).forEach(el => el.remove());
                    const link = document.createElement('link');
                    link.setAttribute('rel', rel);
                    link.setAttribute('href', href);
                    if (type) link.setAttribute('type', type);
                    head.appendChild(link);
                }});
                // テーマカラー
                head.querySelectorAll('meta[name="theme-color"]').forEach(el => el.remove());
                const tc = document.createElement('meta');
                tc.setAttribute('name', 'theme-color');
                tc.setAttribute('content', '#16A085');
                head.appendChild(tc);
                // apple-mobile-web-app-title (iOSホーム画面表示名)
                head.querySelectorAll('meta[name="apple-mobile-web-app-title"]').forEach(el => el.remove());
                const title = document.createElement('meta');
                title.setAttribute('name', 'apple-mobile-web-app-title');
                title.setAttribute('content', '家系図Navi');
                head.appendChild(title);
            }})();
            </script>""",
            unsafe_allow_html=True,
        )
    except Exception:
        pass


_inject_pwa_assets()

MAX_FILE_MB = 5
MAX_LLM_CALLS = 8


# ── OGPメタタグ注入（SNSシェア時のプレビュー用） ─────────────────────────────
_OGP_TITLE = "家系図Navi｜相続・事業承継シミュレーター"
_OGP_DESC = "家族構成を入力するだけで法定相続分・遺留分・相続税概算・事業承継リスクをAIが診断。ゼロ・リテンション設計でデータは一切保存されません。"
_OGP_URL = "https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/"
st.markdown(
    f"""<script>
    (function() {{
        const head = window.parent.document.head;
        const metas = [
            ['og:title', '{_OGP_TITLE}'],
            ['og:description', '{_OGP_DESC}'],
            ['og:url', '{_OGP_URL}'],
            ['og:type', 'website'],
            ['twitter:card', 'summary_large_image'],
            ['twitter:title', '{_OGP_TITLE}'],
            ['twitter:description', '{_OGP_DESC}'],
        ];
        metas.forEach(([prop, content]) => {{
            if (head.querySelector(`meta[property="${{prop}}"], meta[name="${{prop}}"]`)) return;
            const m = document.createElement('meta');
            if (prop.startsWith('og:')) m.setAttribute('property', prop);
            else m.setAttribute('name', prop);
            m.setAttribute('content', content);
            head.appendChild(m);
        }});
    }})();
    </script>""",
    unsafe_allow_html=True,
)


# ── セッション初期化 ────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "consented":    False,
        "llm_count":    0,
        "family_tree":  None,
        "total_assets": 0,
        "step":         0,       # 0=入力, 1=確認修正, 2=結果
        "ai_raw_result": None,
        "edit_state":   None,
        "audio_transcript": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()
remaining_calls = MAX_LLM_CALLS - st.session_state.llm_count


# ── ヘルパー関数 ────────────────────────────────────────────────────────────

def _init_edit_state(raw: dict):
    """AI抽出結果を中間編集ステートへ展開する"""
    st.session_state.edit_state = {
        "persons": [dict(p) for p in raw.get("persons", [])],
        "relationships": [dict(r) for r in raw.get("relationships", [])],
    }


def _build_ft_from_edit_state():
    """edit_state から FamilyTree を構築して返す"""
    from core.family_tree import FamilyTree, Gender
    es = st.session_state.edit_state
    ft = FamilyTree()
    id_map: dict = {}
    gender_map = {
        "male": Gender.MALE, "female": Gender.FEMALE, "unknown": Gender.UNKNOWN,
    }
    for p in es["persons"]:
        new_id = ft.add_person(
            name=p.get("name", "不明"),
            gender=gender_map.get(p.get("gender", "unknown"), Gender.UNKNOWN),
            birth_year=p.get("birth_year"),
            is_alive=bool(p.get("is_alive", True)),
            is_propositus=bool(p.get("is_propositus", False)),
            assets_yen=int(p.get("assets_yen") or 0),
            has_business_shares=bool(p.get("has_business_shares", False)),
            is_renounced=bool(p.get("is_renounced", False)),
            died_simultaneously=bool(p.get("died_simultaneously", False)),
            notes=str(p.get("notes") or ""),
        )
        id_map[p["id"]] = new_id

    for r in es["relationships"]:
        p1 = id_map.get(r.get("person1_id", ""))
        p2 = id_map.get(r.get("person2_id", ""))
        rt = r.get("rel_type") or r.get("type", "")
        if p1 and p2:
            if rt == "spouse":
                ft.add_spouse(p1, p2)
            elif rt == "parent_child":
                adoption = r.get("adoption_type", "biological")
                ft.add_parent_child(p1, p2, adoption_type=adoption)
    return ft


def _sidebar():
    with st.sidebar:
        st.markdown("### 🌳 家系図Navi")
        st.markdown(
            """<div style="background:#27AE60;color:white;padding:6px 10px;
            border-radius:8px;font-size:11px;text-align:center;margin-bottom:8px;">
            ✅ <b>39ケース</b> 自動テスト済<br>
            <span style="font-size:10px;opacity:0.9;">民法・相続税法エッジケース対応</span>
            </div>""",
            unsafe_allow_html=True,
        )
        st.progress(
            remaining_calls / MAX_LLM_CALLS,
            text=f"AI解析残り: **{remaining_calls}/{MAX_LLM_CALLS}** 回",
        )
        if st.session_state.step == 2 and st.session_state.family_tree:
            st.markdown("---")
            if st.button("🔄 最初からやり直す", use_container_width=True):
                for k in ["step", "family_tree", "total_assets", "ai_raw_result", "edit_state"]:
                    st.session_state[k] = {
                        "step": 0, "family_tree": None, "total_assets": 0,
                        "ai_raw_result": None, "edit_state": None,
                    }.get(k)
                st.rerun()

        st.markdown("---")
        st.markdown("#### 📢 スポンサー広告")
        _ads = [
            ("💼 相続専門税理士に相談", "初回無料・全国対応"),
            ("📋 遺言書作成サポート", "弁護士費用0円〜"),
            ("🏢 事業承継コンサルティング", "専門家が無料診断"),
            ("🏦 相続ローン・資金調達", "最短翌日融資"),
        ]
        for label, sub in _ads:
            st.markdown(
                f"""<div style="background:#f8f9fa;padding:10px 12px;border-radius:8px;
                border:1px dashed #ccc;margin-bottom:8px;line-height:1.6;">
                <b style="font-size:13px;">{label}</b><br>
                <span style="font-size:12px;color:#555;">{sub}</span><br>
                <span style="font-size:11px;color:#bbb;">▶ 広告プレースホルダー</span>
                </div>""",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        st.caption("🔒 入力データはサーバーに一切保存されません。\nブラウザを閉じると即時に消去されます。")


_sidebar()

# ── ヘッダー ───────────────────────────────────────────────────────────────
st.title("🌳 家系図Navi")
st.markdown("**相続・事業承継シミュレーター** ｜ 家族構成を入力するだけで法定相続分と事業承継リスクを診断します。")

# ── 免責事項・同意 ─────────────────────────────────────────────────────────
with st.expander(
    "📋 免責事項・プライバシーポリシー（必ずお読みください）",
    expanded=not st.session_state.consented,
):
    from core.legal_safety import MAIN_DISCLAIMER_MD
    st.markdown(MAIN_DISCLAIMER_MD)

consented = st.checkbox(
    "上記の免責事項・プライバシーポリシーを読み、同意した上で利用します",
    value=st.session_state.consented,
)
st.session_state.consented = consented

if not consented:
    st.info("チェックを入れると、シミュレーターをご利用いただけます。")
    st.stop()

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# STEP 0: 入力フォーム
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.step == 0:
    st.subheader("📝 Step 1 ｜ 家族構成を入力")

    tab_text, tab_image, tab_audio = st.tabs([
        "💬 テキスト入力",
        "📷 画像アップロード",
        "🎤 音声入力（2ステップ：文字起こし→解析）",
    ])

    with tab_text:
        st.caption("家族の状況を自由に記述してください。AIが家族関係を自動解析します。")
        input_text = st.text_area(
            "家族構成・状況",
            height=170,
            placeholder=(
                "例：父の山田太郎（昭和20年生まれ）が昨年亡くなりました。\n"
                "配偶者の花子（昭和23年生まれ）は健在です。\n"
                "子供は長男・一郎（1970年生）、長女・二子（1972年生）、\n"
                "次男・三郎（1975年生、数年前に死亡）がおり、三郎には子・四郎がいます。\n"
                "遺産は自宅不動産（3,000万円）と預金2,000万円、会社の株式があります。"
            ),
            key="input_text_area",
        )

    uploaded = None
    with tab_image:
        st.caption(f"家系図・戸籍・メモ等の画像をアップロードしてください。（上限: {MAX_FILE_MB}MB）")
        uploaded = st.file_uploader(
            "画像ファイル（JPG / PNG）",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
            key="image_uploader",
        )
        if uploaded:
            if uploaded.size > MAX_FILE_MB * 1024 * 1024:
                st.error(
                    f"ファイルサイズ（{uploaded.size/1024/1024:.1f}MB）が"
                    f"上限の {MAX_FILE_MB}MB を超えています。"
                )
                uploaded = None
            else:
                st.success(f"✅ {uploaded.name}（{uploaded.size/1024:.0f} KB）")
                st.image(uploaded, caption="アップロード画像", use_column_width=True)

    # ── 音声入力タブ（2ステップ：①文字起こし → ②内容確認 → ③家族抽出）──────
    with tab_audio:
        st.caption(
            "マイクで家族関係を説明してください。\n"
            "**ステップ①** Geminiで文字起こし → **ステップ②** 内容を確認・編集 → **ステップ③** 家族構成を解析"
        )
        try:
            audio_input = st.audio_input(
                "録音（クリックして開始 / 再クリックで停止）",
                key="audio_input_widget",
            )
        except AttributeError:
            audio_input = None
            st.error(
                "`st.audio_input` を使用するには Streamlit 1.36 以上が必要です。\n\n"
                "次のコマンドでアップグレードしてください: `pip install -U streamlit`"
            )

        if audio_input is not None:
            from core.gemini_client import is_gemini_available
            st.audio(audio_input)
            audio_size_kb = len(audio_input.getvalue()) / 1024
            st.caption(f"録音サイズ: {audio_size_kb:.0f} KB")

            if not is_gemini_available():
                st.warning(
                    "Gemini APIキー（環境変数 `GEMINI_API_KEY` または `GOOGLE_API_KEY`）が"
                    "設定されていないため、音声解析は利用できません。"
                )
            else:
                # ── ステップ① 文字起こしボタン ─────────────────────────────
                transcribe_btn = st.button(
                    "🎙️ ステップ① 文字起こしする（Gemini）",
                    type="primary" if not st.session_state.audio_transcript else "secondary",
                    use_container_width=True,
                    disabled=remaining_calls <= 0,
                    key="transcribe_audio_btn",
                )

                if transcribe_btn:
                    from core.gemini_client import transcribe_audio
                    audio_bytes = audio_input.getvalue()
                    mime = getattr(audio_input, "type", None) or "audio/wav"

                    with st.spinner("Geminiが音声を文字起こし中...（10〜20秒）"):
                        transcript = transcribe_audio(audio_bytes, mime)

                    del audio_bytes  # 即時解放

                    if transcript:
                        st.session_state.audio_transcript = transcript
                        st.session_state.llm_count += 1
                        st.rerun()
                    else:
                        st.error(
                            "文字起こしに失敗しました。次をお試しください:\n"
                            "- もう少しゆっくり・はっきり話す\n"
                            "- 録音し直す（マイクの音量を確認）\n"
                            "- テキスト入力タブに切り替える"
                        )

        # ── ステップ② 文字起こし結果の確認・編集 → ステップ③ 家族抽出 ──────
        if st.session_state.audio_transcript:
            st.markdown("---")
            st.markdown("##### 📝 ステップ② 文字起こし結果（編集可能）")
            edited_transcript = st.text_area(
                "下記の内容を確認し、必要に応じて修正してください",
                value=st.session_state.audio_transcript,
                height=180,
                key="audio_transcript_editor",
            )
            st.session_state.audio_transcript = edited_transcript

            ac1, ac2 = st.columns([3, 1])
            with ac1:
                extract_btn = st.button(
                    "🔍 ステップ③ この内容から家族構成を解析する",
                    type="primary",
                    use_container_width=True,
                    disabled=(remaining_calls <= 0 or not edited_transcript.strip()),
                    key="extract_from_transcript_btn",
                )
            with ac2:
                clear_btn = st.button(
                    "🗑 クリア",
                    use_container_width=True,
                    key="clear_transcript_btn",
                )

            if clear_btn:
                st.session_state.audio_transcript = ""
                st.rerun()

            if extract_btn:
                from core.gemini_client import extract_family_from_text_gemini
                with st.spinner("Geminiが家族構成を解析中...（10〜20秒）"):
                    result = extract_family_from_text_gemini(edited_transcript)

                if result and result.get("persons"):
                    st.session_state.ai_raw_result = result
                    st.session_state.llm_count += 1
                    st.session_state.edit_state = None
                    st.session_state.audio_transcript = ""   # クリア
                    st.session_state.step = 1
                    st.rerun()
                else:
                    st.error(
                        "家族構成の抽出に失敗しました。\n"
                        "文字起こし結果に人物名・続柄・生年などを補足してから再度お試しください。"
                    )

    st.markdown("")
    c1, c2 = st.columns([1, 1])
    with c1:
        analyze_btn = st.button(
            "🔍 AIで解析する",
            type="primary",
            use_container_width=True,
            disabled=remaining_calls <= 0,
        )
    with c2:
        if remaining_calls <= 0:
            st.error(f"本セッションのAI解析上限（{MAX_LLM_CALLS}回）に達しました。ページをリロードしてください。")

    # ── 典型事例集（ワンクリック体験） ─────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📚 典型事例集 — ワンクリックで体験")
    st.caption("実際の相続でよくある8つのパターン。AIキー不要で全機能を試せます。")

    SCENARIOS = [
        ("standard",           "👨‍👩‍👧‍👦 標準ケース",       "配偶者+子3名（うち1名先死亡で代襲）", 50_000_000),
        ("no_children",        "💑 子なし夫婦",            "配偶者+両親（直系尊属が相続）",         60_000_000),
        ("siblings_only",      "👫 子なし・親も他界",        "配偶者+兄弟姉妹（遺留分発生せず）",     40_000_000),
        ("half_blood",         "🧬 半血兄弟あり",           "全血:半血 = 2:1 で按分",            30_000_000),
        ("adoption",           "📜 普通養子あり",           "実子2+養子2（養子算入制限が発動）",    100_000_000),
        ("special_adoption",   "🎗 特別養子",              "実親との関係終了・養親からのみ相続",    40_000_000),
        ("simultaneous_death", "⚡ 同時死亡（事故）",         "親子同時死亡 → 孫が代襲",            80_000_000),
        ("renounce",           "🚫 相続放棄",              "債務超過で配偶者+長男が放棄",          50_000_000),
    ]
    sc_cols = st.columns(4)
    for i, (sid, label, desc, assets) in enumerate(SCENARIOS):
        with sc_cols[i % 4]:
            if st.button(
                f"**{label}**\n\n_{desc}_",
                key=f"scenario_{sid}",
                use_container_width=True,
                help=f"相続財産: {assets//10000:,}万円のシナリオで体験",
            ):
                from core.family_tree import FamilyTree
                st.session_state.family_tree = FamilyTree.create_scenario(sid)
                st.session_state.total_assets = assets
                st.session_state.step = 2
                st.rerun()

    # ── AI解析ボタン（Step 3: 実API呼び出し）──────────────────────────────
    if analyze_btn:
        has_text = bool(st.session_state.get("input_text_area", "").strip())
        has_image = uploaded is not None

        if not has_text and not has_image:
            st.error("テキストまたは画像を入力してください。")
        else:
            from core.claude_client import (
                is_api_available,
                extract_family_from_text,
                extract_family_from_image,
            )

            if not is_api_available():
                st.error(
                    "ANTHROPIC_API_KEY が設定されていません。\n"
                    "環境変数に設定してから再起動するか、「デモデータで体験」をご利用ください。"
                )
                st.stop()

            result = None
            with st.spinner("AIが家族関係を解析中...（10〜30秒かかる場合があります）"):
                # テキストから抽出
                if has_text:
                    text_val = st.session_state.get("input_text_area", "")
                    result = extract_family_from_text(text_val)

                # 画像から抽出（テキスト解析が失敗した場合、または画像のみの場合）
                if result is None and has_image:
                    ext = uploaded.name.rsplit(".", 1)[-1].lower()
                    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
                    image_bytes = BytesIO(uploaded.read())   # オンメモリのみ
                    result = extract_family_from_image(image_bytes, mime)
                    image_bytes.close()
                    del image_bytes                           # 即時解放

            if result and result.get("persons"):
                st.session_state.ai_raw_result = result
                st.session_state.llm_count += 1
                st.session_state.edit_state = None           # 前回の編集状態をリセット
                st.session_state.step = 1
                st.rerun()
            else:
                st.error(
                    "解析に失敗しました。以下をお試しください:\n"
                    "- テキストをより具体的に記述する\n"
                    "- 画像を鮮明なものに変える\n"
                    "- テキストと画像を両方入力する"
                )


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: AI解析結果の確認・修正（Step 4）
# ═══════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 1:

    # edit_state の初期化（初回のみ）
    if st.session_state.edit_state is None:
        raw = st.session_state.get("ai_raw_result") or {}
        _init_edit_state(raw)

    es = st.session_state.edit_state

    st.subheader("✅ Step 2 ｜ AI解析結果の確認・修正")
    st.info(
        "AIが抽出した家族情報を確認し、誤りがあれば修正してから計算に進んでください。\n"
        "**★被相続人** を必ず 1名だけチェックしてください。"
    )

    # ── 人物一覧（編集可能） ────────────────────────────────────────────────
    st.markdown("#### 👥 人物一覧")

    del_person_idx = None
    for i, person in enumerate(es["persons"]):
        status = "存命" if person.get("is_alive", True) else "故人"
        flag = " ★被相続人" if person.get("is_propositus") else ""
        with st.expander(f"**{person.get('name', '不明')}**（{status}{flag}）", expanded=(i == 0)):
            col_l, col_r = st.columns(2)
            with col_l:
                person["name"] = st.text_input(
                    "氏名", value=person.get("name", ""), key=f"p_name_{i}"
                )
                g_opts = ["male", "female", "unknown"]
                g_val = person.get("gender", "unknown")
                g_idx = g_opts.index(g_val) if g_val in g_opts else 2
                person["gender"] = st.selectbox(
                    "性別", g_opts, index=g_idx,
                    format_func=lambda x: {"male": "男性", "female": "女性", "unknown": "不明"}[x],
                    key=f"p_gender_{i}",
                )
                birth_str = st.text_input(
                    "生年（西暦）",
                    value=str(person["birth_year"]) if person.get("birth_year") else "",
                    placeholder="例: 1950",
                    key=f"p_birth_{i}",
                )
                person["birth_year"] = int(birth_str) if birth_str.strip().isdigit() else None

            with col_r:
                person["is_alive"] = st.checkbox(
                    "存命（チェックを外すと故人）",
                    value=bool(person.get("is_alive", True)),
                    key=f"p_alive_{i}",
                )
                person["is_propositus"] = st.checkbox(
                    "★ 被相続人（相続の起点）",
                    value=bool(person.get("is_propositus", False)),
                    key=f"p_prop_{i}",
                )
                assets_man = int(person.get("assets_yen") or 0) // 10000
                assets_new = st.number_input(
                    "保有資産（万円）", min_value=0, value=assets_man, step=100,
                    key=f"p_assets_{i}",
                )
                person["assets_yen"] = assets_new * 10000
                person["has_business_shares"] = st.checkbox(
                    "自社株・非上場株を保有",
                    value=bool(person.get("has_business_shares", False)),
                    key=f"p_biz_{i}",
                )
                person["is_renounced"] = st.checkbox(
                    "相続放棄（枝ごと除外・代襲も発生しない）",
                    value=bool(person.get("is_renounced", False)),
                    key=f"p_renounced_{i}",
                )
                person["died_simultaneously"] = st.checkbox(
                    "被相続人と同時死亡（民法32条の2推定）",
                    value=bool(person.get("died_simultaneously", False)),
                    key=f"p_simul_{i}",
                    help="同時死亡推定が働く場合、相互に相続権はないが代襲は発生します。",
                )
                if person["died_simultaneously"]:
                    person["is_alive"] = False

            person["notes"] = st.text_input(
                "備考", value=str(person.get("notes") or ""), key=f"p_notes_{i}"
            )

            if st.button(f"この人物を削除", key=f"del_p_{i}", type="secondary"):
                del_person_idx = i

    if del_person_idx is not None:
        es["persons"].pop(del_person_idx)
        st.rerun()

    if st.button("＋ 人物を追加", key="add_person"):
        es["persons"].append({
            "id": f"p_new_{len(es['persons'])}",
            "name": "新しい人物",
            "gender": "unknown",
            "birth_year": None,
            "is_alive": True,
            "is_propositus": False,
            "assets_yen": 0,
            "has_business_shares": False,
            "is_renounced": False,
            "notes": "",
        })
        st.rerun()

    st.divider()

    # ── 家族関係（確認・削除可能） ──────────────────────────────────────────
    st.markdown("#### 🔗 家族関係")
    id_to_name = {p["id"]: p.get("name", p["id"]) for p in es["persons"]}

    del_rel_idx = None
    if not es["relationships"]:
        st.caption("関係が登録されていません。")
    for i, rel in enumerate(es["relationships"]):
        p1n = id_to_name.get(rel.get("person1_id", ""), "不明")
        p2n = id_to_name.get(rel.get("person2_id", ""), "不明")
        rt = rel.get("rel_type") or rel.get("type", "")
        rt_label = "配偶者" if rt == "spouse" else "親→子"

        if rt == "parent_child":
            col_r1, col_r2, col_r3 = st.columns([4, 2, 1])
            with col_r1:
                st.write(f"　**{p1n}** ←{rt_label}→ **{p2n}**")
            with col_r2:
                adoption_opts = ["biological", "regular_adoption", "special_adoption"]
                adoption_labels = {
                    "biological": "実子",
                    "regular_adoption": "普通養子",
                    "special_adoption": "特別養子",
                }
                cur_adoption = rel.get("adoption_type", "biological")
                if cur_adoption not in adoption_opts:
                    cur_adoption = "biological"
                rel["adoption_type"] = st.selectbox(
                    "養子区分",
                    adoption_opts,
                    index=adoption_opts.index(cur_adoption),
                    format_func=lambda x: adoption_labels[x],
                    key=f"adopt_{i}",
                    label_visibility="collapsed",
                )
            with col_r3:
                if st.button("削除", key=f"del_r_{i}"):
                    del_rel_idx = i
        else:
            col_r1, col_r2 = st.columns([5, 1])
            with col_r1:
                st.write(f"　**{p1n}** ←{rt_label}→ **{p2n}**")
            with col_r2:
                if st.button("削除", key=f"del_r_{i}"):
                    del_rel_idx = i

    if del_rel_idx is not None:
        es["relationships"].pop(del_rel_idx)
        st.rerun()

    st.divider()

    # ── アクションボタン ────────────────────────────────────────────────────
    ca, cb = st.columns(2)
    with ca:
        if st.button("← 入力に戻る", use_container_width=True):
            st.session_state.step = 0
            st.session_state.edit_state = None
            st.rerun()
    with cb:
        if st.button("この内容で計算する →", type="primary", use_container_width=True):
            # バリデーション
            propositus_count = sum(
                1 for p in es["persons"] if p.get("is_propositus")
            )
            if not es["persons"]:
                st.error("人物情報がありません。")
            elif propositus_count == 0:
                st.error("★被相続人を1名設定してください。")
            elif propositus_count > 1:
                st.error("★被相続人は1名のみ設定してください。")
            else:
                ft = _build_ft_from_edit_state()
                assets_total = sum(
                    int(p.get("assets_yen") or 0)
                    for p in es["persons"] if p.get("is_propositus")
                )
                st.session_state.family_tree = ft
                st.session_state.total_assets = assets_total
                st.session_state.step = 2
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: 結果表示
# ═══════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    ft = st.session_state.family_tree
    if not ft or ft.is_empty():
        st.error("データが見つかりません。")
        if st.button("最初からやり直す"):
            st.session_state.step = 0
            st.rerun()
        st.stop()

    propositus_id = ft.get_propositus()
    if not propositus_id:
        st.warning("被相続人が設定されていません。")
        st.stop()

    from core.inheritance import (
        calculate_legal_shares,
        calculate_legitimes,
        format_shares_table,
        get_business_risks,
        get_inheritance_tax_estimate,
        count_tax_legal_heirs,
    )

    shares, explanation = calculate_legal_shares(ft, propositus_id)
    num_heirs = len(shares)
    tax_heir_info = count_tax_legal_heirs(ft, propositus_id)
    num_tax_heirs = tax_heir_info["total"]
    legitime_info = calculate_legitimes(ft, propositus_id)

    # ── 3-1. 家系図 ──────────────────────────────────────────────────────────
    st.subheader("🌳 家系図")
    col_g, col_l = st.columns([3, 1])
    with col_g:
        st.graphviz_chart(ft.to_dot(), use_container_width=True)
    with col_l:
        st.markdown("""
**凡例**
- 🟡 金 = 被相続人
- 🔵 青 = 男性（存命）
- 🩷 ピンク = 女性（存命）
- ⚫ グレー = 故人
- 赤線 = 婚姻
- 黒矢印 = 親子
        """)

    st.divider()

    # ── 3-2. 法定相続分 ──────────────────────────────────────────────────────
    st.subheader("💴 法定相続分シミュレーション")

    c1, c2 = st.columns([2, 3])
    with c1:
        total_man = st.number_input(
            "相続財産総額（万円）",
            min_value=0,
            value=st.session_state.total_assets // 10000,
            step=100,
            help="不動産・預金・有価証券等の合計",
        )
        st.session_state.total_assets = total_man * 10000
    with c2:
        if total_man > 0:
            st.metric("相続財産総額", f"{total_man:,} 万円")

    st.markdown(explanation)

    rows = format_shares_table(shares, ft, st.session_state.total_assets)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if total_man > 0 and shares:
        try:
            import plotly.graph_objects as go
            fig = go.Figure(data=[go.Pie(
                labels=[r["氏名"] for r in rows],
                values=[float(shares[pid]) for pid in shares],
                hole=0.35,
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{percent}<extra></extra>",
            )])
            fig.update_layout(
                title=f"法定相続分の内訳（総額: {total_man:,} 万円）",
                margin=dict(t=50, b=20, l=20, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.info("円グラフには plotly が必要です: pip install plotly")

    st.divider()

    # ── 3-2.5. 遺留分 ────────────────────────────────────────────────────────
    st.subheader("⚖️ 遺留分（民法1042条以下）")
    st.markdown(legitime_info["rule"])

    if not legitime_info["has_legitime"]:
        st.info(
            "**遺留分は発生しません。**\n\n"
            "遺言書で遺産分割の指定をしても、遺留分侵害額請求のリスクはありません。"
        )
    else:
        legitime_rows = []
        total = st.session_state.total_assets
        for hid, frac in legitime_info["individual"].items():
            person = ft.persons.get(hid)
            if not person:
                continue
            row = {
                "氏名": person.name,
                "個別遺留分": f"{frac.numerator}/{frac.denominator}" if frac > 0 else "—",
                "割合": f"{float(frac)*100:.2f}%" if frac > 0 else "—",
            }
            if total > 0:
                if frac > 0:
                    row["最低保障額"] = f"¥{int(float(frac) * total):,}"
                else:
                    row["最低保障額"] = "—（遺留分なし）"
            legitime_rows.append(row)
        st.dataframe(legitime_rows, use_container_width=True, hide_index=True)
        st.caption(
            "💡 **遺留分**とは、遺言の内容にかかわらず一定の相続人に最低限保障される取り分です。"
            "遺言書を作成する際は、この金額を侵害しないことが選択肢として考えられます。"
            "侵害された場合、相続人は遺留分侵害額請求を行うことができます（民法1046条）。"
        )

    st.divider()

    # ── 3-3. 相続税の概算 ─────────────────────────────────────────────────────
    if st.session_state.total_assets > 0:
        st.subheader("📊 相続税の概算（参考値）")
        tax = get_inheritance_tax_estimate(
            shares, st.session_state.total_assets, num_heirs, num_tax_heirs
        )
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric(
            "基礎控除額",
            f"{tax['basic_deduction']//10000:,} 万円",
            f"3,000万 + 600万×{num_tax_heirs}人",
        )
        tc2.metric("課税遺産総額", f"{tax['taxable_estate']//10000:,} 万円")
        tc3.metric(
            "相続税概算（参考）", f"{tax['estimated_tax']//10000:,} 万円",
            help="相続税法16条準拠の正規計算（速算表使用・国税庁公表値と一致）",
        )

        if num_heirs != num_tax_heirs:
            st.warning(
                f"⚠️ **養子算入制限の適用**（相続税法15条2項）\n\n"
                f"民法上の法定相続人は {num_heirs} 名ですが、相続税の基礎控除算定上は "
                f"{num_tax_heirs} 名としてカウントされます。{tax_heir_info['note']}\n\n"
                "📌 **正確には**「相続税の総額」計算でも税法上の法定相続人数（養子算入後）で再按分するため、"
                "本シミュレーションの税額は **若干過少評価**となる可能性があります。"
                "実際の税額は税理士による精密試算が必要です。"
            )
        elif tax_heir_info["note"] != "養子なし":
            st.info(f"ℹ️ {tax_heir_info['note']}")

        st.caption(
            "※ 概算値です。実際は配偶者控除・債務控除等により大きく異なります。"
            "必ず税理士にご相談ください。"
        )

        # ── 3-3-b. 小規模宅地等の特例（任意入力で減額シミュレーション） ────
        with st.expander("🏠 小規模宅地等の特例を試算する（任意）", expanded=False):
            st.caption(
                "被相続人の宅地を相続する場合、要件を満たせば**最大80%減額**できる特例です"
                "（租税特別措置法69条の4）。簡易シミュレーションを行えます。"
            )
            sl_c1, sl_c2, sl_c3 = st.columns(3)
            with sl_c1:
                land_type = st.selectbox(
                    "宅地区分",
                    ["none", "residential", "business", "rental"],
                    format_func=lambda x: {
                        "none": "適用なし",
                        "residential": "特定居住用（80%減・330㎡）",
                        "business":    "特定事業用（80%減・400㎡）",
                        "rental":      "貸付事業用（50%減・200㎡）",
                    }[x],
                    key="land_type",
                )
            with sl_c2:
                land_value_man = st.number_input(
                    "宅地の相続税評価額（万円）", min_value=0, value=0, step=100,
                    key="land_value",
                )
            with sl_c3:
                area_sqm = st.number_input(
                    "宅地面積（㎡）", min_value=0.0, value=0.0, step=10.0,
                    key="area_sqm",
                )

            if land_type != "none" and land_value_man > 0 and area_sqm > 0:
                from core.inheritance import calculate_small_residential_deduction
                ssd = calculate_small_residential_deduction(
                    land_type, land_value_man * 10000, area_sqm
                )
                if ssd["applicable"]:
                    rc1, rc2, rc3 = st.columns(3)
                    rc1.metric("適用前の評価額", f"{land_value_man:,} 万円")
                    rc2.metric(
                        "減額される金額",
                        f"-{ssd['reduced_amount']//10000:,} 万円",
                        f"{int(ssd['reduction_rate']*100)}%減",
                    )
                    rc3.metric(
                        "適用後の評価額",
                        f"{ssd['after_deduction']//10000:,} 万円",
                    )
                    st.success(f"✅ {ssd['rule']}")
                    # 相続税への影響を再計算
                    new_total = max(
                        0, st.session_state.total_assets - ssd["reduced_amount"]
                    )
                    new_tax = get_inheritance_tax_estimate(
                        shares, new_total, num_heirs, num_tax_heirs
                    )
                    st.info(
                        f"💡 **特例適用後の相続税概算**: "
                        f"{new_tax['estimated_tax']//10000:,} 万円 "
                        f"（適用前: {tax['estimated_tax']//10000:,} 万円、"
                        f"**{(tax['estimated_tax']-new_tax['estimated_tax'])//10000:,} 万円**の節税）"
                    )
                    if area_sqm > ssd["limit_sqm"]:
                        st.warning(
                            f"⚠️ 宅地面積が上限（{ssd['limit_sqm']:.0f}㎡）を超えるため、"
                            f"超過部分には特例が適用されません。"
                        )
            st.caption(
                "※ 本特例には「相続開始前から居住・事業に使用」「相続後一定期間の継続利用」等の"
                "厳格な要件があります。適用可否は必ず税理士に確認してください。"
            )

        st.divider()

    # ── 3-3-c. 配偶者居住権の説明（2020年4月施行・民法1028条以下） ──────────
    spouse_id_for_dwelling = ft.get_spouse(propositus_id)
    if spouse_id_for_dwelling and spouse_id_for_dwelling in shares:
        with st.expander("🏡 配偶者居住権について（民法1028条以下）", expanded=False):
            st.markdown("""
**配偶者居住権**は2020年4月施行の制度で、配偶者が自宅に住み続けながら
他の財産も相続しやすくする選択肢として考えられます。

#### 📌 制度の概要

| 項目 | 内容 |
|---|---|
| **配偶者居住権**（民法1028条） | 配偶者が**終身**または**一定期間**、自宅に無償で居住できる権利 |
| **配偶者短期居住権**（民法1037条） | 遺産分割完了まで（最低6か月）、無償で居住できる権利。自動的に発生 |
| **取得方法** | 遺産分割協議／遺言書／家庭裁判所の審判 |
| **登記** | 配偶者居住権は**登記が対抗要件**（所有者と共同申請） |

#### 💡 メリット

- 配偶者は**自宅に住み続けられる**まま、預貯金など他の財産も多く相続できる
- 居住権は配偶者の**一身専属権**で譲渡不可 → 子（所有権者）への将来の承継が確定
- 居住権の評価額は**所有権より低い**ため、配偶者の相続財産配分の負担が軽くなる

#### ⚠️ 注意点

- 居住建物の**所有権は別の相続人**（通常は子）が取得する構造
- 配偶者死亡時に居住権は消滅 → 子が完全な所有権を取得（**二次相続対策**にも有効）
- 評価方法は複雑（建物の耐用年数・配偶者の平均余命などから算定）

#### 🎯 こんなケースで検討推奨

- 自宅が遺産の大半を占め、配偶者が住居を確保したいケース
- 配偶者と子の関係が良好でなく、所有権を分離したいケース
- 二次相続（配偶者死亡時）の相続税負担を抑えたいケース

> 個別事案での適否・評価額算定は、**必ず弁護士・税理士にご相談ください**。
            """)
        st.divider()

    # ── 3-3-d. 二次相続シミュレーション（配偶者がいる場合） ──────────────────
    if spouse_id_for_dwelling and spouse_id_for_dwelling in shares \
            and st.session_state.total_assets > 0:
        st.subheader("🔄 二次相続シミュレーション")
        st.caption(
            "一次相続（被相続人 → 配偶者・子）で配偶者控除を使い切ると一次の税は安くなりますが、"
            "**配偶者死亡時（二次相続）の税負担が大きく**なります。最適な配分を比較します。"
        )

        from core.inheritance import calculate_secondary_inheritance
        # 子の数を算出
        children_count = sum(
            1 for hid in shares
            if hid in set(ft.get_legal_children(propositus_id))
            and hid != spouse_id_for_dwelling
        )
        if children_count == 0:
            # 代襲相続人を孫として数える
            children_count = max(1, len(shares) - 1)

        sec_col1, sec_col2 = st.columns([1, 2])
        with sec_col1:
            spouse_own_man = st.number_input(
                "配偶者の固有財産（万円）",
                min_value=0, value=0, step=100,
                key="spouse_own_assets",
                help="配偶者自身が既に保有している財産。二次相続で加算されます。",
            )
        with sec_col2:
            st.caption(
                f"対象子数: **{children_count}名** "
                f"／ 一次相続財産: **{st.session_state.total_assets//10000:,}万円**"
            )

        sec_result = calculate_secondary_inheritance(
            primary_total_yen=st.session_state.total_assets,
            num_children=children_count,
            spouse_own_assets_yen=spouse_own_man * 10000,
        )

        if sec_result["scenarios"]:
            sec_rows = []
            for sc in sec_result["scenarios"]:
                sec_rows.append({
                    "シナリオ": sc["label"],
                    "配偶者取得額": f"{sc['primary_spouse_amount']//10000:,} 万円",
                    "一次相続税": f"{sc['primary_tax']//10000:,} 万円",
                    "二次相続税": f"{sc['secondary_tax']//10000:,} 万円",
                    "合計税額": f"**{sc['total_tax']//10000:,} 万円**",
                })
            st.dataframe(sec_rows, use_container_width=True, hide_index=True)

            st.success(
                f"🏆 **最も税負担が軽いシナリオ**: {sec_result['best_label']}"
                f"（最大シナリオとの差額: **{sec_result['best_savings']//10000:,}万円**）"
            )
            st.caption(
                "💡 配偶者控除（相続税法19条の2）は「法定相続分」または「1.6億円」のいずれか多い方まで非課税。"
                "ただし配偶者が多く相続すると二次相続で子の税負担が増えるため、**バランスが重要**です。"
                "※ 本シミュレーションは概算であり、実際は配偶者の余命・物価変動・他の控除等を考慮した精密な試算が必要です。"
            )
        st.divider()

    # ── 3-3-e. 生前贈与シミュレーション ──────────────────────────────────────
    if st.session_state.total_assets > 0:
        with st.expander("🎁 生前贈与シミュレーション（暦年贈与 vs 相続時精算課税）", expanded=False):
            st.caption(
                "毎年計画的に贈与することで相続財産を圧縮し、相続税を抑える戦略です。"
                "2024年改正後の制度に基づいて比較します。"
            )
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                gift_annual_man = st.number_input(
                    "1人あたり年間贈与額（万円）",
                    min_value=0, value=110, step=10,
                    key="gift_annual",
                    help="110万円までは暦年贈与で非課税",
                )
            with gc2:
                gift_years = st.number_input(
                    "贈与期間（年）",
                    min_value=1, max_value=30, value=10, step=1,
                    key="gift_years",
                )
            with gc3:
                gift_recipients = st.number_input(
                    "受贈者数（人）",
                    min_value=1, value=max(1, children_count if 'children_count' in dir() else 2),
                    step=1, key="gift_recipients",
                )

            # 推定される相続税の限界税率（簡易判定）
            est_rate = 0.10
            for threshold, rate in [(50_000_000, 0.20), (100_000_000, 0.30),
                                    (200_000_000, 0.40), (300_000_000, 0.45)]:
                if st.session_state.total_assets > threshold:
                    est_rate = rate

            if gift_annual_man > 0:
                from core.inheritance import compare_gift_strategies
                gift_result = compare_gift_strategies(
                    annual_amount_yen=gift_annual_man * 10000,
                    years=gift_years,
                    num_recipients=gift_recipients,
                    estimated_marginal_rate=est_rate,
                )
                st.metric(
                    "贈与総額",
                    f"{gift_result['total_gifted']//10000:,} 万円",
                    f"{gift_annual_man}万円 × {gift_years}年 × {gift_recipients}人",
                )

                # 比較テーブル
                gift_rows = [
                    {
                        "戦略": "📅 暦年贈与（年110万円非課税）",
                        "非課税枠活用額": f"{gift_result['annual']['tax_free_portion']//10000:,} 万円",
                        "贈与税": f"{gift_result['annual']['taxable_gift_tax']//10000:,} 万円",
                        "相続税の節税効果": f"{gift_result['annual']['inheritance_tax_saved']//10000:,} 万円",
                        "正味節税額": f"**{gift_result['annual']['net_savings']//10000:,} 万円**",
                    },
                    {
                        "戦略": "💼 相続時精算課税（2,500万円非課税）",
                        "非課税枠活用額": f"{gift_result['lump_sum_2500']['tax_free_portion']//10000:,} 万円",
                        "贈与税": f"{gift_result['lump_sum_2500']['taxable_gift_tax']//10000:,} 万円",
                        "相続税の節税効果": f"{gift_result['lump_sum_2500']['inheritance_tax_saved']//10000:,} 万円",
                        "正味節税額": f"**{gift_result['lump_sum_2500']['net_savings']//10000:,} 万円**",
                    },
                ]
                st.dataframe(gift_rows, use_container_width=True, hide_index=True)
                st.info(gift_result["recommendation"])
                st.caption(
                    "⚠️ **重要な注意点**\n\n"
                    "- 暦年贈与: 2024年改正で相続開始前**7年以内**の贈与は相続財産に持戻し（旧3年）\n"
                    "- 相続時精算課税: 一度選択すると暦年贈与に戻れない。受贈者18歳以上＋贈与者60歳以上が要件\n"
                    "- 教育資金・結婚子育て資金・住宅取得資金等の特例も別途活用可能\n"
                    "- 推定限界税率: 約{:.0%}（財産総額より自動算定）— 実際は配偶者控除・特例適用後で異なります\n"
                    "- 個別戦略は必ず**税理士にご相談ください**。".format(est_rate)
                )
        st.divider()

    # ── 3-4. 事業承継リスクアラート ───────────────────────────────────────────
    risks = get_business_risks(ft, propositus_id)
    if risks:
        st.subheader("🏢 事業承継リスクアラート")
        for risk in risks:
            st.warning(risk)
        st.divider()

    # ── 3-4-b. 国際相続の警告 ────────────────────────────────────────────────
    with st.expander("🌐 国際相続にご注意（外国籍配偶者・海外資産がある場合）", expanded=False):
        st.warning(
            "本シミュレーションは**日本国内法**に基づく計算です。以下に該当する場合、"
            "外国の相続法・税制が併用適用される可能性があり、結果が**大きく異なります**。"
        )
        st.markdown("""
#### ⚠️ 国際相続の可能性があるケース

| 該当事例 | 注意点 |
|---|---|
| 被相続人が**外国籍**または相続人に外国籍の方がいる | 法の適用に関する通則法36条により、被相続人の本国法が準拠法となる場合あり（日本国籍なら原則日本法） |
| **海外に資産**（不動産・銀行口座・証券）がある | 現地法に基づくプロベート手続（米英）等が必要になる場合あり |
| 相続人が**海外に居住**（日本に住所なし） | 制限納税義務者として日本国内財産のみ課税の場合あり（相続税法1条の3） |
| 被相続人が**過去10年以内に海外居住歴**あり | 国外財産も日本の相続税課税対象となる場合あり |
| 米国に資産（株式・不動産等）がある | **米国遺産税**（連邦・州）が別途課税される可能性 |
| 中国・韓国に不動産がある | 現地での名義変更手続き・税制が日本と大きく異なる |

#### 🚨 必ず専門家にご相談を

- **国際相続専門の弁護士**: 準拠法の判断、プロベート手続き、現地代理人の選定
- **国際税務専門の税理士**: 二重課税防止条約、国外財産調書、国外転出時課税
- **現地の専門家**との連携体制を持つ事務所が望ましい

> 国際相続は手続きに**1年以上**かかるケースも珍しくありません。早めの相談が選択肢として考えられます。
        """)
        st.caption(
            "本アプリは日本国内法を前提とした一般情報提供であり、国際相続については一切判断・助言を行いません。"
        )
    st.divider()

    # ── 3-5. 生命保険の非課税枠 ──────────────────────────────────────────────
    st.subheader("🛡️ 生命保険の非課税枠")
    # 生命保険の非課税枠も相続税法上の法定相続人数を使用
    ins_exemption = 5_000_000 * num_tax_heirs
    ic1, ic2 = st.columns(2)
    ic1.metric(
        "死亡保険金の非課税枠",
        f"{ins_exemption//10000:,} 万円",
        f"500万円 × 相続税法上の法定相続人{num_tax_heirs}名",
    )
    with ic2:
        st.info(
            f"相続税法上の法定相続人 **{num_tax_heirs}名** の場合、死亡保険金のうち "
            f"**{ins_exemption//10000:,}万円** が相続税の課税対象外になります。\n\n"
            "既存の生命保険を確認し、非課税枠を最大限活用することが選択肢として考えられます。"
        )

    st.divider()

    # ── 3-5.5. Gemini AI 診断 ──────────────────────────────────────────────
    from core.gemini_client import is_gemini_available, diagnose_succession_gemini

    st.subheader("🤖 AI診断（Gemini）— 最優先の一手をズバリ提示")

    if not is_gemini_available():
        st.warning(
            "Gemini APIキーが設定されていません。\n\n"
            "環境変数 `GEMINI_API_KEY` または `GOOGLE_API_KEY` に、"
            "[Google AI Studio](https://aistudio.google.com/app/apikey) で取得した"
            "APIキー（無料枠あり）を設定してください。"
        )
    else:
        with st.form("gemini_diagnosis_form"):
            concerns = st.text_area(
                "懸念事項・相談したいこと（任意）",
                placeholder="例：長男以外の子への配慮、後継者問題、相続税の負担など",
                height=80,
            )
            run_diag = st.form_submit_button("🤖 AIで診断する", type="primary")

        if run_diag:
            # サマリーを組み立てる
            family_summary = ft.summary()
            propositus = ft.persons[propositus_id]
            assets_lines = [
                f"被相続人の資産: {propositus.assets_yen:,}円"
                f"（{propositus.assets_yen//10000:,}万円）",
            ]
            if propositus.has_business_shares:
                assets_lines.append("自社株・非上場株を保有")
            if propositus.notes:
                assets_lines.append(f"備考: {propositus.notes}")
            if st.session_state.total_assets:
                assets_lines.append(
                    f"相続財産総額（ユーザー入力）: "
                    f"{st.session_state.total_assets//10000:,}万円"
                )
            assets_summary = "\n".join(assets_lines)

            with st.spinner("Gemini が診断中...（10〜20秒）"):
                diagnosis = diagnose_succession_gemini(
                    family_summary=family_summary,
                    assets_summary=assets_summary,
                    shares_summary=explanation,
                    concerns=concerns,
                )

            st.markdown("#### 📋 診断結果")
            from core.legal_safety import safety_badge
            st.markdown(safety_badge(), unsafe_allow_html=True)

            # ── AI出力クロスバリデーション（ハルシネーション検知）─────
            from core.ai_validation import (
                validate_ai_output, cross_check_tax_amount, format_validation_badge
            )
            val_result = validate_ai_output(diagnosis)
            badge = format_validation_badge(val_result)
            if badge:
                st.markdown(badge, unsafe_allow_html=True)

            # 税額が言及されていたら自社計算値と照合
            if st.session_state.total_assets > 0:
                calc_tax = tax["estimated_tax"] if "tax" in dir() else 0
                if calc_tax > 0:
                    discrepancy = cross_check_tax_amount(diagnosis, calc_tax)
                    if discrepancy:
                        st.warning(discrepancy)

            st.markdown(diagnosis)
            st.caption(
                "※ AI診断は参考情報です。最終判断は必ず弁護士・税理士等の専門家にご相談ください。"
                "AI出力は自社計算ロジック・既知の事実DBと照合済みです。"
            )

    st.divider()

    # ── 3-6. 遺言書作成のポイント ─────────────────────────────────────────────
    st.subheader("📝 遺言書作成のポイント")

    has_business = any(
        p.has_business_shares for p in ft.persons.values() if p.is_propositus
    )
    spouse_id = ft.get_spouse(propositus_id)
    children_ids = ft.get_children(propositus_id)

    will_points = []
    if len(shares) >= 3:
        will_points.append(
            "**遺産分割の明確化** — 相続人が多い場合、遺言書で各財産の帰属先を明確にすることで"
            "遺産分割協議の長期化・紛争を防げます。"
        )
    if spouse_id and children_ids:
        will_points.append(
            "**遺留分への配慮** — 配偶者・子には最低限の遺留分（法定相続分の1/2）が保障されています。"
            "特定の相続人に集中させる場合は遺留分侵害額請求のリスクを考慮してください。"
        )
    if has_business:
        will_points.append(
            "**自社株の承継先指定** — 遺言書で後継者へ自社株を集中させることで経営権の分散を防げます。"
            "遺言執行者の指定もあわせて行ってください。"
        )
    will_points += [
        "**遺言執行者の指定** — 信頼できる人物または専門家（弁護士・税理士）を遺言執行者として指定することで、"
        "手続きをスムーズに進められます。",
        "**遺言書の形式** — 公正証書遺言（公証役場で作成）または法務局への自筆証書遺言保管制度の利用を推奨します。"
        "紛失・偽造リスクを最小化できます。",
    ]
    for i, pt in enumerate(will_points, 1):
        st.markdown(f"{i}. {pt}")

    # ── 3-6-b. AI遺言書ドラフト生成 ──────────────────────────────────────────
    from core.gemini_client import is_gemini_available as _is_gem_avail
    if _is_gem_avail():
        with st.expander("✍️ AIで自筆証書遺言の雛形を生成（Gemini）", expanded=False):
            st.warning(
                "⚖️ **重要**: 出力されるのは**一般的な雛形テンプレート**であり、"
                "個別事案の法的助言ではありません。実際の作成は**必ず弁護士・公証人にご相談ください**。"
                "本機能は弁護士法72条に抵触しないよう、特定事案の法律事務は提供しません。"
            )
            with st.form("will_draft_form"):
                distribution_intent = st.text_area(
                    "希望する財産配分（任意）",
                    placeholder=(
                        "例：自宅は妻に、預金は子供たちに均等に、自社株は後継者の長男に集中させたい。\n"
                        "次女には保険金で配慮したい。等"
                    ),
                    height=100,
                )
                will_btn = st.form_submit_button(
                    "📜 雛形テンプレートを生成", type="primary",
                    disabled=remaining_calls <= 0,
                )

            if will_btn:
                from core.gemini_client import generate_will_draft_gemini
                family_summary = ft.summary()
                propositus = ft.persons[propositus_id]
                assets_lines = [
                    f"被相続人の資産: {propositus.assets_yen:,}円"
                    f"（{propositus.assets_yen//10000:,}万円）",
                ]
                if propositus.has_business_shares:
                    assets_lines.append("自社株・非上場株を保有")
                if st.session_state.total_assets:
                    assets_lines.append(
                        f"相続財産総額（ユーザー入力）: "
                        f"{st.session_state.total_assets//10000:,}万円"
                    )
                assets_summary = "\n".join(assets_lines)

                with st.spinner("Geminiが遺言書雛形を作成中...（15〜30秒）"):
                    draft = generate_will_draft_gemini(
                        family_summary=family_summary,
                        assets_summary=assets_summary,
                        distribution_intent=distribution_intent,
                    )
                st.session_state.llm_count += 1

                from core.legal_safety import safety_badge
                from core.ai_validation import validate_ai_output, format_validation_badge
                st.markdown(safety_badge(), unsafe_allow_html=True)
                draft_val = validate_ai_output(draft)
                draft_badge = format_validation_badge(draft_val)
                if draft_badge:
                    st.markdown(draft_badge, unsafe_allow_html=True)
                st.markdown(draft)
                st.download_button(
                    "📥 雛形をテキストファイルでダウンロード",
                    data=draft.encode("utf-8"),
                    file_name=f"will_draft_template_{propositus.name}.txt",
                    mime="text/plain",
                )

    st.divider()

    # ── 3-7. 死後手続きタイムライン ──────────────────────────────────────────
    st.subheader("📅 死後の手続きタイムライン")
    timeline = [
        ("7日以内",    "死亡届の提出（市区町村役場）"),
        ("14日以内",   "年金受給停止・国民健康保険/介護保険 資格喪失届"),
        ("3か月以内",  "相続放棄・限定承認の申述（家庭裁判所）※必要な場合"),
        ("4か月以内",  "故人の準確定申告（所得税・消費税）"),
        ("速やかに",   "生命保険・死亡退職金の請求（通常3年の時効に注意）"),
        ("速やかに",   "預貯金口座の凍結解除・名義変更"),
        ("3年以内",    "不動産の相続登記（2024年4月より義務化）"),
        ("10か月以内", "相続税の申告・納付（課税対象の場合）"),
    ]
    for deadline, task in timeline:
        st.markdown(
            f"""<div style="display:flex;gap:12px;margin-bottom:8px;align-items:flex-start;">
            <span style="background:#4a90d9;color:white;padding:3px 10px;border-radius:12px;
                         font-size:12px;white-space:nowrap;flex-shrink:0;">{deadline}</span>
            <span style="font-size:14px;line-height:1.6;">{task}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── 3-8. PDFダウンロード ─────────────────────────────────────────────────
    st.subheader("💾 結果の保存")
    from core.pdf_export import is_pdf_available, generate_pdf_report

    if not is_pdf_available():
        col_pdf, col_note = st.columns([1, 3])
        with col_pdf:
            st.button("📄 PDFで保存", disabled=True, use_container_width=True)
        with col_note:
            st.warning(
                "PDF出力には `reportlab` が必要です。次のコマンドでインストールしてください:\n\n"
                "`pip install reportlab`"
            )
    else:
        tax_for_pdf = None
        if st.session_state.total_assets > 0:
            tax_for_pdf = get_inheritance_tax_estimate(
                shares, st.session_state.total_assets, num_heirs, num_tax_heirs
            )

        # ── PDFに新セクション情報を集約（セッション入力済みの場合のみ） ──
        small_land_for_pdf = None
        lt = st.session_state.get("land_type", "none")
        lv = st.session_state.get("land_value", 0)
        lar = st.session_state.get("area_sqm", 0.0)
        if lt != "none" and lv > 0 and lar > 0:
            from core.inheritance import calculate_small_residential_deduction
            ssd = calculate_small_residential_deduction(lt, lv * 10000, lar)
            if ssd["applicable"]:
                ssd["before"] = lv * 10000
                small_land_for_pdf = ssd

        secondary_for_pdf = None
        spouse_id_pdf = ft.get_spouse(propositus_id)
        if spouse_id_pdf and spouse_id_pdf in shares and st.session_state.total_assets > 0:
            from core.inheritance import calculate_secondary_inheritance
            ch_count = sum(
                1 for hid in shares
                if hid in set(ft.get_legal_children(propositus_id))
                and hid != spouse_id_pdf
            )
            if ch_count == 0:
                ch_count = max(1, len(shares) - 1)
            secondary_for_pdf = calculate_secondary_inheritance(
                primary_total_yen=st.session_state.total_assets,
                num_children=ch_count,
                spouse_own_assets_yen=st.session_state.get("spouse_own_assets", 0) * 10000,
            )

        gift_for_pdf = None
        ga = st.session_state.get("gift_annual", 0)
        gy = st.session_state.get("gift_years", 0)
        gr = st.session_state.get("gift_recipients", 0)
        if ga > 0 and gy > 0 and gr > 0:
            from core.inheritance import compare_gift_strategies
            est_rate = 0.10
            for threshold, rate in [(50_000_000, 0.20), (100_000_000, 0.30),
                                    (200_000_000, 0.40), (300_000_000, 0.45)]:
                if st.session_state.total_assets > threshold:
                    est_rate = rate
            gift_for_pdf = compare_gift_strategies(
                annual_amount_yen=ga * 10000,
                years=gy,
                num_recipients=gr,
                estimated_marginal_rate=est_rate,
            )

        try:
            pdf_bytes = generate_pdf_report(
                family_tree=ft,
                propositus_id=propositus_id,
                shares=shares,
                total_assets_yen=st.session_state.total_assets,
                tax_info=tax_for_pdf,
                tax_heir_info=tax_heir_info,
                legitime_info=legitime_info,
                small_land_info=small_land_for_pdf,
                secondary_info=secondary_for_pdf,
                gift_info=gift_for_pdf,
            )
        except Exception as e:
            pdf_bytes = None
            st.error(f"PDF生成中にエラー: {e}")

        col_pdf, col_note = st.columns([1, 3])
        with col_pdf:
            if pdf_bytes:
                from datetime import datetime as _dt
                fname = f"inheritance_report_{_dt.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.download_button(
                    label="📄 PDFで保存",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            else:
                st.button("📄 PDFで保存", disabled=True, use_container_width=True)
        with col_note:
            st.caption(
                "📋 PDFには家族構成・法定相続分・相続税概算・専門家相談ガイドが含まれます。"
                "弁護士法72条への配慮として、特定事案への法的助言は記載されません。"
            )

    st.divider()

    # ── 3-9. CTAバナー広告（アフィリエイトリンク差し替え可能） ────────────────
    st.subheader("👨‍💼 次のステップ：専門家にご相談を")

    # ▼ アフィリエイト URL（承認後にここを差し替えるだけ）
    AFFILIATE_URL_TAX = "#"          # 例: 税理士ドットコム（A8.net 案件）
    AFFILIATE_URL_BIZ = "#"          # 例: 事業承継・M&A仲介（A8.net 案件）

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(
            f"""<a href="{AFFILIATE_URL_TAX}" target="_blank" rel="noopener sponsored"
            style="text-decoration:none;color:inherit;">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);
            color:white;padding:20px;border-radius:12px;text-align:center;cursor:pointer;">
            <b style="font-size:16px;">相続専門税理士に無料相談</b><br>
            <span style="font-size:13px;">診断結果を見せるだけでOK・全国対応</span><br><br>
            <span style="background:white;color:#667eea;padding:6px 20px;
                  border-radius:20px;font-weight:bold;font-size:13px;">
            相談する →
            </span>
            </div></a>""",
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            f"""<a href="{AFFILIATE_URL_BIZ}" target="_blank" rel="noopener sponsored"
            style="text-decoration:none;color:inherit;">
            <div style="background:linear-gradient(135deg,#f093fb,#f5576c);
            color:white;padding:20px;border-radius:12px;text-align:center;cursor:pointer;">
            <b style="font-size:16px;">事業承継・M&A専門家に相談</b><br>
            <span style="font-size:13px;">後継者問題・自社株対策を無料診断</span><br><br>
            <span style="background:white;color:#f5576c;padding:6px 20px;
                  border-radius:20px;font-weight:bold;font-size:13px;">
            診断を受ける →
            </span>
            </div></a>""",
            unsafe_allow_html=True,
        )
    st.caption(
        "※ 上記は広告枠です（アフィリエイトリンク差し替え予定）。"
        "リンク先での申込・契約は各社の責任のもとで行われ、当サイトは仲介を行いません。"
    )

    st.divider()

    # ── 3-10. 専門家チェック歓迎 CTA ─────────────────────────────────────────
    st.subheader("🤝 専門家の皆様へ — 計算ロジックの精査を歓迎します")
    st.markdown(
        """<div style="background:#F4F6F7;border-left:4px solid #1ABC9C;
        padding:18px 20px;border-radius:6px;">
        <p style="margin:0 0 10px 0;font-size:14px;line-height:1.8;">
        本アプリは <b>39ケースの自動テスト</b>（民法・相続税法のエッジケース）と
        <b>国税庁公表の相続税速算表</b>に基づいて計算ロジックを実装しており、
        シンプルなケースでは国税庁シミュレーターと一致する精度で算出しています。
        </p>
        <p style="margin:0 0 10px 0;font-size:14px;line-height:1.8;">
        <b>弁護士・税理士・司法書士の先生方へ</b>: 計算ロジックの誤り・改善点を
        ご指摘いただける場合、GitHub Issues または下記より歓迎いたします。
        本アプリは <b>弁護士法72条</b> に抵触しない設計（特定事案への法律事務を行わない一般情報提供）と
        しており、専門家の皆様のお仕事を補完・促進するツールを目指しています。
        </p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">
            <a href="https://github.com/yadianqiteng5-spec/kakeizu-navi/issues"
               target="_blank" rel="noopener"
               style="background:#1ABC9C;color:white;padding:8px 16px;
                      border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">
               🐛 GitHub Issuesで指摘する
            </a>
            <a href="https://github.com/yadianqiteng5-spec/kakeizu-navi"
               target="_blank" rel="noopener"
               style="background:#34495E;color:white;padding:8px 16px;
                      border-radius:6px;text-decoration:none;font-weight:bold;font-size:13px;">
               📂 ソースコードを見る
            </a>
            <span style="background:#27AE60;color:white;padding:8px 16px;
                  border-radius:6px;font-weight:bold;font-size:13px;">
               ✅ 39ケース自動テスト済
            </span>
        </div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "💡 計算ロジックは `core/inheritance.py` に集約され、`tests/test_inheritance.py` で"
        "検証可能です。`python -X utf8 tests/test_inheritance.py` で39ケースのテストを再現できます。"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 共通フッター: 信頼性バッジ + テスト済みケース一覧（全Step末尾に表示）
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown(
    """<div style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 12px 0;justify-content:center;">
    <span style="background:#27AE60;color:white;padding:4px 10px;border-radius:12px;
                 font-size:11px;font-weight:bold;">
    ✅ 39ケース 自動テスト済</span>
    <span style="background:#2980B9;color:white;padding:4px 10px;border-radius:12px;
                 font-size:11px;font-weight:bold;">
    ⚖️ 民法・相続税法準拠</span>
    <span style="background:#8E44AD;color:white;padding:4px 10px;border-radius:12px;
                 font-size:11px;font-weight:bold;">
    🔒 ゼロ・リテンション</span>
    <span style="background:#E67E22;color:white;padding:4px 10px;border-radius:12px;
                 font-size:11px;font-weight:bold;">
    🤖 Claude + Gemini</span>
    </div>""",
    unsafe_allow_html=True,
)

with st.expander("📋 テスト済みの法律ケース一覧（39ケース全通過）", expanded=False):
    st.markdown("""
| 分類 | ケース | 根拠条文 |
|---|---|---|
| 基本順位 | 配偶者+子、配偶者+直系尊属、配偶者+兄弟姉妹、配偶者のみ | 民法900条 |
| 代襲相続 | 子の死亡→孫が無限代襲 | 民法887条2項 |
| 代襲相続 | 兄弟の死亡→甥姪が代襲（一代限り） | 民法889条2項 |
| 代襲相続 | 相続放棄者の子は代襲しない | 民法939条 |
| 同時死亡 | 親子同時死亡時の相続権 + 代襲成立 | 民法32条の2 |
| 半血兄弟 | 全血:半血 = 2:1 | 民法900条4号但書 |
| 直系尊属繰上 | 両親死亡→祖父母へ繰上 | 民法889条1項 |
| 特別養子 | 実親との親族関係終了（実親から相続不可） | 民法817条の9 |
| 普通養子 | 実親・養親いずれからも相続可 | 民法809条 |
| 遺留分 | 兄弟のみ→0、直系尊属のみ→1/3、配偶者+子→1/2 | 民法1042条 |
| 相続税 | 養子算入制限（実子あり1名／なし2名） | 相続税法15条2項 |

> ⚠️ 寄与分・特別受益・特別寄与料などは未対応です。該当事案は専門家にご相談ください。
    """)
