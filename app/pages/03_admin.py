# app/pages/03_Admin.py - VERSÃO HIERÁRQUICA (SUPREMO + MODERADORES)
import streamlit as st

st.set_page_config(
    page_title="Admin",
    page_icon="⚙️",
    layout="wide"
)

from core.db.session import get_streamlit_db
from core.services.territory_service import TerritoryService
from core.auth.authenticator import AuthManager
from app.components.sidebar import render_sidebar

# Renderiza a sidebar primeiro
render_sidebar()

# ========== VERIFICAÇÃO DE LOGIN ==========
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Faça login primeiro")
    st.stop()

user = st.session_state.user

# ========== HIERARQUIA DE ACESSO ==========
is_supreme = (user.id == 1)                    # Você, o criador
is_moderator = (user.role == "moderator")      # Ajudantes
is_admin = (user.role == "admin")              # Caso você tenha se colocado como admin no seed

# Se não for nenhum dos acima, bloqueia o acesso
if not (is_supreme or is_moderator or is_admin):
    st.error("🚫 Acesso restrito apenas ao Supremo (ID 1) e Moderadores autorizados.")
    st.stop()

# ========== PAINEL ==========
st.title("⚙️ Painel Administrativo")
st.caption(f"Bem-vindo, {user.username}. Seu nível de acesso: **{'👑 Supremo' if is_supreme else '🛡️ Moderador'}**")

db = get_streamlit_db()
service = TerritoryService(db)

# Cria as abas do painel
tab1, tab2, tab3 = st.tabs(["👤 Gerenciar Usuários", "🌍 Regiões", "📊 Estatísticas do Site"])

# ========== ABA 1: GERENCIAR USUÁRIOS ==========
with tab1:
    st.subheader("🔧 Lista de Usuários Cadastrados")
    from core.models.user import User
    from sqlalchemy import update
    
    users = db.query(User).all()
    
    for u in users:
        with st.container(border=True):
            cols = st.columns([2, 1, 1, 2])
            cols[0].write(f"**{u.username}** (🆔 ID: `{u.id}`)")
            cols[1].write(f"Role: `{u.role}`")
            cols[2].write(f"Clã: {u.clan or 'N/A'}")
            
            # COLUNA DE AÇÕES
            with cols[3]:
                # 1. Promover/Rebaixar a Moderador (Apenas SUPREMO pode fazer isso)
                if is_supreme:
                    if u.id != 1: # Não pode modificar a si mesmo
                        if u.role == "moderator":
                            if st.button(f"⬇️ Rebaixar para Jogador", key=f"demote_{u.id}", type="secondary"):
                                db.execute(update(User).where(User.id == u.id).values(role="jogador"))
                                db.commit()
                                st.success(f"{u.username} agora é Jogador.")
                                st.rerun()
                        else:
                            if st.button(f"⬆️ Promover a Moderador", key=f"promote_{u.id}"):
                                db.execute(update(User).where(User.id == u.id).values(role="moderator"))
                                db.commit()
                                st.success(f"{u.username} agora é Moderador!")
                                st.rerun()

                # 2. Resetar Senha (Apenas SUPREMO)
                if is_supreme:
                    if st.button(f"🔑 Resetar Senha (123456)", key=f"reset_{u.id}"):
                        if u.id == 1:
                            st.warning("Você não pode resetar sua própria senha pelo painel.")
                        else:
                            new_hash = AuthManager.hash_password("123456")
                            db.execute(update(User).where(User.id == u.id).values(hashed_password=new_hash))
                            db.commit()
                            st.success(f"Senha de '{u.username}' resetada para `123456`!")
                            st.rerun()
                
                # 3. Excluir Conta (Apenas SUPREMO)
                if is_supreme:
                    if st.button(f"🗑️ Excluir Conta", key=f"delete_{u.id}", type="secondary"):
                        if u.id == 1:
                            st.error("Você não pode excluir a sua própria conta!")
                        else:
                            db.delete(u)
                            db.commit()
                            st.success(f"Usuário '{u.username}' removido com sucesso!")
                            st.rerun()

# ========== ABA 2: REGIÕES ==========
with tab2:
    st.subheader("🌍 Regiões Cadastradas")
    regions = service.get_regions()
    for r in regions:
        st.write(f"📍 **{r.display_name}** (`{r.name}`)")

# ========== ABA 3: ESTATÍSTICAS ==========
with tab3:
    st.subheader("📊 Métricas de Acesso e IPs")
    
    # Importa o modelo de log
    try:
        from core.models.access_log import AccessLog
        
        logs = db.query(AccessLog).all()
        
        if not logs:
            st.info("📭 Nenhuma visita registrada ainda.")
        else:
            total_visits = len(logs)
            unique_ips = set(log.ip_address for log in logs if log.ip_address)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🌐 Total de Visitas", total_visits)
            col2.metric("👥 IPs Únicos (Pessoas)", len(unique_ips))
            
            st.markdown("---")
            st.write("**🕒 Últimos 20 acessos registrados:**")
            for log in sorted(logs, key=lambda x: x.created_at, reverse=True)[:20]:
                st.caption(
                    f"🕒 {log.created_at.strftime('%d/%m %H:%M')} | "
                    f"🌍 IP: `{log.ip_address or 'Desconhecido'}` | "
                    f"📍 Página: {log.path or 'Dashboard'}"
                )
    except ImportError:
        st.warning("⚠️ Para ver estatísticas, crie o arquivo `core/models/access_log.py` e recrie o banco.")