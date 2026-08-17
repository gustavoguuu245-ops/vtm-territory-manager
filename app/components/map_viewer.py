# app/components/map_viewer.py - VERSÃO FINAL (APENAS DESENHO E POLÍGONO)
"""Componente de visualização do mapa com Folium."""
import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from typing import List, Optional
from core.models.territory import Territory
from config.settings import settings

def get_clan_color(clan: str) -> str:
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
        "Ministry": "#FFD700",      
        "Hecata": "#556B2F",        
        "Banu Haqim": "#8B4513",   
        "The Thin-Blood": "#FFFFFF",
    }
    return colors.get(clan, "#808080")

def render_map(territories: List[Territory], 
               center: tuple = None,
               zoom: int = None,
               enable_draw: bool = False,
               height: int = 500,
               key: str = "map") -> dict:
    """Renderiza o mapa com territórios."""
    if center is None:
        center = settings.DEFAULT_MAP_CENTER
    if zoom is None:
        zoom = settings.DEFAULT_MAP_ZOOM
    
    # CRIA O MAPA
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter"
    )
    
    # Tiles alternativos
    folium.TileLayer("OpenStreetMap", name="Padrão", control=True).add_to(m)
    folium.TileLayer("CartoDB positron", name="Claro", control=True).add_to(m)
    
    # ========================================================
    # DESENHA OS TERRITÓRIOS (APENAS POLÍGONOS, SEM PINOS)
    # ========================================================
    for t in territories:
        # Define a cor do clã
        color = t.map_color or get_clan_color(t.controlling_clan)
        
        # Popup de informações
        popup_html = f"""
        <div style="font-family: serif; min-width: 150px;">
            <h4>{t.name}</h4>
            <b>Clã:</b> {t.controlling_clan or 'Neutro'}<br>
            <b>Influência:</b> {'⭐' * (t.influence_level or 1)}<br>
            <b>Perigo:</b> {'💀' * (t.danger_level or 1)}<br>
            <b>Versão:</b> v{t.version}
        </div>
        """
        
        # Se tiver um polígono salvo, desenha ele exatamente como foi desenhado
        if t.geojson_polygon:
            try:
                import json
                geo = json.loads(t.geojson_polygon)
                folium.GeoJson(
                    geo,
                    style_function=lambda x, color=color: {
                        "fillColor": color,      # Cor do Clã
                        "color": color,          # Borda da mesma cor
                        "weight": 2,
                        "fillOpacity": 0.4       # Transparência
                    },
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(m)
            except:
                pass # Ignora erros no JSON
    
    # ========================================================
    # FERRAMENTA DE DESENHO DO MAPA (VOLTOU AQUI!)
    # ========================================================
    if enable_draw:
        Draw(
            draw_options={
                "polyline": False,
                "rectangle": True,    # Permite desenhar retângulo
                "polygon": True,      # Permite desenhar polígono livre
                "circle": False,      # Não permite círculo
                "marker": False,      # Não permite marcador manual
                "circlemarker": False
            },
            edit_options={"edit": True, "remove": True}
        ).add_to(m)
    
    # Adiciona popup de clique para mostrar coordenadas
    m.add_child(folium.LatLngPopup())
    
    # Adiciona controle de camadas
    folium.LayerControl().add_to(m)
    
    # RETORNA com captura de clique e desenho
    return st_folium(
        m, 
        width="100%", 
        height=height, 
        returned_objects=["last_clicked", "all_drawings", "last_active_drawing"], 
        key=key
    )