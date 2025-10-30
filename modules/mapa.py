import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Função para classificar o risco com base na chuva prevista
def classificar_risco(chuva_mm):
    if chuva_mm >= 20:
        return "alto"
    elif chuva_mm >= 10:
        return "medio"
    else:
        return "baixo"

# Função principal para desenhar o mapa com ícones coloridos
def desenhar_mapa(dados_clima):
    # Carrega os pontos de alagamento
    pontos = pd.read_csv("data/pontos_alagamento.csv")

    # Cria o mapa centralizado em Araraquara
    mapa = folium.Map(location=[-21.7945, -48.1752], zoom_start=13)

    # Soma total da chuva prevista nas próximas horas
    chuva_total = dados_clima["Chuva (mm)"].sum()

    # Adiciona marcadores para cada ponto
    for _, row in pontos.iterrows():
        risco = classificar_risco(chuva_total)

        cor = {
            "baixo": "green",
            "medio": "orange",
            "alto": "red"
        }[risco]

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"{row['local']}<br>Risco: {risco.title()}<br>Chuva prevista: {chuva_total:.1f} mm",
            icon=folium.Icon(color=cor, icon="cloud")
        ).add_to(mapa)

    # Exibe o mapa no Streamlit
    st.subheader("🗺️ Mapa Interativo de Pontos de Alagamento")
    st_folium(mapa, width=900, height=500)
