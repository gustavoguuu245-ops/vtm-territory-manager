# app/pages/02_Historico.py
import streamlit as st

st.set_page_config(
    page_title="Histórico",
    page_icon="📜",
    layout="wide"
)

from core.db.session import get_streamlit_db
from core.services.territory_service import TerritoryService
from app.components.sidebar import render_sidebar

render_sidebar()

if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Faça login primeiro")
    st.stop()

st.title("📜 Histórico de Alterações")

db = get_streamlit_db()
service = TerritoryService(db)

history = service.get_history(limit=50)

if not history:
    st.info("Nenhuma alteração registrada ainda.")
else:
    for h in history:
        with st.container(border=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.caption(h.changed_at.strftime("%d/%m %H:%M"))
            with col2:
                st.write(f"**{h.modified_by}** alterou `{h.field_changed}`")
                st.caption(f"De: `{h.old_value}` → Para: `{h.new_value}`")