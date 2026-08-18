import streamlit as st
import json
from core.db.session import get_streamlit_db
from core.services.territory_service import TerritoryService
from app.components.map_viewer import render_map, get_clan_color

def render_mapa():
    """Renderiza a página do mapa."""
    if "user" not in st.session_state or st.session_state.user is None:
        st.warning("⚠️ Faça login primeiro")
        return
    
    user = st.session_state.user
    db = get_streamlit_db()
    service = TerritoryService(db)
    
    st.title("🗺️ Mapa de Territórios")
    
    # ========== SELETOR DE REGIÃO ==========
    regions = service.get_regions()
    
    if not regions:
        st.warning("⚠️ Nenhuma região cadastrada. Execute o seed.py primeiro!")
        return
    
    region_options = {r.display_name: r for r in regions}
    
    if user.assigned_region and user.assigned_region != "Global":
        region = service.get_region_by_name(user.assigned_region)
        selected_region = region
        st.info(f"📍 Visualizando sua região: **{user.assigned_region}**")
    else:
        selected_name = st.selectbox(
            "📍 Selecione a Região", 
            list(region_options.keys()),
            key="region_selector"
        )
        selected_region = region_options[selected_name]
    
    if selected_region is None:
        st.error("❌ Região não encontrada")
        return
    
    
    
    # 1. Verifica se o link já veio com o ID de outro usuário (ex: ?view_user_id=2)
    view_user_id_str = st.query_params.get("view_user_id")
    target_user_id = user.id
    is_viewing_other = False

    if view_user_id_str and view_user_id_str.isdigit():
        target_user_id = int(view_user_id_str)
        if target_user_id != user.id:
            is_viewing_other = True

    # 2. Campo de ID 
    st.caption("🔎 Visualizar mapa de outro ID:")
    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        # Se já estiver vendo outro, mostra o ID na caixa. Se não, deixa vazio.
        search_id = st.text_input(
            "ID do Usuário", 
            value=str(target_user_id) if is_viewing_other else "", 
            label_visibility="collapsed", 
            placeholder="Digite o ID (ex: 2)"
        )
    with col_search2:
        if st.button("Ir para ID", use_container_width=True, type="secondary"):
            if search_id and search_id.isdigit():
                # Atualiza a URL e recarrega a página
                st.query_params["view_user_id"] = search_id
                st.rerun()
            else:
                st.error("Digite um ID numérico válido!")

    # 3. Carrega os territórios APENAS do usuário 
    territories = service.get_territories(region_id=selected_region.id, owner_id=target_user_id)
    
    # 4. Bloqueia a edição se estiver vendo o mapa de outro 
    if is_viewing_other:
        st.warning(f"👁️ Modo Visualização: Você está vendo o mapa do ID {target_user_id}. Não é possível editar.")

    # ========== LAYOUT PRINCIPAL ==========
    col_map, col_panel = st.columns([3, 2])
    
    with col_map:
        st.subheader("🗺️ Clique ou desenhe no mapa")
        
        # Renderiza o mapa (Bloqueia o desenho se estiver vendo outro ID)
        map_data = render_map(
            territories,
            center=(selected_region.center_lat, selected_region.center_lng),
            zoom=selected_region.zoom_level,
            enable_draw=not is_viewing_other,
            key=f"map_{selected_region.id}"
        )
        
        # Feedback do que foi clicado/desenhado
        has_draw = False
        if map_data and map_data.get("all_drawings"):
            drawings = map_data["all_drawings"]
            if drawings:
                last_draw = drawings[-1]
                if last_draw.get("geometry") and last_draw["geometry"]["type"] in ["Polygon", "Rectangle"]:
                    has_draw = True
                    if not is_viewing_other: # Só mostra se puder editar
                        st.success("✅ Polígono desenhado! Preencha o nome e salve.")
        
        if not has_draw and map_data and map_data.get("last_clicked"):
            click = map_data["last_clicked"]
            if not is_viewing_other:
                st.success(f"📍 Ponto selecionado! Lat: {click['lat']:.5f}, Lng: {click['lng']:.5f}")
        
        if not has_draw and not (map_data and map_data.get("last_clicked")):
            if not is_viewing_other:
                st.info("👆 Clique no mapa para marcar um ponto, ou desenhe um polígono.")
            
        # ========================================================
        # TUTORIAL RÁPIDO PARA NOVOS USUÁRIOS

        with st.expander("💡 Como criar seu primeiro Território?", expanded=False):
            st.markdown("""
            **1. Desenhe a área:**  
            Use a ferramenta de **Polígono** (o ícone de pentágono ou quadrado no lado esquerdo do mapa).  
            Clique em vários pontos para contornar o bairro ou área que você quer dominar.

            **2. Feche a forma:**  
            Dê um **duplo clique** no último ponto para fechar o polígono.

            **3. Salve o domínio:**  
            Preencha o nome do território, escolha o Clã, ajuste os níveis e clique no botão vermelho **Salvar Território**.
            """)
        # ========================================================

    with col_panel:
                # ========== LISTA DE TERRITÓRIOS ==========
        st.subheader("🏛️ Domínios da Região")
        
        if territories:
            for t in territories:
                with st.expander(f"📍 {t.name} - {t.controlling_clan or 'Neutro'}", expanded=False):
                    st.write(f"**Clã:** {t.controlling_clan or 'Neutro'}")
                    st.write(f"**Influência:** {'⭐' * (t.influence_level or 1)}")
                    st.write(f"**Perigo:** {'💀' * (t.danger_level or 1)}")
                    
                    # Só permite editar se for o próprio mapa e tiver permissão
                    if not is_viewing_other and user.can_edit_region(selected_region.name):
                        
                        # Botão de Editar
                        if st.button(f"✏️ Editar", key=f"edit_btn_{t.id}"):
                            st.session_state.editing_territory = t.id
                            st.rerun()
                        
                        # ============================================================
                        # NOVO: BOTÃO DE EXCLUIR COM CONFIRMAÇÃO
                        # ============================================================
                        with st.popover("🗑️ Excluir Território", use_container_width=True):
                            st.warning(f"Tem certeza que deseja excluir **{t.name}**?")
                            st.caption("Essa ação não pode ser desfeita.")
                            if st.button("Sim, excluir permanentemente", key=f"delete_confirm_{t.id}", type="primary"):
                                result = service.delete_territory(t.id, user)
                                if result["success"]:
                                    st.success(result["message"])
                                    st.rerun()
                                else:
                                    st.error(result["error"])
                        # ============================================================
        else:
            st.info("📭 Nenhum território cadastrado.")
        
        st.divider()
        
        # ADICIONAR NOVO DOMÍNIO 
        st.subheader("➕ Adicionar Novo Domínio")
        
        # Se estiver vendo outro mapa, bloqueia qualquer criação
        can_create = user.can_edit_region(selected_region.name) and not is_viewing_other
        
        if not can_create:
            if is_viewing_other:
                st.info("🔒 Você está em modo visualização. Não pode criar territórios aqui.")
            else:
                st.error("🚫 Você não tem permissão para criar territórios nesta região")
        
        nome = st.text_input("Nome do Território", placeholder="Ex: Centro, Taverna..", disabled=not can_create)
        
        col1, col2 = st.columns(2)
        with col1:
            clan = st.selectbox(
                "Clã Dominante",
                ["Brujah", "Gangrel", "Malkavian", "Nosferatu", "Setita", "Toreador", "Tremere", "Ventrue", "Lasombra", "Tzimisce", "Assamita", "Ravnos", "Giovanni", "Banu Haqim", "Ministry", "Hecata", "Neutro", "Caçador", "The Thin-Blood"],
                disabled=not can_create
            )
        with col2:
            influencia = st.slider("Influência", 1, 5, 3, disabled=not can_create)
        
        perigo = st.slider("Nível de Perigo", 1, 5, 1, disabled=not can_create)
        
        # CAPTURA DOS DADOS DO MAPA (Direto do map_data)
        has_click = map_data and map_data.get("last_clicked") is not None
        
        has_draw = False
        geojson_str = None
        lat = selected_region.center_lat
        lng = selected_region.center_lng
        
        if map_data and map_data.get("all_drawings"):
            drawings = map_data["all_drawings"]
            if drawings:
                last_shape = drawings[-1]
                if last_shape.get("geometry") and last_shape["geometry"]["type"] in ["Polygon", "Rectangle"]:
                    has_draw = True
                    geojson_str = json.dumps(last_shape["geometry"])
                    coords = last_shape["geometry"]["coordinates"][0]
                    lat = sum(p[1] for p in coords) / len(coords)
                    lng = sum(p[0] for p in coords) / len(coords)
                    st.caption(f"📍 Capturado: Polígono")
        
        if not has_draw and has_click:
            lat = map_data["last_clicked"]["lat"]
            lng = map_data["last_clicked"]["lng"]
            st.caption(f"📍 Capturado: Ponto")
        
        # =======================================================
        # O BOTÃO SALVAR (Funciona com Enter ou Clique)
       
        has_selection = has_click or has_draw
        can_save = can_create and has_selection and nome
        
        if st.button("💾 Salvar Território", type="primary", disabled=not can_save):
            try:
                service.create_territory(
                    user=user,
                    owner_id=user.id,              
                    name=nome,
                    region_id=selected_region.id,
                    latitude=lat,
                    longitude=lng,
                    controlling_clan=clan,
                    geojson_polygon=geojson_str,
                    map_color=get_clan_color(clan),
                    influence_level=influencia,
                    danger_level=perigo
                )
                st.success(f"✅ Território '{nome}' criado!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
        
        # ========== EDIÇÃO ==========
        if "editing_territory" in st.session_state:
            edit_id = st.session_state.editing_territory
            territory = service.get_territory(edit_id)
            
            if territory:
                st.divider()
                st.subheader(f"✏️ Editando: {territory.name}")
                
                if not user.can_edit_region(territory.region.name if territory.region else ""):
                    st.error("🚫 Sem permissão")
                    if st.button("❌ Fechar"):
                        del st.session_state.editing_territory
                        st.rerun()
                else:
                    lock_result = service.acquire_lock(
                        territory.id, user, 
                        st.session_state.get("token", "session")
                    )
                    
                    if not lock_result["success"]:
                        st.error(f"🔒 {lock_result['message']}")
                        if st.button("🔄 Tentar novamente"):
                            st.rerun()
                    else:
                        st.success(f"🔓 Travado até {lock_result['expires_at'].strftime('%H:%M:%S')}")
                        
                        with st.form("form_editar"):
                            clan_list = ["Brujah", "Gangrel", "Malkavian", "Nosferatu", 
                                        "Toreador", "Tremere", "Ventrue", "Lasombra", 
                                        "Tzimisce", "Assamita", "Setita", "Giovanni", "Neutro"]
                            current_clan = territory.controlling_clan or "Neutro"
                            try:
                                clan_index = clan_list.index(current_clan)
                            except ValueError:
                                clan_index = 0
                            
                            novo_clan = st.selectbox("Clã", clan_list, index=clan_index)
                            nova_influencia = st.slider("Influência", 1, 5, territory.influence_level or 1)
                            novo_perigo = st.slider("Perigo", 1, 5, territory.danger_level or 1)
                            motivo = st.text_input("Motivo", placeholder="Ex: Conquista")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Salvar", type="primary"):
                                    changes = {
                                        "controlling_clan": novo_clan,
                                        "influence_level": nova_influencia,
                                        "danger_level": novo_perigo,
                                    }
                                    result = service.update_territory(
                                        territory.id, user, changes,
                                        reason=motivo or "Alteração",
                                        expected_version=territory.version
                                    )
                                    if result["success"]:
                                        st.success("✅ Salvo!")
                                        del st.session_state.editing_territory
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {result['error']}")
                            
                            with col2:
                                if st.form_submit_button("❌ Cancelar"):
                                    service.release_lock(territory.id, user)
                                    del st.session_state.editing_territory
                                    st.rerun()

if __name__ == "__main__":
    render_mapa()