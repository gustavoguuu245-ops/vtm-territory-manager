import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("🧪 Teste do Mapa")

m = folium.Map(location=[-22.9068, -43.1729], zoom_start=12)

folium.LatLngPopup().add_to(m)

output = st_folium(m, width=700, height=500, returned_objects=["last_clicked"])

if output and output.get("last_clicked"):
    st.success(f"📍 Você clicou em: {output['last_clicked']}")
    
    lat = output["last_clicked"]["lat"]
    lng = output["last_clicked"]["lng"]
    
    with st.form("test_form"):
        nome = st.text_input("Nome do território")
        if st.form_submit_button("Salvar"):
            st.success(f"Território {nome} em {lat}, {lng}")
else:
    st.info("👆 Clique no mapa")