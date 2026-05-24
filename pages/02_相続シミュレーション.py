import streamlit as st
from core.family_tree import FamilyTree
from core.inheritance import calculate_legal_shares, format_shares_table

st.set_page_config(page_title="相続シミュレーション", page_icon="💴", layout="wide")
st.info("メインのシミュレーターは **トップページ（家系図Navi）** をご利用ください。")

if "family_tree" not in st.session_state:
    st.session_state.family_tree = FamilyTree()
if "total_assets" not in st.session_state:
    st.session_state.total_assets = 0

ft: FamilyTree = st.session_state.family_tree

st.title("💴 相続シミュレーション")

if ft.is_empty():
    st.warning("まず「家系図入力」ページで家族情報を入力してください。")
    st.stop()

propositus_id = ft.get_propositus()
if not propositus_id:
    st.warning("被相続人が設定されていません。「家系図入力」で被相続人にチェックを入れてください。")
    st.stop()

st.info(f"**被相続人**: {ft.persons[propositus_id].name}")

total_man = st.number_input("相続財産総額（万円）", min_value=0,
                            value=st.session_state.total_assets // 10000, step=100)
st.session_state.total_assets = total_man * 10000

shares, explanation = calculate_legal_shares(ft, propositus_id)
if not shares:
    st.error("法定相続人が見つかりません。")
    st.stop()

st.markdown(explanation)

rows = format_shares_table(shares, ft, st.session_state.total_assets)
st.dataframe(rows, use_container_width=True, hide_index=True)

if total_man > 0:
    try:
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Pie(
            labels=[r["氏名"] for r in rows],
            values=[float(shares[pid]) for pid in shares],
            hole=0.3, textinfo="label+percent",
        )])
        fig.update_layout(title=f"相続財産分配（総額: {total_man:,}万円）")
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass

st.session_state.calculated_shares = shares
st.session_state.shares_explanation = explanation
