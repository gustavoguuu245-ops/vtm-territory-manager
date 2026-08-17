import streamlit as st
from core.auth.authenticator import AuthManager

def render_sidebar():
    """Renderiza a sidebar com informações do usuário logado."""
    with st.sidebar:
        st.title("🧛 VTM Territory Manager")
        st.markdown("---")
        
        if "user" in st.session_state and st.session_state.user:
            user = st.session_state.user
            st.subheader(f"Olá, {user.username}")
            st.caption(f"Role: **{user.role.upper()}**")
            if user.assigned_region:
                st.caption(f"Região: {user.assigned_region}")
            if user.clan:
                st.caption(f"Clã: {user.clan}")
            
            st.markdown("---")
            
            # Contador de locks ativos
            if "active_locks" in st.session_state and st.session_state.active_locks:
                st.warning(f"🔒 {len(st.session_state.active_locks)} território(s) travado(s)")
            
            if st.button("🚪 Sair", use_container_width=True):
                from core.services.territory_service import TerritoryService
                from core.db.session import get_streamlit_db
                
                db = get_streamlit_db()
                service = TerritoryService(db)
                service.release_all_user_locks(user)
                
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            st.info("Faça login para continuar")
'''

with open(f"{base}/app/components/sidebar.py", "w", encoding="utf-8") as f:
    f.write(sidebar_py)

# ============================================
# 9. app/components/map_viewer.py
# ============================================
map_viewer_py = '''"""Componente de visualização do mapa com Folium."""
import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from typing import List, Optional
from core.models.territory import Territory
from config.settings import settings

def get_clan_color(clan: str) -> str:
    """Retorna cor do clã para o mapa."""
    colors = {
        "Brujah": "#FF0000",
        "Gangrel": "#006400",
        "Malkavian": "#9400D3",
        "Nosferatu": "#2F4F4F",
        "Toreador": "#FF69B4",
        "Tremere": "#8B0000",
        "Ventrue": "#000080",
        "Lasombra": "#000000",
        "Tzimisce": "#4B0082",
        "Assamita": "#8B4513",
        "Setita": "#FFD700",
        "Giovanni": "#556B2F",
        "Ravnos": "#FF8C00",
        "Neutro": "#808080",
        "Caçador": "#DC143C",
    }
    return colors.get(clan, "#808080")

def render_map(territories: List[Territory], 
               center: tuple = None,
               zoom: int = None,
               enable_draw: bool = False,
               key: str = "map") -> dict:
    """Renderiza o mapa com territórios.
    
    Returns:
        dict com dados do último clique/desenho do usuário
    """
    if center is None:
        center = settings.DEFAULT_MAP_CENTER
    if zoom is None:
        zoom = settings.DEFAULT_MAP_ZOOM
    
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter"  # Tema escuro para VTM
    )
    
    # Adiciona tiles alternativos
    folium.TileLayer("OpenStreetMap", name="Padrão", control=True).add_to(m)
    folium.TileLayer("CartoDB positron", name="Claro", control=True).add_to(m)
    
    # Desenha territórios
    for t in territories:
        color = t.map_color or get_clan_color(t.controlling_clan)
        popup_html = f"""
        <div style="font-family: serif;">
            <h4>{t.name}</h4>
            <b>Clã:</b> {t.controlling_clan or 'Neutro'}<br>
            <b>Influência:</b> {'●' * (t.influence_level or 1)}<br>
            <b>Perigo:</b> {'⚠' * (t.danger_level or 1)}<br>
            <b>Versão:</b> {t.version}<br>
            <i>Modificado por: {t.modified_by or 'N/A'}</i>
        </div>
        """
        
        # Se tem polígono GeoJSON, desenha polígono
        if t.geojson_polygon:
            try:
                import json
                geo = json.loads(t.geojson_polygon)
                folium.GeoJson(
                    geo,
                    style_function=lambda x, color=color: {
                        "fillColor": color,
                        "color": color,
                        "weight": 2,
                        "fillOpacity": 0.4
                    },
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(m)
            except:
                pass
        else:
            # Ponto simples
            folium.CircleMarker(
                location=[t.latitude, t.longitude],
                radius=8 + (t.influence_level or 1) * 2,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=t.name,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6
            ).add_to(m)
    
    # Ferramenta de desenho (para narradores criarem polígonos)
    if enable_draw:
        Draw(
            draw_options={
                "polyline": False,
                "rectangle": True,
                "polygon": True,
                "circle": False,
                "marker": True,
                "circlemarker": False
            },
            edit_options={"edit": False}
        ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return st_folium(m, width="100%", height=600, returned_objects=["last_clicked", "all_drawings"], key=key)
'''

with open(f"{base}/app/components/map_viewer.py", "w", encoding="utf-8") as f:
    f.write(map_viewer_py)

# ============================================
# 10. app/main.py (página principal / login)
# ============================================
main_py = '''"""Aplicação principal - Login e Dashboard."""
import streamlit as st
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

# Inicializa banco na primeira execução
init_db()

# Estado da sessão
if "user" not in st.session_state:
    st.session_state.user = None
if "active_locks" not in st.session_state:
    st.session_state.active_locks = []

render_sidebar()

# ========== TELA DE LOGIN ==========
if st.session_state.user is None:
    st.title("🧛 Vampiro: A Máscara - Territory Manager")
    st.markdown("### Sistema de Gestão de Territórios")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔐 Login")
            username = st.text_input("Usuário", key="login_user")
            password = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Entrar", use_container_width=True, type="primary"):
                db = get_streamlit_db()
                user = AuthManager.authenticate(db, username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.token = AuthManager.create_token(
                        user.username, user.role, user.id
                    )
                    st.success(f"Bem-vindo, {user.username}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")
        
        st.info("""
        **Contas padrão de demonstração:**
        - Narrador: `narrador` / `narrador123`
        - Jogador BR: `jogador_br` / `br123`
        - Jogador ES: `jogador_es` / `es123`
        """)
    
    st.stop()

# ========== DASHBOARD ==========
user = st.session_state.user
st.title(f"🗺️ Dashboard - {user.assigned_region or 'Global'}")

db = get_streamlit_db()
service = TerritoryService(db)

# Cards de resumo
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

# Visão rápida do mapa
from app.components.map_viewer import render_map

st.subheader("Visão Global")
if region_territories:
    render_map(region_territories, key="dashboard_map")
else:
    st.info("Nenhum território cadastrado ainda. Vá até a página de Mapa para criar.")

# Atividade recente
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
