import streamlit as st
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

st.set_page_config(
    page_title="VTM Territory Manager",
    page_icon="🧛",
    layout="wide",
    initial_sidebar_state="expanded"
)

from core.db.database import init_db
from core.db.session import get_streamlit_db
from core.auth.authenticator import AuthManager
from core.services.territory_service import TerritoryService
from app.components.sidebar import render_sidebar
from app.components.map_viewer import render_map

# Adiciona o caminho das páginas ao sys.path
pages_path = os.path.join(os.path.dirname(__file__), "pages")
if pages_path not in sys.path:
    sys.path.insert(0, pages_path)

# Inicializa banco
init_db()

# Estado da sessão
if "user" not in st.session_state:
    st.session_state.user = None
if "active_locks" not in st.session_state:
    st.session_state.active_locks = []

# ========== RENDERIZA SIDEBAR ==========
render_sidebar()

# ========== CONTROLE DE PÁGINAS ==========
current_page = st.query_params.get("page", "dashboard")

# ========== TELA DE LOGIN / CADASTRO ==========
if st.session_state.user is None:
    st.title("🧛 Vampiro: A Máscara - Territory Manager")
    st.markdown("### Sistema de Gestão de Territórios")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # CRIA AS ABAS DE LOGIN E CRIAÇÃO DE CONTA
        tab1, tab2 = st.tabs(["🔐 Login", "➕ Criar Conta"])
        
        with tab1:
            with st.container(border=True):
                st.subheader("Login")
                username = st.text_input("Usuário", key="login_user")
                password = st.text_input("Senha", type="password", key="login_pass")
                
                if st.button("Entrar", use_container_width=True, type="primary"):
                    db = get_streamlit_db()
                    user = AuthManager.authenticate(db, username, password)
                    if user:
                        st.session_state.user = user
                        st.success(f"Bem-vindo, {user.username}!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")

        with tab2:
            with st.container(border=True):
                st.subheader("Crie sua conta")
                new_username = st.text_input("Escolha seu nome de usuário", key="new_user")
                new_password = st.text_input("Crie uma senha", type="password", key="new_pass")
                new_email = st.text_input("Seu e-mail (opcional)", key="new_email")
                
                if st.button("Criar Conta", use_container_width=True, type="primary"):
                    if not new_username or not new_password:
                        st.error("Preencha o nome de usuário e a senha!")
                    else:
                        db = get_streamlit_db()
                        existing = AuthManager.get_user_by_username(db, new_username)
                        if existing:
                            st.error("Este nome de usuário já existe. Escolha outro.")
                        else:
                            # Cria o usuário. A primeira conta criada na nuvem será o ID 1 (Supremo)
                            AuthManager.create_user(
                                db, 
                                username=new_username, 
                                password=new_password, 
                                email=new_email if new_email else None,
                                role="jogador",
                                assigned_region="Global"
                            )
                            st.success("✅ Conta criada! Agora faça login com seu novo usuário.")
                            st.rerun()
    
    st.stop()

# ========== ROTEAMENTO DE PÁGINAS ==========
user = st.session_state.user
db = get_streamlit_db()
service = TerritoryService(db)

# ============================================================
# NOVO: Registra o IP e a visita do usuário no banco
# ============================================================
try:
    from core.models.access_log import AccessLog
    try:
        headers = st.context.headers
        ip = headers.get("X-Forwarded-For", headers.get("Host", "Desconhecido"))
        user_agent = headers.get("User-Agent", "Desconhecido")
    except Exception:
        ip = "Localhost/Desconhecido"
        user_agent = "Desconhecido"
    
    log_entry = AccessLog(
        ip_address=ip,
        user_agent=user_agent,
        path=st.query_params.get("page", "dashboard")
    )
    db.add(log_entry)
    db.commit()
except ImportError:
    pass

except Exception:
    db.rollback()
    pass
st.markdown("---")
st.markdown(
    "🌐 **Junte-se à nossa comunidade no Reddit!** "
    "[r/VampiroBrasil](https://www.reddit.com/r/VampiroBrasil/) | "
    "Se quiser ajudar, siga a página, torne-se membro para incentivar a gente a crescer!"
)

if current_page == "dashboard" or current_page == "":
    # ===== DASHBOARD =====
    st.title(f"🗺️ Dashboard - {user.assigned_region or 'Global'}")
    
    cols = st.columns(4)
    all_territories = service.get_territories()
    user_region = user.assigned_region
    
    if user_region and user_region != "Global":
        region = service.get_region_by_name(user_region)
        if region:
            region_territories = service.get_territories(region_id=region.id)
        else:
            region_territories = all_territories
    else:
        region_territories = all_territories
    
    with cols[0]:
        st.metric("Total de Territórios", len(all_territories))
    with cols[1]:
        st.metric("Sua Região", len(region_territories))
    with cols[2]:
        clans = set(t.controlling_clan for t in all_territories if t.controlling_clan)
        st.metric("Clãs Ativos", len(clans))
    with cols[3]:
        recent = service.get_history(limit=1)
        last_change = recent[0].changed_at.strftime("%H:%M") if recent else "N/A"
        st.metric("Última Alteração", last_change)
    
    st.markdown("---")
    st.subheader("Visão Global")
    if region_territories:
        render_map(region_territories, key="dashboard_map")
    else:
        st.info("Nenhum território cadastrado ainda.")
    
    st.markdown("---")
    st.subheader("📜 Atividade Recente")
    history = service.get_history(limit=10)
    if history:
        for h in history:
            icon = "🆕" if h.field_changed == "CREATED" else "✏️"
            st.markdown(
                f"{icon} **{h.modified_by}** ({h.modified_by_role}) alterou "
                f"`{h.field_changed}` de *{h.old_value or 'vazio'}* → *{h.new_value or 'vazio'}* "
                f"em **{h.changed_at.strftime('%d/%m %H:%M')}**"
            )
    else:
        st.info("Nenhuma atividade registrada ainda.")

elif current_page == "mapa":
    # ===== MAPA =====
    try:
        import importlib.util
        import os
        file_path = os.path.join(os.path.dirname(__file__), "pages", "01_mapa.py")
        
        if os.path.exists(file_path):
            spec = importlib.util.spec_from_file_location("mapa_page", file_path)
            mapa_page = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mapa_page)
            
            if hasattr(mapa_page, 'render_mapa'):
                mapa_page.render_mapa()
            else:
                st.error("O arquivo 01_mapa.py não tem a função 'render_mapa'")
        else:
            st.error(f"❌ Arquivo não encontrado: {file_path}")
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar o mapa: {e}")
        import traceback
        st.code(traceback.format_exc())

elif current_page == "historico":
    # ===== HISTÓRICO =====
    st.title("📜 Histórico de Alterações")
    history = service.get_history(limit=50)
    if history:
        for h in history:
            with st.container(border=True):
                cols = st.columns([1, 3])
                with cols[0]:
                    st.caption(h.changed_at.strftime("%d/%m %H:%M"))
                with cols[1]:
                    st.write(f"**{h.modified_by}** alterou `{h.field_changed}`")
                    st.caption(f"De: `{h.old_value}` → Para: `{h.new_value}`")
    else:
        st.info("Nenhuma alteração registrada.")

elif current_page == "admin":
    # ===== ADMIN =====
    if user.id != 1 and user.role != "moderator":
        st.error("🚫 Acesso restrito ao Supremo (ID 1) e Moderadores autorizados.")
    else:
        st.title("⚙️ Painel Administrativo")
        st.caption(f"Bem-vindo, {user.username}. Seu nível de acesso: **{'👑 Supremo' if user.id == 1 else '🛡️ Moderador'}**")
        
        from core.models.user import User
        from core.auth.authenticator import AuthManager
        from sqlalchemy import update
        
        tab1, tab2, tab3 = st.tabs(["👤 Gerenciar Usuários", "🌍 Regiões", "📊 Estatísticas do Site"])
        
        with tab1:
            st.subheader("🔧 Lista de Usuários Cadastrados")
            users = db.query(User).all()
            
            for u in users:
                with st.container(border=True):
                    cols = st.columns([2, 1, 1, 2])
                    cols[0].write(f"**{u.username}** (🆔 ID: `{u.id}`)")
                    cols[1].write(f"Role: `{u.role}`")
                    cols[2].write(f"Clã: {u.clan or 'N/A'}")
                    
                    with cols[3]:
                        if user.id == 1:
                            if u.id != 1:
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

                        if user.id == 1:
                            if st.button(f"🔑 Resetar Senha (123456)", key=f"reset_{u.id}"):
                                if u.id == 1:
                                    st.warning("Você não pode resetar sua própria senha pelo painel.")
                                else:
                                    new_hash = AuthManager.hash_password("123456")
                                    db.execute(update(User).where(User.id == u.id).values(hashed_password=new_hash))
                                    db.commit()
                                    st.success(f"Senha de '{u.username}' resetada para `123456`!")
                                    st.rerun()
                        
                        if user.id == 1:
                            if st.button(f"🗑️ Excluir Conta", key=f"delete_{u.id}", type="secondary"):
                                if u.id == 1:
                                    st.error("Você não pode excluir a sua própria conta!")
                                else:
                                    db.delete(u)
                                    db.commit()
                                    st.success(f"Usuário '{u.username}' removido com sucesso!")
                                    st.rerun()
        
        with tab2:
            st.subheader("🌍 Regiões Cadastradas")
            regions = service.get_regions()
            for r in regions:
                st.write(f"📍 **{r.display_name}** (`{r.name}`)")
        
        with tab3:
            st.subheader("📊 Métricas de Acesso e IPs")
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
                st.warning("⚠️ Ainda não criamos a tabela de logs. Crie o arquivo `core/models/access_log.py` e recrie o banco.")
            
else:
    st.warning("Página não encontrada")