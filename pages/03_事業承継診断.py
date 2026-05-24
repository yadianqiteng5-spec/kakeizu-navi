import streamlit as st
from core.family_tree import FamilyTree
from core.claude_client import is_api_available, diagnose_succession

st.set_page_config(page_title="事業承継診断", page_icon="🏢", layout="wide")
st.info("メインのシミュレーターは **トップページ（家系図Navi）** をご利用ください。")

if "family_tree" not in st.session_state:
    st.session_state.family_tree = FamilyTree()

ft: FamilyTree = st.session_state.family_tree

st.title("🏢 事業承継診断")

if ft.is_empty():
    st.warning("まず「家系図入力」ページで家族情報を入力してください。")
    st.stop()

if not is_api_available():
    st.error("ANTHROPIC_API_KEY が設定されていません。")
    st.stop()

propositus_id = ft.get_propositus()
st.info(f"**被相続人**: {ft.persons[propositus_id].name if propositus_id else '未設定'}")

assets_description = st.text_area("資産・事業の概要（任意）", height=110)
concerns = st.text_area("懸念事項（任意）", height=75)

if st.button("AIで診断する", type="primary"):
    shares_text = st.session_state.get("shares_explanation", "（未計算）")
    assets_full = (assets_description.strip() or "（情報なし）")
    if concerns.strip():
        assets_full += f"\n\n【懸念事項】\n{concerns.strip()}"

    with st.spinner("AIが診断中..."):
        result = diagnose_succession(ft.summary(), assets_full, shares_text)

    st.subheader("診断結果")
    st.markdown(result)
