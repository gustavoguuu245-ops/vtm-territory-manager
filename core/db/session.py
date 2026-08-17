"""Gerenciamento de sessões para Streamlit."""
import streamlit as st
from core.db.database import SessionLocal

def get_streamlit_db():
    if "db_session" not in st.session_state:
        st.session_state.db_session = SessionLocal()
    return st.session_state.db_session

def close_streamlit_db():
    if "db_session" in st.session_state:
        st.session_state.db_session.close()
        del st.session_state.db_session