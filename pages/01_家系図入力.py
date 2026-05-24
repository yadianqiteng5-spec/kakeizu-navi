import streamlit as st
from core.family_tree import FamilyTree, Gender

st.set_page_config(page_title="家系図入力", page_icon="👨‍👩‍👧‍👦", layout="wide")

st.info("このページはサブ機能です。メインのシミュレーターは **トップページ（家系図Navi）** をご利用ください。")

if "family_tree" not in st.session_state:
    st.session_state.family_tree = FamilyTree()
if "ai_preview" not in st.session_state:
    st.session_state.ai_preview = None

ft: FamilyTree = st.session_state.family_tree

st.title("👨‍👩‍👧‍👦 家系図入力（サブページ）")

tab_manual, tab_ai = st.tabs(["手動入力", "テキストから自動抽出（AI）"])

# ── 手動入力 ──────────────────────────────────────────────────────────────
with tab_manual:
    st.subheader("メンバーを追加")
    with st.form("form_add_person", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("氏名 *")
            gender = st.selectbox("性別", [Gender.MALE, Gender.FEMALE, Gender.UNKNOWN])
        with c2:
            birth_year_str = st.text_input("生年（西暦、省略可）", placeholder="例: 1950")
            is_alive = st.checkbox("存命（チェックを外すと故人）", value=True)
            is_propositus = st.checkbox("被相続人（相続の起点）")
            has_biz = st.checkbox("自社株保有")
            assets_str = st.text_input("保有資産（万円、省略可）", placeholder="例: 5000")

        if st.form_submit_button("追加する"):
            if not name.strip():
                st.error("氏名を入力してください")
            else:
                if is_propositus:
                    for p in ft.persons.values():
                        p.is_propositus = False
                birth_year = int(birth_year_str.strip()) if birth_year_str.strip().isdigit() else None
                assets = int(assets_str.strip()) * 10000 if assets_str.strip().isdigit() else 0
                ft.add_person(
                    name=name.strip(),
                    gender=gender,
                    birth_year=birth_year,
                    is_alive=is_alive,
                    is_propositus=is_propositus,
                    assets_yen=assets,
                    has_business_shares=has_biz,
                )
                st.success(f"「{name}」を追加しました")
                st.rerun()

    if not ft.is_empty():
        st.subheader("関係を設定")
        persons_list = [(pid, p.name) for pid, p in ft.persons.items()]
        options = [p[1] for p in persons_list]

        with st.form("form_add_rel"):
            c1, c2, c3 = st.columns(3)
            with c1:
                sel1 = st.selectbox("人物1", options, key="sel1")
            with c2:
                rel_type = st.selectbox("関係", ["配偶者", "親→子（人物1が親）"])
            with c3:
                sel2 = st.selectbox("人物2", options, key="sel2")

            if st.form_submit_button("関係を追加"):
                idx1, idx2 = options.index(sel1), options.index(sel2)
                p1_id, p2_id = persons_list[idx1][0], persons_list[idx2][0]
                if p1_id == p2_id:
                    st.error("同一人物を選択しています")
                else:
                    if rel_type == "配偶者":
                        ft.add_spouse(p1_id, p2_id)
                    else:
                        ft.add_parent_child(p1_id, p2_id)
                    st.success("関係を追加しました")
                    st.rerun()

        st.subheader("登録済みメンバー")
        for pid, p in list(ft.persons.items()):
            c1, c2 = st.columns([5, 1])
            with c1:
                tags = []
                if p.is_propositus:
                    tags.append("★被相続人")
                if not p.is_alive:
                    tags.append("故人")
                if p.has_business_shares:
                    tags.append("自社株")
                birth = f"（{p.birth_year}年生）" if p.birth_year else ""
                st.write(f"**{p.name}** {p.gender.value}{birth}　{'　'.join(tags)}")
            with c2:
                if st.button("削除", key=f"del_{pid}"):
                    ft.remove_person(pid)
                    st.rerun()

# ── AI自動抽出 ────────────────────────────────────────────────────────────
with tab_ai:
    st.subheader("文章から家族関係を自動抽出")
    from core.claude_client import is_api_available, extract_family_from_text

    if not is_api_available():
        st.warning("ANTHROPIC_API_KEY が設定されていません。手動入力タブをご利用ください。")

    input_text = st.text_area("家族の説明文を入力", height=140)
    if st.button("AIで自動抽出", disabled=not is_api_available() or not input_text.strip()):
        with st.spinner("AIが解析中..."):
            result = extract_family_from_text(input_text)
        if result:
            st.session_state.ai_preview = result
            st.rerun()
        else:
            st.error("解析に失敗しました。テキストをより詳しく入力してみてください。")

    if st.session_state.ai_preview:
        preview = st.session_state.ai_preview
        names = [p["name"] for p in preview.get("persons", [])]
        st.success(f"解析完了: {', '.join(names)}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("この内容で登録（現在のデータを上書き）", type="primary"):
                new_ft = FamilyTree()
                id_map: dict = {}
                gender_map = {"male": Gender.MALE, "female": Gender.FEMALE, "unknown": Gender.UNKNOWN}
                for p_data in preview.get("persons", []):
                    new_id = new_ft.add_person(
                        name=p_data["name"],
                        gender=gender_map.get(p_data.get("gender", "unknown"), Gender.UNKNOWN),
                        birth_year=p_data.get("birth_year"),
                        is_alive=p_data.get("is_alive", True),
                        is_propositus=p_data.get("is_propositus", False),
                        assets_yen=p_data.get("assets_yen", 0) or 0,
                        has_business_shares=p_data.get("has_business_shares", False),
                        notes=p_data.get("notes", ""),
                    )
                    id_map[p_data["id"]] = new_id
                for rel in preview.get("relationships", []):
                    p1 = id_map.get(rel["person1_id"])
                    p2 = id_map.get(rel["person2_id"])
                    if p1 and p2:
                        if rel["rel_type"] == "spouse":
                            new_ft.add_spouse(p1, p2)
                        elif rel["rel_type"] == "parent_child":
                            new_ft.add_parent_child(p1, p2)
                st.session_state.family_tree = new_ft
                st.session_state.ai_preview = None
                st.rerun()
        with c2:
            if st.button("キャンセル"):
                st.session_state.ai_preview = None
                st.rerun()

# ── 家系図プレビュー ──────────────────────────────────────────────────────
if not ft.is_empty():
    st.divider()
    st.subheader("家系図プレビュー")
    st.graphviz_chart(ft.to_dot())

    if st.button("全データをリセット", type="secondary"):
        st.session_state.family_tree = FamilyTree()
        st.session_state.ai_preview = None
        st.rerun()
