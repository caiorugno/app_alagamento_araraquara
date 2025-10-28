import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

def desenhar_mapa(dados_clima):
    pontos = pd.read_csv("data/pontos_alagamento.csv")

    mapa = folium.Map(location=[-21.7945, -48.1752], zoom_start=13)

    for _, row in pontos.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=row["local"],
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(mapa)

    st.subheader("🗺️ Mapa Interativo de Pontos de Alagamento")
    st_folium(mapa, width=900, height=500)
