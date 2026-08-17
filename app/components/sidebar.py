# app/components/sidebar.py - VERSÃO DEFINITIVA (SEM st.switch_page)
import streamlit as st

def render_sidebar():
    """Renderiza a sidebar com navegação usando query params."""
    with st.sidebar:
        st.title("🧛 VTM Territory Manager")
        st.markdown("---")
        
        if "user" in st.session_state and st.session_state.user:
            user = st.session_state.user
            st.write(f"👤 **{user.username}**")
            st.write(f"Role: `{user.role.upper()}`")
            st.write(f"Região: `{user.assigned_region or 'Global'}`")
            
            if user.clan:
                st.write(f"Clã: `{user.clan}`")
            st.write(f"🆔 **Seu ID:** `{user.id}`")
            st.info(f"💡 Compartilhe seu mapa: Envie o ID `{user.id}` ou o link `?view_user_id={user.id}`")    
            
            st.markdown("---")
            
            # ========== NAVEGAÇÃO COM BOTÕES + st.query_params ==========
            st.markdown("### 📍 Navegação")
            
            # Usa query_params para navegação
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🏠", use_container_width=True, help="Dashboard"):
                    st.query_params["page"] = "dashboard"
                    st.rerun()
            
            with col2:
                if st.button("🗺️", use_container_width=True, help="Mapa"):
                    st.query_params["page"] = "mapa"
                    st.rerun()
            
            col3, col4 = st.columns(2)
            with col3:
                if st.button("📜", use_container_width=True, help="Histórico"):
                    st.query_params["page"] = "historico"
                    st.rerun()
            
            if user.is_admin() or user.is_narrador():
                with col4:
                    if st.button("⚙️", use_container_width=True, help="Admin"):
                        st.query_params["page"] = "admin"
                        st.rerun()
            
            st.markdown("---")
            
            # Mostra a página atual
            current_page = st.query_params.get("page", "dashboard")
            st.caption(f"📍 Página: {current_page}")
            
            if st.button("🚪 Sair", use_container_width=True, type="secondary"):
                from core.services.territory_service import TerritoryService
                from core.db.session import get_streamlit_db
                
                db = get_streamlit_db()
                service = TerritoryService(db)
                service.release_all_user_locks(user)
                
                # Limpa a sessão
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            st.info("🔐 Faça login para continuar")